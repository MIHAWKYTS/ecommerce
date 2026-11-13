"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import ProductImage from "@/components/ProductImage";
import QtyControl from "@/components/QtyControl";
import { Alert, EmptyState, ErrorState } from "@/components/States";
import { Address, api, ApiError, Cart } from "@/lib/api";
import { brl, PAYMENT_METHODS } from "@/lib/format";
import { useRequireLogin, useStore } from "../store";

const EMPTY_ADDR = { street: "", number: "", complement: "", city: "", state: "", zip_code: "" };
const ADDR_FIELDS: { k: keyof typeof EMPTY_ADDR; label: string; span: string; max: number; req: boolean; auto?: string }[] = [
  { k: "street", label: "Rua", span: "sm:col-span-4", max: 200, req: true, auto: "address-line1" },
  { k: "number", label: "Número", span: "sm:col-span-2", max: 20, req: true },
  { k: "complement", label: "Complemento (opcional)", span: "sm:col-span-6", max: 100, req: false, auto: "address-line2" },
  { k: "city", label: "Cidade", span: "sm:col-span-3", max: 100, req: true, auto: "address-level2" },
  { k: "state", label: "UF", span: "sm:col-span-1", max: 2, req: true, auto: "address-level1" },
  { k: "zip_code", label: "CEP", span: "sm:col-span-2", max: 10, req: true, auto: "postal-code" },
];

export default function Carrinho() {
  const logged = useRequireLogin();
  const router = useRouter();
  const { setCart: setCount } = useStore();
  const [cart, setCart] = useState<Cart | null>(null);
  const [addrs, setAddrs] = useState<Address[]>([]);
  const [addr, setAddr] = useState("");
  const [method, setMethod] = useState("pix");
  const [loadErr, setLoadErr] = useState("");
  const [err, setErr] = useState("");
  const [busyItem, setBusyItem] = useState<string | null>(null);
  const [paying, setPaying] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_ADDR);
  const [formErr, setFormErr] = useState("");
  const [savingAddr, setSavingAddr] = useState(false);

  const load = useCallback(async () => {
    setLoadErr("");
    try {
      const [c, a] = await Promise.all([api<Cart>("/cart"), api<Address[]>("/addresses")]);
      setCart(c); setCount(c); setAddrs(a);
      setAddr((cur) => cur || a[0]?.id || "");
      if (a.length === 0) setShowForm(true);
    } catch (e) {
      setLoadErr((e as Error).message);
    }
  }, [setCount]);
  useEffect(() => { if (logged) load(); }, [logged, load]);

  async function setQty(pid: string, q: number) {
    setErr(""); setBusyItem(pid);
    try {
      const c = await api<Cart>(`/cart/items/${pid}`, { method: "PUT", body: JSON.stringify({ quantity: q }) });
      setCart(c); setCount(c);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusyItem(null);
    }
  }

  async function saveAddr(e: React.FormEvent) {
    e.preventDefault(); setFormErr(""); setSavingAddr(true);
    try {
      const body = { ...form, state: form.state.toUpperCase(), complement: form.complement || null };
      const r = await api<{ id: string }>("/addresses", { method: "POST", body: JSON.stringify(body) });
      setAddrs(await api<Address[]>("/addresses"));
      setAddr(r.id);
      setForm(EMPTY_ADDR);
      setShowForm(false);
    } catch (e) {
      setFormErr((e as Error).message);
    } finally {
      setSavingAddr(false);
    }
  }

  async function checkout() {
    setErr(""); setPaying(true);
    try {
      const r = await api<{ order_id: string }>("/checkout", { method: "POST", body: JSON.stringify({ address_id: addr, method }) });
      setCount({ items: [], total: "0" });
      router.push(`/pedidos/${r.order_id}?novo=1`);
    } catch (e) {
      const status = e instanceof ApiError ? e.status : 0;
      setErr(status === 409
        ? "Estoque insuficiente para pelo menos um item. Seu carrinho foi mantido: reduza as quantidades ou remova o item e tente de novo."
        : (e as Error).message);
      setPaying(false);
      await load();
    }
  }

  if (!logged) return null;
  if (loadErr) return <ErrorState message={loadErr} onRetry={load} />;
  if (!cart) {
    return (
      <div className="grid gap-6 lg:grid-cols-[1fr_360px]" aria-label="Carregando carrinho">
        <div className="space-y-3">{[0, 1, 2].map((i) => <div key={i} className="skeleton h-24" />)}</div>
        <div className="skeleton h-72" />
      </div>
    );
  }
  if (cart.items.length === 0) {
    return (
      <>
        <h1 className="mb-5 text-2xl font-bold">Carrinho</h1>
        <EmptyState title="Seu carrinho está vazio" text="Navegue pelas categorias e adicione produtos." action={{ href: "/", label: "Ver categorias" }} />
      </>
    );
  }

  const units = cart.items.reduce((n, i) => n + i.quantity, 0);
  return (
    <>
      <h1 className="mb-5 text-2xl font-bold">Carrinho <span className="text-base font-normal text-muted">({units} {units === 1 ? "item" : "itens"})</span></h1>
      {err && <div className="mb-4"><Alert tone="error">{err}</Alert></div>}

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_380px]">
        <ul className="card divide-y divide-line">
          {cart.items.map((i) => (
            <li key={i.product_id} className="flex gap-3 p-4 sm:gap-4">
              <Link href={`/produto/${i.product_id}`} className="w-20 shrink-0 overflow-hidden rounded-lg sm:w-24">
                <ProductImage id={i.product_id} name={i.name} />
              </Link>
              <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <Link href={`/produto/${i.product_id}`} className="font-medium hover:text-brand-600">{i.name}</Link>
                  <p className="text-sm text-muted">{brl(i.price)} cada</p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <QtyControl value={i.quantity} max={i.available} onCommit={(q) => setQty(i.product_id, q)} disabled={busyItem === i.product_id || paying} />
                  <span className="w-24 text-right font-semibold">{brl(i.subtotal)}</span>
                  <button className="cursor-pointer text-sm text-rose-700 hover:underline disabled:opacity-50" disabled={busyItem === i.product_id || paying}
                    onClick={() => setQty(i.product_id, 0)}>Remover</button>
                </div>
              </div>
            </li>
          ))}
        </ul>

        <aside className="card space-y-5 p-5 lg:sticky lg:top-24">
          <h2 className="text-lg font-bold">Resumo do pedido</h2>

          <section className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold">Endereço de entrega</h3>
              {!showForm && <button className="cursor-pointer text-sm font-medium text-brand-600 hover:underline" onClick={() => setShowForm(true)}>+ Novo</button>}
            </div>
            {addrs.length > 0 && (
              <select aria-label="Endereço de entrega" className="field" value={addr} onChange={(e) => setAddr(e.target.value)}>
                {addrs.map((a) => (
                  <option key={a.id} value={a.id}>{a.street}, {a.number}{a.complement ? ` (${a.complement})` : ""} · {a.city}/{a.state}</option>
                ))}
              </select>
            )}
            {showForm && (
              <form onSubmit={saveAddr} className="space-y-3 rounded-lg bg-page p-3">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-6 lg:grid-cols-2">
                  {ADDR_FIELDS.map((f) => (
                    <div key={f.k} className={`col-span-2 ${f.span} lg:col-span-2`}>
                      <label htmlFor={`a-${f.k}`} className="label">{f.label}</label>
                      <input id={`a-${f.k}`} className="field" required={f.req} maxLength={f.max} minLength={f.k === "state" ? 2 : undefined}
                        autoComplete={f.auto} value={form[f.k]} onChange={(e) => setForm({ ...form, [f.k]: e.target.value })} />
                    </div>
                  ))}
                </div>
                {formErr && <Alert tone="error">{formErr}</Alert>}
                <div className="flex gap-2">
                  <button type="submit" className="btn-primary flex-1" disabled={savingAddr}>{savingAddr ? "Salvando…" : "Salvar endereço"}</button>
                  {addrs.length > 0 && <button type="button" className="btn-ghost" onClick={() => { setShowForm(false); setForm(EMPTY_ADDR); }}>Cancelar</button>}
                </div>
              </form>
            )}
          </section>

          <fieldset className="space-y-2">
            <legend className="mb-2 text-sm font-semibold">Pagamento</legend>
            {PAYMENT_METHODS.map((m) => (
              <label key={m.id} className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm transition ${method === m.id ? "border-brand-500 bg-brand-50" : "border-line hover:bg-page"}`}>
                <input type="radio" name="method" value={m.id} checked={method === m.id} onChange={() => setMethod(m.id)} className="accent-brand-600" />
                <span className="flex-1 font-medium">{m.label}</span>
                <span className="text-xs text-muted">{m.hint}</span>
              </label>
            ))}
          </fieldset>

          <div className="space-y-1 border-t border-line pt-4">
            <div className="flex justify-between text-sm text-muted"><span>{units} {units === 1 ? "item" : "itens"}</span><span>{brl(cart.total)}</span></div>
            <div className="flex justify-between pt-1 text-xl font-extrabold"><span>Total</span><span>{brl(cart.total)}</span></div>
          </div>

          <button className="btn-cta w-full py-3 text-base" disabled={!addr || paying || busyItem !== null} onClick={checkout}>
            {paying ? "Processando…" : "Finalizar compra"}
          </button>
          {!addr && <p className="text-center text-xs text-muted">Cadastre um endereço para finalizar.</p>}
        </aside>
      </div>
    </>
  );
}
