"use client";
import Link from "next/link";
import { EmptyState, ErrorState } from "@/components/States";
import CategoryThumb from "@/components/CategoryThumb";
import { useStore } from "./store";

export default function Home() {
  const { catalog, catalogError, reloadCatalog } = useStore();

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-2xl bg-gradient-to-br from-brand-600 to-brand-900 px-6 py-8 text-white md:px-10 md:py-12">
        <p className="text-sm font-medium uppercase tracking-wider text-cta">Catálogo completo</p>
        <h1 className="mt-2 max-w-xl text-3xl font-extrabold leading-tight md:text-4xl">Encontre o que precisa em poucos cliques</h1>
        <p className="mt-3 max-w-xl text-brand-100">
          {catalog ? `${catalog.roots.length} categorias e ${catalog.leaves.length} subcategorias. ` : ""}
          Escolha uma subcategoria abaixo ou use a busca no topo.
        </p>
      </section>

      {catalogError && <ErrorState message={catalogError} onRetry={reloadCatalog} />}

      {!catalog && !catalogError && (
        <div className="space-y-8" aria-label="Carregando categorias">
          {[0, 1, 2].map((i) => (
            <div key={i} className="space-y-3">
              <div className="skeleton h-6 w-40" />
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                {[0, 1, 2, 3, 4].map((j) => <div key={j} className="skeleton h-20" />)}
              </div>
            </div>
          ))}
        </div>
      )}

      {catalog && catalog.roots.length === 0 && (
        <EmptyState title="Nenhuma categoria cadastrada" text="O banco está vazio. Suba o projeto com SEED=1 para carregar o catálogo de exemplo." />
      )}

      {catalog?.roots.map((r) => (
        <section key={r.id} aria-labelledby={`cat-${r.id}`}>
          <h2 id={`cat-${r.id}`} className="mb-3 text-xl font-bold">{r.display}</h2>
          {r.children.length === 0 ? (
            <p className="text-sm text-muted">Sem subcategorias.</p>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {r.children.map((c) => (
                <Link key={c.id} href={`/categoria/${c.id}`}
                  className="card group flex items-center gap-3 p-3 transition hover:-translate-y-0.5 hover:border-brand-500 hover:shadow-md">
                  <CategoryThumb id={c.id} slug={c.slug} label={c.display} />
                  <span className="text-sm font-medium group-hover:text-brand-600">{c.display}</span>
                </Link>
              ))}
            </div>
          )}
        </section>
      ))}
    </div>
  );
}
