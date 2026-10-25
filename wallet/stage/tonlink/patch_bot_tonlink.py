import io, sys

PATH = "/root/shapito-store/src/bot.js"

with io.open(PATH, encoding="utf-8") as f:
    text = f.read()

if '"tonlink"' in text:
    sys.exit("already patched")

# 1. command menu entry
old_list = '''    { command: "promo_code", description: translate(language, "commandPromo") },
  ];'''
new_list = '''    { command: "promo_code", description: translate(language, "commandPromo") },
    { command: "tonlink", description: translate(language, "commandTonlink") },
  ];'''
assert old_list in text, "commandList anchor missing"
text = text.replace(old_list, new_list, 1)

# 2. /tonlink handler before the start handler
old_cmd = '  bot.command("start", async (ctx) => {'
new_cmd = '''  // Wallet linking status for the account behind this chat. The link itself is
  // created on ton.shapitogram.xyz with a code delivered here.
  bot.command("tonlink", async (ctx) => {
    const language = languageOf(ctx.from.id);
    const link = (await db.pool.query(
      "SELECT wallet_address FROM ton_wallet_links WHERE telegram_id = $1",
      [ctx.from.id],
    )).rows[0];
    const message = link
      ? tr(ctx.from.id, "tonLinkCommandLinked", { wallet: escapeHTML(link.wallet_address) })
      : tr(ctx.from.id, "tonLinkCommandNone");
    await ctx.reply(message, { parse_mode: "HTML", link_preview_options: { is_disabled: true } });
  });

  bot.command("start", async (ctx) => {'''
assert old_cmd in text, "start anchor missing"
text = text.replace(old_cmd, new_cmd, 1)

with io.open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print("bot.js patched")
