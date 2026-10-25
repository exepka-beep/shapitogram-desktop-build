import { chromium } from "playwright";

const browser = await chromium.launch();
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push("PAGEERROR: " + e.message));
page.on("console", (m) => { if (m.type() === "error") errors.push("CONSOLE: " + m.text().slice(0, 200)); });
page.on("response", (r) => { if (r.status() >= 400) errors.push("HTTP " + r.status() + " " + r.url()); });

const resp = await page.goto("https://ton.shapitogram.xyz/", { waitUntil: "networkidle", timeout: 45000 });
console.log("STATUS", resp?.status());

// Создаём кошелёк, чтобы добраться до главного экрана с баннером привязки.
await page.getByRole("button", { name: "Создать кошелёк" }).first().click();
await page.getByRole("button", { name: /^Создать кошелёк$/ }).last().click();
await page.getByRole("button", { name: /Я сохранил/ }).click();
await page.waitForTimeout(2500);

const body = ((await page.textContent("body")) ?? "").replace(/\s+/g, " ");
console.log("HOME:", body.slice(0, 260));

// Открываем экран привязки тремя путями: баннер на главной и пункт в настройках.
await page.getByText("Привязать аккаунт").first().click();
await page.waitForTimeout(800);
const linkBody = ((await page.textContent("body")) ?? "").replace(/\s+/g, " ");
console.log("LINK_SCREEN:", linkBody.slice(0, 300));
console.log("HAS_PHONE_FIELD:", await page.locator('input[placeholder*="+7"]').count());

// Проверяем сам эндпоинт привязки с домена кошелька.
const status = await page.evaluate(async () => {
  const r = await fetch("/tonlink/status?wallet=EQAUhGdr4iyhXsUIfKIzrd6fM-hSVwy5Y9nYSWyj5-qDdx5Q");
  return { status: r.status, body: await r.text() };
});
console.log("TONLINK_STATUS:", JSON.stringify(status));

console.log("ERRORS:", JSON.stringify(errors, null, 2));
await browser.close();
