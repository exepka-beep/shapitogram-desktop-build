-- Wallet <-> account links for ShapitoTON (ton.shapitogram.xyz).
--
-- A user proves control of a phone number with a short code delivered through
-- this bot, then binds that ShapitoGram account to a TON wallet address. One
-- account keeps a single active wallet (re-linking replaces the address), and a
-- wallet address may belong to exactly one account.
CREATE TABLE IF NOT EXISTS ton_wallet_links (
  telegram_id BIGINT PRIMARY KEY,
  server_user_id BIGINT NOT NULL DEFAULT 0,
  chat_id BIGINT NOT NULL,
  phone TEXT NOT NULL,
  wallet_address TEXT NOT NULL,
  linked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ton_wallet_links_address_key ON ton_wallet_links (wallet_address);
CREATE INDEX IF NOT EXISTS ton_wallet_links_phone_idx ON ton_wallet_links (phone);

-- Pending link codes. Attempts are counted per code, so a guessed six-digit
-- code gets at most five tries; a new request invalidates older pending codes
-- for the same phone.
CREATE TABLE IF NOT EXISTS ton_link_codes (
  id BIGSERIAL PRIMARY KEY,
  telegram_id BIGINT NOT NULL,
  chat_id BIGINT NOT NULL,
  phone TEXT NOT NULL,
  wallet_address TEXT NOT NULL,
  code_hash TEXT NOT NULL,
  attempts SMALLINT NOT NULL DEFAULT 0,
  expires_at TIMESTAMPTZ NOT NULL,
  consumed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ton_link_codes_phone_idx ON ton_link_codes (phone, created_at DESC);
