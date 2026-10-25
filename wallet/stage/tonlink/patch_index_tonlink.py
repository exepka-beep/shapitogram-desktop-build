import io, sys

PATH = "/root/shapito-store/src/index.js"

with io.open(PATH, encoding="utf-8") as f:
    text = f.read()

if "WalletLink" in text:
    sys.exit("already patched")

# 1. import
old_import = 'import { isRealMode } from "./real-number.js";'
new_import = old_import + '\nimport { WalletLink, normalizePhoneInput, normalizeWalletAddress } from "./tonlink.js";'
assert old_import in text, "import anchor missing"
text = text.replace(old_import, new_import, 1)

# 2. instantiate after bot creation
old_bot = "const bot = createBot({ config, db, gramsrv });"
new_bot = old_bot + "\nconst walletLink = new WalletLink({ db, gramsrv, bot, config });"
assert old_bot in text, "bot anchor missing"
text = text.replace(old_bot, new_bot, 1)

# 3. route /tonlink before the POST-only guard
old_route = '  if (request.method !== "POST" || !["/code", "/v1/otp/deliveries"].includes(request.url)) return json(response, 404, { error: "not found" });'
new_route = '  if ((request.url ?? "").split("?")[0].startsWith("/tonlink")) return void handleTonlink(request, response);\n' + old_route
assert old_route in text, "route anchor missing"
text = text.replace(old_route, new_route, 1)

# 4. handler before server creation
handler = '''
// --- Wallet <-> account linking (ShapitoTON, ton.shapitogram.xyz) ----------
// These endpoints are called by the browser wallet on another origin of the
// same service, so they carry no Telesrv signature: the six-digit code that
// the bot delivers to the phone owner is the proof. A coarse per-IP limit
// keeps the code endpoints from being hammered.
const TONLINK_WINDOW_MS = 60_000;
const TONLINK_MAX_PER_WINDOW = 40;
const tonlinkHits = new Map();
function tonlinkLimited(ip) {
  const now = Date.now();
  const key = String(ip ?? "unknown");
  const bucket = (tonlinkHits.get(key) ?? []).filter((at) => now - at < TONLINK_WINDOW_MS);
  if (bucket.length >= TONLINK_MAX_PER_WINDOW) {
    tonlinkHits.set(key, bucket);
    return true;
  }
  bucket.push(now);
  tonlinkHits.set(key, bucket);
  return false;
}

const TONLINK_ERRORS = {
  ACCOUNT_NOT_FOUND: [404, "Аккаунт с таким номером не найден. Проверьте номер или откройте @shapitogrambot."],
  DELIVERY_FAILED: [502, "Не удалось отправить код. Откройте @shapitogrambot, нажмите /start и повторите."],
  TOO_MANY_REQUESTS: [429, "Слишком много запросов кода. Попробуйте через несколько минут."],
  TOO_MANY_ATTEMPTS: [429, "Слишком много неверных попыток. Запросите новый код."],
  CODE_INVALID: [400, "Неверный код."],
  CODE_EXPIRED: [410, "Код истёк. Запросите новый."],
};

function readJsonBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    let tooLarge = false;
    request.on("data", (chunk) => {
      size += chunk.length;
      if (size > 16_384) tooLarge = true;
      else chunks.push(chunk);
    });
    request.on("end", () => {
      if (tooLarge) return reject(new Error("TOO_LARGE"));
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}"));
      } catch {
        reject(new Error("INVALID_JSON"));
      }
    });
    request.on("error", () => reject(new Error("INVALID_JSON")));
  });
}

async function handleTonlink(request, response) {
  if (tonlinkLimited(request.socket.remoteAddress)) {
    return json(response, 429, { error: "rate_limited", message: "Слишком много запросов. Попробуйте позже." });
  }
  const url = new URL(request.url, "http://127.0.0.1");
  const path = url.pathname.replace(/\\/+$/, "");
  const fail = (status, code, message) => json(response, status, { error: code, message });
  try {
    if (path === "/tonlink/request" && request.method === "POST") {
      const body = await readJsonBody(request);
      const phone = normalizePhoneInput(body.phone);
      const wallet = normalizeWalletAddress(body.wallet);
      if (!phone) return fail(400, "bad_phone", "Введите номер телефона.");
      if (!wallet) return fail(400, "bad_wallet", "Некорректный адрес кошелька.");
      const result = await walletLink.requestLink(phone, wallet);
      return json(response, 200, { ok: true, expiresIn: result.expiresIn });
    }
    if (path === "/tonlink/confirm" && request.method === "POST") {
      const body = await readJsonBody(request);
      const phone = normalizePhoneInput(body.phone);
      const code = String(body.code ?? "").trim();
      if (!phone) return fail(400, "bad_phone", "Введите номер телефона.");
      const result = await walletLink.confirmLink(phone, code);
      return json(response, 200, result);
    }
    if (path === "/tonlink/status" && request.method === "GET") {
      const wallet = normalizeWalletAddress(url.searchParams.get("wallet"));
      if (!wallet) return fail(400, "bad_wallet", "Некорректный адрес кошелька.");
      return json(response, 200, await walletLink.status(wallet));
    }
    if (path === "/tonlink/owner" && request.method === "GET") {
      // Used by the web client to show which account holds a gifted NFT; the
      // response is intentionally display-only.
      const address = normalizeWalletAddress(url.searchParams.get("address"));
      if (!address) return fail(400, "bad_address", "Некорректный адрес.");
      const status = await walletLink.status(address);
      if (!status.linked) return json(response, 200, { found: false });
      return json(response, 200, {
        found: true,
        account: {
          name: status.account.firstName || status.account.username || "",
          username: status.account.username || "",
          phone: status.account.phone || "",
        },
      });
    }
    if (path === "/tonlink/unlink" && request.method === "POST") {
      const body = await readJsonBody(request);
      const phone = normalizePhoneInput(body.phone);
      const wallet = normalizeWalletAddress(body.wallet);
      if (!phone) return fail(400, "bad_phone", "Введите номер телефона.");
      if (!wallet) return fail(400, "bad_wallet", "Некорректный адрес кошелька.");
      return json(response, 200, await walletLink.unlink(wallet, phone));
    }
    return fail(404, "not_found", "Неизвестный метод.");
  } catch (error) {
    const mapped = TONLINK_ERRORS[error?.code];
    if (mapped) return fail(mapped[0], String(error.code).toLowerCase(), mapped[1]);
    console.error("tonlink request failed", path, error);
    return fail(400, "failed", "Не удалось выполнить операцию. Попробуйте позже.");
  }
}

const server = http.createServer('''

old_server = "const server = http.createServer("
assert old_server in text, "server anchor missing"
text = text.replace(old_server, handler, 1)

with io.open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print("index.js patched")
