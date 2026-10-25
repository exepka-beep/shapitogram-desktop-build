import io, sys

PATH = "/root/shapito-store/src/i18n.js"

RU_AFTER = '    otpWarning: "Никому не сообщайте этот код.",'
RU_BLOCK = '''    commandTonlink: "🔗 Кошелёк",
    tonLinkTitle: "🔗 <b>Привязка кошелька {product}</b>",
    tonLinkCode: "🔑 Код: <code>{code}</code>",
    tonLinkHint: "Введите этот код на ton.shapitogram.xyz, чтобы привязать аккаунт к кошельку. Никому не сообщайте код.\\nЕсли вы не запрашивали привязку — просто проигнорируйте это сообщение.",
    tonLinkDone: "✅ Кошелёк <code>{wallet}</code> привязан к аккаунту {product}.\\nТеперь подарки из блокчейна показывают, что их держит ваш аккаунт.",
    tonLinkCommandLinked: "🔗 Привязанный кошелёк: <code>{wallet}</code>\\nОтвязать можно на ton.shapitogram.xyz → Настройки → «Привязка аккаунта».",
    tonLinkCommandNone: "🔗 Кошелёк не привязан.\\nОткройте ton.shapitogram.xyz → Настройки → «Привязка аккаунта» и введите свой номер телефона.",'''

EN_AFTER = '    otpWarning: "Never share this code with anyone.",'
EN_BLOCK = '''    commandTonlink: "🔗 Wallet",
    tonLinkTitle: "🔗 <b>{product} wallet linking</b>",
    tonLinkCode: "🔑 Code: <code>{code}</code>",
    tonLinkHint: "Enter this code on ton.shapitogram.xyz to link your account to the wallet. Never share the code.\\nIf you did not request a link, just ignore this message.",
    tonLinkDone: "✅ Wallet <code>{wallet}</code> is linked to your {product} account.",
    tonLinkCommandLinked: "🔗 Linked wallet: <code>{wallet}</code>",
    tonLinkCommandNone: "🔗 No wallet linked.\\nOpen ton.shapitogram.xyz → Settings → \\"Link account\\" and enter your phone number.",'''

with io.open(PATH, encoding="utf-8") as f:
    text = f.read()

if "tonLinkTitle" in text:
    sys.exit("already patched")

for after, block in ((RU_AFTER, RU_BLOCK), (EN_AFTER, EN_BLOCK)):
    if after not in text:
        sys.exit("anchor not found: %s" % after[:40])
    text = text.replace(after, after + "\n" + block, 1)

with io.open(PATH, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print("i18n patched, tonLinkTitle count:", text.count("tonLinkTitle"))
