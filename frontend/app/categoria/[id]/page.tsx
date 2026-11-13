"use client";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import ProductCard, { GRID, ProductCardSkeleton } from "@/components/ProductCard";
import { Breadcrumb, EmptyState, ErrorState } from "@/components/States";
import { api, PAGE_SIZE, Product } from "@/lib/api";
import { useStore } from "../../store";

export default function Categoria() {
  const { id } = useParams<{ id: string }>();
  const { catalog } = useStore();
  const cat = catalog?.byId.get(id);
  const [items, setItems] = useState<Product[]>([]);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const load = useCallback(async (p: number) => {
    setLoading(true); setErr("");
    try {
      const got = await api<Product[]>(`/categories/${id}/products?page=${p}`);
      setItems((cur) => (p === 1 ? got : [...cur, ...got]));
      setPage(p);
      setHasMore(got.length === PAGE_SIZE);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { setItems([]); setPage(0); setHasMore(true); load(1); }, [load]);

  return (
    <>
      <Breadcrumb items={[
        { href: "/", label: "Início" },
        ...(cat?.parentDisplay ? [{ label: cat.parentDisplay }] : []),
        { label: cat?.display ?? "Categoria" },
      ]} />
      <div className="mb-5 flex flex-wrap items-end justify-between gap-2">
        {cat ? <h1 className="text-2xl font-bold">{cat.display}</h1> : <div className="skeleton h-8 w-56" />}
        {items.length > 0 && <p className="text-sm text-muted">{items.length} produtos exibidos · ordem alfabética</p>}
      </div>

      {err && page === 0 && <ErrorState message={err} onRetry={() => load(1)} />}

      {!err && page === 0 && loading && (
        <div className={GRID} aria-label="Carregando produtos">
          {Array.from({ length: 10 }, (_, i) => <ProductCardSkeleton key={i} />)}
        </div>
      )}

      {page > 0 && items.length === 0 && (
        <EmptyState title="Nenhum produto nesta categoria" text="Escolha outra subcategoria na página inicial." action={{ href: "/", label: "Ver categorias" }} />
      )}

      {items.length > 0 && (
        <div className={GRID}>
          {items.map((p) => <ProductCard key={p.id} p={p} />)}
          {loading && Array.from({ length: 5 }, (_, i) => <ProductCardSkeleton key={`s${i}`} />)}
        </div>
      )}

      {err && page > 0 && <p className="mt-4 text-center text-sm text-rose-700" role="alert">{err}</p>}

      {page > 0 && hasMore && items.length > 0 && (
        <div className="mt-6 flex justify-center">
          <button className="btn-ghost min-w-48" disabled={loading} onClick={() => load(page + 1)}>
            {loading ? "Carregando…" : "Carregar mais"}
          </button>
        </div>
      )}
      {page > 0 && !hasMore && items.length > 0 && (
        <p className="mt-6 text-center text-sm text-muted">Você chegou ao fim desta categoria.</p>
      )}
    </>
  );
}
