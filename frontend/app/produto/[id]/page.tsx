"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import ProductImage from "@/components/ProductImage";
import QtyControl from "@/components/QtyControl";
import { Alert, Breadcrumb, ErrorState } from "@/components/States";
import { api, Cart, getToken, Product, Stock } from "@/lib/api";
import { brl } from "@/lib/format";
import { useStore } from "../../store";

export default function Produto() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { catalog, setCart } = useStore();
  const [p, setP] = useState<Product | null>(null);
  const [stock, setStock] = useState<number | null>(null);
  const [qty, setQty] = useState(1);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [loadErr, setLoadErr] = useState("");

  const load = useCallback(() => {
    setLoadErr(""); setP(null); setStock(null);
    api<Product>(`/products/${id}`).then(setP).catch((e) => setLoadErr(e.message));
    api<Stock>(`/products/${id}/stock`).then((s) => setStock(s.available)).catch(() => setStock(null));
  }, [id]);
  useEffect(load, [load]);

  const cat = p ? catalog?.byId.get(p.category_id) : undefined;
  const soldOut = stock === 0;
  const max = Math.min(stock ?? 999, 999);

  async function add() {
    setErr(""); setMsg("");
    if (!getToken()) return router.push(`/login?next=${encodeURIComponent(`/produto/${id}`)}`);
    setBusy(true);
    try {
      const cart = await api<Cart>("/cart");
      const cur = cart.items.find((i) => i.product_id === id)?.quantity ?? 0;
      const total = Math.min(cur + qty, max);
      if (total <= cur) { setErr(`Você já tem ${cur} no carrinho, o máximo disponível.`); return; }
      setCart(await api<Cart>(`/cart/items/${id}`, { method: "PUT", body: JSON.stringify({ quantity: total }) }));
      setMsg(total - cur === qty ? `${qty} ${qty === 1 ? "unidade adicionada" : "unidades adicionadas"} ao carrinho.`
        : `Adicionamos ${total - cur} (limite do estoque).`);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (loadErr) return <ErrorState message={loadErr === "Produto não encontrado" ? "Este produto não existe ou não está mais à venda." : loadErr} onRetry={load} />;

  if (!p) {
    return (
      <div className="grid gap-8 md:grid-cols-2" aria-label="Carregando produto">
        <div className="skeleton aspect-square rounded-2xl" />
        <div className="space-y-4"><div className="skeleton h-8 w-3/4" /><div className="skeleton h-10 w-1/3" /><div className="skeleton h-24 w-full" /></div>
      </div>
    );
  }

  return (
    <>
      <Breadcrumb items={[
        { href: "/", label: "Início" },
        ...(cat ? [{ href: `/categoria/${cat.id}`, label: cat.display }] : []),
        { label: p.name },
      ]} />
      <div className="grid gap-6 md:grid-cols-2 md:gap-10">
        <div className="card overflow-hidden">
          <ProductImage id={p.id} name={p.name} src={p.images[0]} />
        </div>

        <div className="flex flex-col gap-4">
          <div>
            <h1 className="text-2xl font-bold md:text-3xl">{p.name}</h1>
            <p className="mt-1 text-sm text-muted">Código {p.sku}</p>
          </div>

          <div className="card space-y-4 p-5">
            <p className="text-3xl font-extrabold">{brl(p.price)}</p>
            {stock === null ? (
              <div className="skeleton h-5 w-40" />
            ) : soldOut ? (
              <p className="inline-flex w-fit rounded-full bg-rose-50 px-3 py-1 text-sm font-semibold text-rose-700 ring-1 ring-rose-200">Esgotado</p>
            ) : (
              <p className="text-sm font-medium text-emerald-700">
                Em estoque{stock <= 10 ? `: só ${stock} ${stock === 1 ? "unidade" : "unidades"}` : ` (${stock} unidades)`}
              </p>
            )}

            {!soldOut && (
              <div className="flex flex-wrap items-center gap-3">
                <QtyControl value={qty} max={max} onCommit={setQty} disabled={busy || stock === null} />
                <button className="btn-cta flex-1 whitespace-nowrap sm:flex-none sm:px-8" disabled={busy || stock === null} onClick={add}>
                  {busy ? "Adicionando…" : "Adicionar ao carrinho"}
                </button>
              </div>
            )}
            {soldOut && <button className="btn-cta w-full" disabled>Indisponível</button>}

            {msg && <Alert tone="success">{msg} <Link href="/carrinho" className="font-semibold underline">Ver carrinho</Link></Alert>}
            {err && <Alert tone="error">{err}</Alert>}
          </div>

          <div>
            <h2 className="mb-1 font-semibold">Descrição</h2>
            <p className="text-sm leading-relaxed text-muted">{p.description || "Sem descrição."}</p>
          </div>
        </div>
      </div>
    </>
  );
}
