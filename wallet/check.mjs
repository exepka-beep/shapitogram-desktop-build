import { chromium } from "playwright";

const browser = await chromium.launch();
const page = await browser.newPage();
const errors = [];
const failed = [];
page.on("console", (m) => {
  if (m.type() === "error") errors.push(m.text());
});
page.on("pageerror", (e) => errors.push("PAGEERROR: " + e.message));
page.on("requestfailed", (r) => failed.push(r.url() + " :: " + (r.failure()?.errorText ?? "")));
page.on("response", (r) => {
  if (r.status() >= 400) failed.push(r.url() + " :: HTTP " + r.status());
});

const resp = await page.goto("https://shapitogram.xyz/wallet/", { waitUntil: "networkidle", timeout: 45000 });
console.log("STATUS", resp?.status());
await page.waitForTimeout(4000);
const bodyText = (await page.textContent("body"))?.slice(0, 300) ?? "";
console.log("BODY:", JSON.stringify(bodyText));
console.log("ROOT_HTML_LEN:", (await page.innerHTML("#root"))?.length ?? 0);
console.log("ERRORS:", JSON.stringify(errors, null, 2));
console.log("FAILED:", JSON.stringify(failed, null, 2));
await browser.close();
