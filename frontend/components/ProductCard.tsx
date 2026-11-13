import Link from "next/link";
import type { Product } from "@/lib/api";
import { brl } from "@/lib/format";
import ProductImage from "./ProductImage";

export default function ProductCard({ p }: { p: Product }) {
  return (
    <Link href={`/produto/${p.id}`}
      className="card group flex flex-col overflow-hidden transition hover:-translate-y-0.5 hover:shadow-lg hover:shadow-brand-900/5">
      <ProductImage id={p.id} name={p.name} src={p.images[0]} />
      <div className="flex flex-1 flex-col gap-1 p-3">
        <span className="line-clamp-2 text-sm text-ink group-hover:text-brand-600">{p.name}</span>
        <span className="mt-auto text-lg font-bold text-ink">{brl(p.price)}</span>
        <span className="text-xs text-muted">{p.sku}</span>
      </div>
    </Link>
  );
}

export function ProductCardSkeleton() {
  return (
    <div className="card overflow-hidden" aria-hidden>
      <div className="skeleton aspect-square rounded-none" />
      <div className="space-y-2 p-3">
        <div className="skeleton h-4 w-3/4" />
        <div className="skeleton h-6 w-1/2" />
        <div className="skeleton h-3 w-1/3" />
      </div>
    </div>
  );
}

export const GRID = "grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5";
