/**
 * Login Superusuario en Chrome (headed). No loguea la contraseña.
 * Uso (desde frontend/):
 *   set ERP_EMAIL=... & set ERP_PASSWORD=... & node ../ops/_login_chrome.cjs
 */
const path = require("path");
const fs = require("fs");

// resolver playwright desde frontend/node_modules
const frontendRoot = path.join(__dirname, "..", "frontend");
const playwrightPath = path.join(frontendRoot, "node_modules", "playwright");
const { chromium } = require(playwrightPath);

// Credenciales: env, base64 JSON, o archivo temporal
let email = process.env.ERP_EMAIL || "admin@superozonoglobal.com";
let password = process.env.ERP_PASSWORD || "";
let url = process.env.ERP_URL || "https://127.0.0.1:5173";
let keepMs = Number(process.env.ERP_KEEP_MS || 900000); // 15 min

if (process.env.ERP_AUTH_B64) {
  try {
    const c = JSON.parse(Buffer.from(process.env.ERP_AUTH_B64, "base64").toString("utf8"));
    if (c.email) email = c.email;
    if (c.password) password = c.password;
    if (c.url) url = c.url;
    if (c.keepMs) keepMs = Number(c.keepMs);
  } catch (e) {
    console.error("ERP_AUTH_B64 invalido", e.message);
  }
}

const credCandidates = [
  process.env.ERP_CRED_FILE,
  path.join(__dirname, "smoke-screens", "_login_cred.json"),
  path.join(__dirname, "..", "ops", "smoke-screens", "_login_cred.json"),
].filter(Boolean);

if (!password || password.length < 4) {
  for (const credFile of credCandidates) {
    if (!fs.existsSync(credFile)) continue;
    try {
      const raw = fs.readFileSync(credFile, "utf8").replace(/^\uFEFF/, "");
      const c = JSON.parse(raw);
      if (c.email) email = c.email;
      if (c.password) password = c.password;
      if (c.url) url = c.url;
      if (c.keepMs) keepMs = Number(c.keepMs);
      console.log("CREDS_FROM", credFile);
      break;
    } catch (e) {
      console.error("cred parse fail", credFile, e.message);
    }
  }
}

if (!password) {
  console.error("Falta ERP_PASSWORD / cred file. candidates=", credCandidates);
  process.exit(1);
}

// Prefer ops/smoke-screens del repo (script puede vivir en ops/ o copia en frontend/)
const shots = fs.existsSync(path.join(__dirname, "smoke-screens"))
  ? path.join(__dirname, "smoke-screens")
  : path.join(__dirname, "..", "ops", "smoke-screens");
fs.mkdirSync(shots, { recursive: true });

(async () => {
  let browser;
  try {
    browser = await chromium.launch({
      headless: false,
      channel: "chrome",
      args: ["--start-maximized"],
    });
  } catch {
    browser = await chromium.launch({ headless: false, args: ["--start-maximized"] });
  }

  const context = await browser.newContext({
    ignoreHTTPSErrors: true,
    viewport: null,
  });
  const page = await context.newPage();

  const statusPath = path.join(shots, "login-status.txt");
  const writeStatus = (s) => {
    try {
      fs.writeFileSync(statusPath, s + "\n", "utf8");
    } catch (_) {}
    console.log(s);
  };

  writeStatus("GOTO " + url);
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 90000 });
  await page.waitForTimeout(1500);

  // placeholders del LoginView
  const emailBox = page.locator('input[type="email"], input[placeholder*="usuario@"], input[placeholder*="@"]').first();
  const passBox = page.locator('input[type="password"]').first();
  await emailBox.fill(email);
  await passBox.fill(password);
  writeStatus("FILLED_CREDS");

  const btn = page.getByRole("button", { name: /Acceder/i });
  await btn.click();
  writeStatus("CLICKED_LOGIN");

  try {
    await page.getByText(/Cerrar Sesi[oó]n/i).waitFor({ timeout: 25000 });
    writeStatus("LOGIN_UI_OK");
    await page.screenshot({
      path: path.join(shots, "login-session.png"),
      fullPage: true,
    });
  } catch (e) {
    writeStatus("LOGIN_UI_FAIL " + String(e.message || e).slice(0, 200));
    await page.screenshot({
      path: path.join(shots, "login-fail.png"),
      fullPage: true,
    });
  }

  writeStatus("KEEP_OPEN_MS " + keepMs);
  await page.waitForTimeout(keepMs);
  await browser.close();
  writeStatus("DONE");
})().catch((e) => {
  try {
    fs.writeFileSync(
      path.join(__dirname, "smoke-screens", "login-status.txt"),
      "FATAL " + String(e),
      "utf8"
    );
  } catch (_) {}
  console.error("FATAL", e);
  process.exit(1);
});
