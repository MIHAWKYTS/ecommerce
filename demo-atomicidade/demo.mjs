import { chromium } from "playwright";
import { execSync } from "node:child_process";
import readline from "node:readline/promises";
import { fileURLToPath } from "node:url";

const FRONT = "http://localhost:3000";
const API = "http://localhost:8000";
const ROOT = fileURLToPath(new URL("..", import.meta.url));
const psql = (sql) =>
  execSync(`docker compose exec -T postgres psql -U ecommerce -d ecommerce -qAt -c "${sql}"`, { cwd: ROOT }).toString().trim();
const PRODUCT = process.env.PRODUCT_ID || psql("select id from products where name ilike 'Esteira Brisano BR-1008%' limit 1");
if (!PRODUCT) throw new Error("Esteira Brisano BR-1008 não encontrada no banco; rode o seed ou defina PRODUCT_ID.");
const SLOW = Number(process.env.SLOW ?? 150);

const stock = async () => (await (await fetch(`${API}/products/${PRODUCT}/stock`)).json()).available;

function setStock(n) {
  psql(`update inventory set quantity=${n}, updated_at=now() where product_id='${PRODUCT}'`);
}

async function banner(page, text, color = "#1e293b") {
  await page.evaluate(([t, c]) => {
    let el = document.getElementById("__demo");
    if (!el) {
      el = document.createElement("div");
      el.id = "__demo";
      el.style.cssText = "position:fixed;left:0;right:0;bottom:0;z-index:99999;padding:18px;font:700 22px system-ui;text-align:center;color:#fff;box-shadow:0 -4px 20px #0005;white-space:pre-line";
      document.body.appendChild(el);
    }
    el.style.background = c;
    el.textContent = t;
  }, [text, color]);
}

async function openClient(label, x) {
  const browser = await chromium.launch({
    executablePath: process.env.CHROME || `${process.env.HOME}/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome`,
    headless: false,
    slowMo: SLOW,
    args: [`--window-position=${x},0`, "--window-size=960,1150"],
  });
  const page = await (await browser.newContext({ viewport: null })).newPage();
  return { label, browser, page };
}

async function prepare({ label, page }) {
  const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

  await page.goto(`${FRONT}/login`);
  await banner(page, `${label}: criando conta`);
  await page.getByRole("tab", { name: "Criar conta" }).click();
  await page.fill("#name", `${label} Demo`);
  await page.fill("#email", `demo-${label.toLowerCase().replace(/\s/g, "")}-${id}@teste.com`);
  await page.fill("#password", "senha123");
  await page.getByRole("button", { name: "Cadastrar" }).click();
  await page.waitForURL(`${FRONT}/`);

  await page.goto(`${FRONT}/produto/${PRODUCT}`);
  await banner(page, `${label}: colocando a esteira no carrinho`);
  await page.getByRole("button", { name: "Adicionar ao carrinho" }).click();
  await page.getByText("Ver carrinho").waitFor();

  await page.goto(`${FRONT}/carrinho`);
  await banner(page, `${label}: cadastrando endereço`);
  await page.fill("#a-street", "Av. Lourival Melo Mota");
  await page.fill("#a-number", "100");
  await page.fill("#a-city", "Maceió");
  await page.fill("#a-state", "AL");
  await page.fill("#a-zip_code", "57072-900");
  await page.getByRole("button", { name: "Salvar endereço" }).click();
  await page.getByRole("button", { name: "Finalizar compra" }).waitFor();
  await page.waitForFunction(() => {
    const b = [...document.querySelectorAll("button")].find((x) => x.textContent?.includes("Finalizar compra"));
    return b && !b.disabled;
  });
  await banner(page, `${label}: pronto, aguardando o sinal`);
}

function armClick(page, label, at) {
  return page.evaluate(([at, label]) => new Promise((resolve) => {
    const el = document.getElementById("__demo");
    el.style.background = "#b45309";
    const tick = setInterval(() => {
      const s = Math.ceil((at - Date.now()) / 1000);
      if (s > 0) el.textContent = `${label}: clicando em "Finalizar compra" em ${s}…`;
    }, 100);
    const btn = [...document.querySelectorAll("button")].find((x) => x.textContent?.includes("Finalizar compra"));
    const fire = () => {
      while (Date.now() < at) {}
      clearInterval(tick);
      const t = performance.timeOrigin + performance.now();
      btn.click();
      el.textContent = `${label}: CLICOU!`;
      resolve(t);
    };
    setTimeout(fire, Math.max(0, at - Date.now() - 20));
  }), [at, label]);
}

async function main() {
  console.log("Colocando a esteira com 1 unidade em estoque…");
  setStock(1);
  const antes = await stock();
  console.log("Estoque antes:", antes);
  if (antes !== 1) throw new Error(`O estoque precisa ser exatamente 1 antes da corrida, mas está em ${antes}.`);

  const a = await openClient("Cliente A", 0);
  const b = await openClient("Cliente B", 960);

  await Promise.all([prepare(a), prepare(b)]);

  const at = Date.now() + Number(process.env.WAIT ?? 10) * 1000;
  const resp = (p) => p.waitForResponse((r) => r.url().endsWith("/checkout") && r.request().method() === "POST", { timeout: 30000 });
  const [ra, rb, ta, tb] = await Promise.all([resp(a.page), resp(b.page), armClick(a.page, a.label, at), armClick(b.page, b.label, at)]);

  const results = [];
  for (const [c, r, t] of [[a, ra, ta], [b, rb, tb]]) {
    const ok = r.status() === 200 || r.status() === 201;
    results.push({ cliente: c.label, http: r.status(), resultado: ok ? "COMPROU" : "RECUSADO (estoque insuficiente)", clique_ms: t.toFixed(3) });
    await c.page.waitForTimeout(600);
    await banner(c.page, ok ? `${c.label}: ✔ COMPROU (HTTP ${r.status()})` : `${c.label}: ✖ RECUSADO, sem estoque (HTTP ${r.status()})\nO carrinho foi mantido.`, ok ? "#047857" : "#be123c");
  }

  console.log("\nResultado:");
  console.table(results);
  console.log(`Diferença entre os cliques: ${Math.abs(ta - tb).toFixed(3)} ms`);
  console.log("Estoque depois:", await stock(), "(nunca fica negativo)");

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  await rl.question("\nPressione Enter para fechar as janelas…");
  rl.close();
  await Promise.all([a.browser.close(), b.browser.close()]);
}

main().catch((e) => { console.error(e); process.exit(1); });
