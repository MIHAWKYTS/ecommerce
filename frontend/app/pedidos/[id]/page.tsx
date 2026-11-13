"use client";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import ProductImage from "@/components/ProductImage";
import { Breadcrumb, ErrorState } from "@/components/States";
import StatusBadge from "@/components/StatusBadge";
import { api, OrderDetail } from "@/lib/api";
import { brl, dataHora, paymentMethod, paymentStatus, shortId } from "@/lib/format";
import { useRequireLogin } from "../../store";

function Detalhe() {
  const logged = useRequireLogin();
  const { id } = useParams<{ id: string }>();
  const novo = useSearchParams().get("novo") === "1";
  const [o, setO] = useState<OrderDetail | null>(null);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    setErr("");
    api<OrderDetail>(`/orders/${id}`).then(setO).catch((e) => setErr(e.message));
  }, [id]);
  useEffect(() => { if (logged) load(); }, [logged, load]);

  if (!logged) return null;
  if (err) return <ErrorState message={err === "Pedido não encontrado" ? "Pedido não encontrado na sua conta." : err} onRetry={load} />;
  if (!o) return <div className="space-y-4" aria-label="Carregando pedido"><div className="skeleton h-32" /><div className="skeleton h-64" /></div>;

  return (
    <>
      <Breadcrumb items={[{ href: "/pedidos", label: "Meus pedidos" }, { label: `#${shortId(o.id)}` }]} />

      {novo && (
        <section role="status" className="mb-6 flex flex-col items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-5 sm:flex-row sm:items-center">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-2xl text-white" aria-hidden>✓</span>
          <div className="flex-1">
            <h1 className="text-xl font-bold text-emerald-900">Pedido confirmado!</h1>
            <p className="text-sm text-emerald-800">
              Pedido <strong className="font-mono">#{shortId(o.id)}</strong> no valor de <strong>{brl(o.total)}</strong>, pagamento {paymentStatus(o.payment.status).toLowerCase()}.
            </p>
          </div>
          <Link href="/" className="btn-ghost">Continuar comprando</Link>
        </section>
      )}

      <div className="grid items-start gap-6 lg:grid-cols-[1fr_320px]">
        <section className="card overflow-hidden">
          <header className="flex flex-wrap items-center gap-3 border-b border-line p-4">
            {novo ? <h2 className="text-lg font-bold">Itens do pedido</h2> : <h1 className="text-lg font-bold">Pedido #{shortId(o.id)}</h1>}
            <StatusBadge status={o.status} />
            <span className="ml-auto text-sm text-muted">{dataHora(o.created_at)}</span>
          </header>
          <ul className="divide-y divide-line">
            {o.items.map((i) => (
              <li key={i.product_id} className="flex items-center gap-3 p-4">
                <Link href={`/produto/${i.product_id}`} className="w-14 shrink-0 overflow-hidden rounded-lg"><ProductImage id={i.product_id} name={i.name} /></Link>
                <div className="min-w-0 flex-1">
                  <Link href={`/produto/${i.product_id}`} className="font-medium hover:text-brand-600">{i.name}</Link>
                  <p className="text-sm text-muted">{i.quantity} × {brl(i.unit_price)}</p>
                </div>
                <span className="font-semibold">{brl(i.subtotal)}</span>
              </li>
            ))}
          </ul>
        </section>

        <aside className="card space-y-4 p-5">
          <h2 className="font-bold">Resumo</h2>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between"><dt className="text-muted">Itens distintos</dt><dd>{o.distinct_items}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Unidades</dt><dd>{o.total_units}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Pagamento</dt><dd>{paymentMethod(o.payment.method)}</dd></div>
            <div className="flex justify-between"><dt className="text-muted">Situação do pagamento</dt><dd>{paymentStatus(o.payment.status)}</dd></div>
          </dl>
          <div className="flex justify-between border-t border-line pt-3 text-lg font-extrabold"><span>Total</span><span>{brl(o.total)}</span></div>
          <p className="text-xs text-muted">Valores congelados no momento da compra.</p>
          <Link href="/pedidos" className="btn-ghost w-full">Voltar aos pedidos</Link>
        </aside>
      </div>
    </>
  );
}

export default function PedidoPage() {
  return <Suspense fallback={<div className="skeleton h-64" />}><Detalhe /></Suspense>;
}
