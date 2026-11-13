"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { EmptyState, ErrorState } from "@/components/States";
import StatusBadge from "@/components/StatusBadge";
import { api, Order } from "@/lib/api";
import { brl, dataHora, shortId } from "@/lib/format";
import { useRequireLogin } from "../store";

export default function Pedidos() {
  const logged = useRequireLogin();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [err, setErr] = useState("");

  const load = useCallback(() => {
    setErr("");
    api<Order[]>("/orders").then(setOrders).catch((e) => setErr(e.message));
  }, []);
  useEffect(() => { if (logged) load(); }, [logged, load]);

  if (!logged) return null;
  return (
    <>
      <h1 className="mb-5 text-2xl font-bold">Meus pedidos</h1>
      {err && <ErrorState message={err} onRetry={load} />}
      {!orders && !err && <div className="space-y-3" aria-label="Carregando pedidos">{[0, 1, 2].map((i) => <div key={i} className="skeleton h-20" />)}</div>}
      {orders?.length === 0 && <EmptyState title="Você ainda não fez pedidos" text="Quando finalizar uma compra, ela aparece aqui." action={{ href: "/", label: "Começar a comprar" }} />}
      {orders && orders.length > 0 && (
        <ul className="space-y-3">
          {orders.map((o) => (
            <li key={o.id}>
              <Link href={`/pedidos/${o.id}`} className="card flex flex-wrap items-center gap-x-6 gap-y-2 p-4 transition hover:border-brand-500 hover:shadow-md">
                <div className="min-w-32">
                  <p className="text-xs text-muted">Pedido</p>
                  <p className="font-mono font-semibold">#{shortId(o.id)}</p>
                </div>
                <div className="min-w-32">
                  <p className="text-xs text-muted">Data</p>
                  <p className="text-sm">{dataHora(o.created_at)}</p>
                </div>
                <StatusBadge status={o.status} />
                <p className="ml-auto text-lg font-bold">{brl(o.total)}</p>
                <span className="text-sm font-medium text-brand-600">Ver detalhes ›</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {orders && orders.length === 20 && <p className="mt-4 text-center text-xs text-muted">Mostrando os 20 pedidos mais recentes.</p>}
    </>
  );
}
