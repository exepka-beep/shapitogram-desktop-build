import { createHash, randomInt } from "node:crypto";
import { normalizeLanguage, translate } from "./i18n.js";

// Wallet <-> account linking for ShapitoTON (ton.shapitogram.xyz).
//
// Flow: the wallet asks for a code bound to a phone number; the bot delivers a
// six-digit code to the Telegram chat that already owns that phone; the wallet
// confirms the code and the account is bound to the wallet address. Proof of
// the phone is exactly what the OTP login flow proves, so no new channel is
// trusted here.
export const CODE_TTL_MS = 10 * 60 * 1000;
export const MAX_CODE_ATTEMPTS = 5;
const MAX_CODES_PER_WINDOW = 3;
const CODE_REQUEST_WINDOW_MS = 15 * 60 * 1000;
const DELETE_CODE_AFTER_MS = 120_000;

export class WalletLinkError extends Error {
  constructor(code) {
    super(code);
    this.name = "WalletLinkError";
    this.code = code;
  }
}

// TON user addresses are base64url of 36 bytes (48 chars) or 48 bytes (64
// chars). Only the friendly form is accepted; anything else never reaches the
// chain lookups.
export function normalizeWalletAddress(value) {
  const address = String(value ?? "").trim();
  return /^[A-Za-z0-9_-]{48}$/.test(address) || /^[A-Za-z0-9_-]{64}$/.test(address) ? address : "";
}

// Phones travel with a leading "+" inside the store database (normalizePhone
// in db.js) and without it on the server; keep both forms out of the helpers.
export function normalizePhoneInput(value) {
  const raw = String(value ?? "").trim().replace(/[^\d+]/g, "");
  if (!raw) return "";
  const plus = raw.startsWith("+");
  const digits = raw.replace(/\D/g, "");
  if (!digits || digits.length < 5 || digits.length > 15) return "";
  return `${plus ? "+" : "+"}${digits}`;
}

function hashCode(code) {
  return createHash("sha256").update(`tonlink:${code}`).digest("hex");
}

function digits(count) {
  let out = "";
  for (let i = 0; i < count; i += 1) out += String(randomInt(0, 10));
  return out;
}

function codeMessage(language, config, code) {
  const variables = { product: config.productName, code };
  return [
    translate(language, "tonLinkTitle"),
    "",
    translate(language, "tonLinkCode", variables),
    "",
    translate(language, "tonLinkHint"),
  ].join("\n");
}

export class WalletLink {
  constructor({ db, gramsrv, bot, config }) {
    this.db = db;
    this.gramsrv = gramsrv;
    this.bot = bot;
    this.config = config;
  }

  // The phone must belong to a known store user: a verified phone, a number
  // whose login codes this bot already delivers to that chat, or an anonymous
  // number the user owns (the same three sources the OTP delivery uses).
  async resolveTarget(phone) {
    const row = (await this.db.pool.query(
      `WITH owners AS (
         SELECT telegram_id FROM verified_phones WHERE phone = $1
         UNION
         SELECT telegram_id FROM code_access WHERE phone = $1
         UNION
         SELECT owner_id FROM numbers WHERE phone = $1 AND owner_id IS NOT NULL
       )
       SELECT u.telegram_id, u.chat_id, u.username, u.first_name, u.language, u.server_user_id
         FROM users u
         JOIN owners o ON o.telegram_id = u.telegram_id
        ORDER BY u.updated_at DESC
        LIMIT 1`,
      [phone],
    )).rows[0];
    if (!row) throw new WalletLinkError("ACCOUNT_NOT_FOUND");
    return row;
  }

  async serverUserID(phone, fallback) {
    try {
      const resolved = await this.gramsrv.resolveUserByPhone(phone);
      if (resolved > 0) return resolved;
    } catch (error) {
      console.error("tonlink account resolve failed", phone, error);
    }
    return fallback > 0 ? fallback : 0;
  }

  async requestLink(phone, wallet) {
    const target = await this.resolveTarget(phone);
    const recent = Number((await this.db.pool.query(
      `SELECT count(*)::int AS n FROM ton_link_codes
        WHERE phone = $1 AND created_at > now() - ($2::bigint * interval '1 millisecond')`,
      [phone, CODE_REQUEST_WINDOW_MS],
    )).rows[0]?.n ?? 0);
    if (recent >= MAX_CODES_PER_WINDOW) throw new WalletLinkError("TOO_MANY_REQUESTS");

    const code = digits(6);
    // Any still-pending code for the phone becomes unusable, so only the
    // newest message can confirm the link.
    await this.db.pool.query(
      "UPDATE ton_link_codes SET consumed_at = now() WHERE phone = $1 AND consumed_at IS NULL",
      [phone],
    );
    await this.db.pool.query(
      `INSERT INTO ton_link_codes(telegram_id, chat_id, phone, wallet_address, code_hash, expires_at)
       VALUES($1, $2, $3, $4, $5, now() + ($6::bigint * interval '1 millisecond'))`,
      [target.telegram_id, target.chat_id, phone, wallet, hashCode(code), CODE_TTL_MS],
    );

    const language = normalizeLanguage(target.language, this.config.defaultLanguage);
    try {
      const sent = await this.bot.api.sendMessage(target.chat_id, codeMessage(language, this.config, code), { parse_mode: "HTML" });
      if (sent?.message_id) {
        setTimeout(() => this.bot.api.deleteMessage(target.chat_id, sent.message_id).catch(() => {}), DELETE_CODE_AFTER_MS).unref?.();
      }
    } catch (error) {
      console.error("tonlink code delivery failed", target.chat_id, error);
      await this.db.pool.query(
        "UPDATE ton_link_codes SET consumed_at = now() WHERE phone = $1 AND consumed_at IS NULL",
        [phone],
      );
      throw new WalletLinkError("DELIVERY_FAILED");
    }
    return { ok: true, expiresIn: Math.floor(CODE_TTL_MS / 1000) };
  }

  async confirmLink(phone, code) {
    const normalized = String(code ?? "").trim();
    if (!/^\d{6}$/.test(normalized)) throw new WalletLinkError("CODE_INVALID");
    const row = (await this.db.pool.query(
      `SELECT * FROM ton_link_codes
        WHERE phone = $1 AND consumed_at IS NULL AND expires_at > now()
        ORDER BY id DESC
        LIMIT 1`,
      [phone],
    )).rows[0];
    if (!row) throw new WalletLinkError("CODE_EXPIRED");
    if (row.attempts >= MAX_CODE_ATTEMPTS) throw new WalletLinkError("TOO_MANY_ATTEMPTS");
    if (row.code_hash !== hashCode(normalized)) {
      await this.db.pool.query("UPDATE ton_link_codes SET attempts = attempts + 1 WHERE id = $1", [row.id]);
      throw new WalletLinkError("CODE_INVALID");
    }

    const account = (await this.db.pool.query(
      "SELECT telegram_id, chat_id, username, first_name, language, server_user_id FROM users WHERE telegram_id = $1",
      [row.telegram_id],
    )).rows[0];
    if (!account) throw new WalletLinkError("ACCOUNT_NOT_FOUND");

    const serverUserID = await this.serverUserID(phone, account.server_user_id);
    await this.db.pool.query("UPDATE ton_link_codes SET consumed_at = now() WHERE id = $1", [row.id]);
    await this.db.pool.query(
      `INSERT INTO ton_wallet_links(telegram_id, server_user_id, chat_id, phone, wallet_address)
       VALUES($1, $2, $3, $4, $5)
       ON CONFLICT (telegram_id) DO UPDATE SET
         server_user_id = EXCLUDED.server_user_id,
         chat_id = EXCLUDED.chat_id,
         phone = EXCLUDED.phone,
         wallet_address = EXCLUDED.wallet_address,
         updated_at = now()`,
      [account.telegram_id, serverUserID, account.chat_id, phone, row.wallet_address],
    );

    const language = normalizeLanguage(account.language, this.config.defaultLanguage);
    this.bot.api.sendMessage(account.chat_id, translate(language, "tonLinkDone", {
      wallet: row.wallet_address,
      product: this.config.productName,
    }), { parse_mode: "HTML" }).catch(() => {});

    return {
      ok: true,
      account: {
        phone,
        wallet: row.wallet_address,
        telegramId: Number(account.telegram_id),
        serverUserId: serverUserID,
        username: account.username || "",
        firstName: account.first_name || "",
      },
    };
  }

  async status(wallet) {
    const row = (await this.db.pool.query(
      `SELECT l.phone, l.wallet_address, l.server_user_id, l.linked_at, u.username, u.first_name
         FROM ton_wallet_links l
         LEFT JOIN users u ON u.telegram_id = l.telegram_id
        WHERE l.wallet_address = $1`,
      [wallet],
    )).rows[0];
    if (!row) return { linked: false };
    return {
      linked: true,
      account: {
        phone: row.phone,
        wallet: row.wallet_address,
        telegramId: 0,
        serverUserId: Number(row.server_user_id ?? 0),
        username: row.username || "",
        firstName: row.first_name || "",
        linkedAt: row.linked_at,
      },
    };
  }

  // Both the address and the phone must match: the address alone is public
  // knowledge (it is printed in gift cards), the phone alone is guessable.
  async unlink(wallet, phone) {
    const removed = await this.db.pool.query(
      "DELETE FROM ton_wallet_links WHERE wallet_address = $1 AND phone = $2",
      [wallet, phone],
    );
    return { ok: true, removed: removed.rowCount ?? 0 };
  }

  // Bot-facing status for the /tonlink command; the store user is the caller.
  async statusForTelegram(telegramID) {
    const row = (await this.db.pool.query(
      `SELECT l.wallet_address, l.phone, l.server_user_id
         FROM ton_wallet_links l
        WHERE l.telegram_id = $1`,
      [telegramID],
    )).rows[0];
    if (!row) return { linked: false };
    return { linked: true, wallet: row.wallet_address, phone: row.phone, serverUserId: Number(row.server_user_id ?? 0) };
  }
}
