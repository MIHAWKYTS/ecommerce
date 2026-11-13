"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { searchCategories } from "@/lib/categorias";
import { useStore } from "@/app/store";

function CategorySearch({ className = "" }: { className?: string }) {
  const { catalog } = useStore();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const box = useRef<HTMLDivElement>(null);
  const results = catalog ? searchCategories(catalog, q) : [];

  useEffect(() => {
    const close = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  function go(id: string) {
    setOpen(false); setQ("");
    router.push(`/categoria/${id}`);
  }

  return (
    <div ref={box} className={`relative ${className}`}>
      <label htmlFor="busca-cat" className="sr-only">Buscar categorias</label>
      <input id="busca-cat" type="search" autoComplete="off" placeholder="Buscar categorias (ex.: geladeiras)"
        className="h-10 w-full rounded-lg border-0 bg-white px-4 pr-10 text-sm text-ink shadow-sm outline-none ring-brand-100 placeholder:text-muted focus:ring-4"
        value={q}
        onChange={(e) => { setQ(e.target.value); setOpen(true); setActive(0); }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, results.length - 1)); }
          if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
          if (e.key === "Enter" && results[active]) { e.preventDefault(); go(results[active].id); }
          if (e.key === "Escape") setOpen(false);
        }} />
      <svg aria-hidden viewBox="0 0 24 24" className="pointer-events-none absolute right-3 top-2.5 h-5 w-5 text-muted" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" strokeLinecap="round" />
      </svg>
      {open && q.trim() && (
        <ul role="listbox" className="absolute left-0 right-0 top-12 z-30 overflow-hidden rounded-lg border border-line bg-white py-1 text-sm text-ink shadow-xl">
          {results.length === 0 && <li className="px-4 py-2 text-muted">Nenhuma categoria encontrada.</li>}
          {results.map((c, i) => (
            <li key={c.id} role="option" aria-selected={i === active}>
              <button type="button" onMouseEnter={() => setActive(i)} onClick={() => go(c.id)}
                className={`flex w-full items-center justify-between gap-3 px-4 py-2 text-left ${i === active ? "bg-brand-50" : ""}`}>
                <span>{c.display}</span>
                <span className="text-xs text-muted">{c.parentDisplay}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function CartButton() {
  const { user, cartCount } = useStore();
  return (
    <Link href="/carrinho" className="relative flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-white/10" aria-label={`Carrinho${user ? `, ${cartCount} itens` : ""}`}>
      <svg aria-hidden viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M3 4h2l2.4 11.2a1 1 0 0 0 1 .8h8.9a1 1 0 0 0 1-.8L20 8H6.2" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="9" cy="20" r="1.3" /><circle cx="17" cy="20" r="1.3" />
      </svg>
      <span className="hidden text-sm font-medium sm:inline">Carrinho</span>
      {user && cartCount > 0 && (
        <span data-testid="cart-count" className="absolute -right-1 -top-1 min-w-5 rounded-full bg-cta px-1.5 text-center text-xs font-bold leading-5 text-ink">
          {cartCount > 99 ? "99+" : cartCount}
        </span>
      )}
    </Link>
  );
}

function Account() {
  const { user, ready, signOut } = useStore();
  if (!ready) return <div className="h-8 w-20 animate-pulse rounded-md bg-white/20" />;
  if (!user) return <Link href="/login" className="rounded-lg px-3 py-1.5 text-sm font-medium hover:bg-white/10">Entrar</Link>;
  return (
    <div className="flex items-center gap-1 text-sm">
      <Link href="/pedidos" className="flex flex-col rounded-lg px-2 py-1 leading-tight hover:bg-white/10">
        <span className="max-w-32 truncate text-xs text-brand-100">Olá, {user.name.split(" ")[0]}</span>
        <span className="font-medium">Meus pedidos</span>
      </Link>
      <button onClick={signOut} className="cursor-pointer rounded-lg px-2 py-1.5 font-medium hover:bg-white/10">Sair</button>
    </div>
  );
}

export default function Header() {
  return (
    <header className="sticky top-0 z-20 bg-brand-600 text-white shadow-md">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3 md:gap-6">
        <Link href="/" className="flex shrink-0 items-center gap-2 font-extrabold tracking-tight">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-cta text-brand-900">B2</span>
          <span className="text-lg">Loja BD II</span>
        </Link>
        <CategorySearch className="hidden flex-1 md:block" />
        <nav className="ml-auto flex items-center gap-1 md:ml-0">
          <Account />
          <CartButton />
        </nav>
      </div>
      <div className="px-4 pb-3 md:hidden">
        <CategorySearch />
      </div>
    </header>
  );
}
