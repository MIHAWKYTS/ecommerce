"use client";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, Cart, cartCount, Category, getToken, SESSION_EXPIRED, setToken, User } from "@/lib/api";
import { buildCatalog, CatalogTree } from "@/lib/categorias";

type Store = {
  user: User | null;
  ready: boolean;
  cartCount: number;
  setCart: (c: Cart) => void;
  refreshCart: () => Promise<void>;
  catalog: CatalogTree | null;
  catalogError: string;
  reloadCatalog: () => void;
  signIn: (sessionId: string, user: User) => void;
  signOut: () => Promise<void>;
};

const Ctx = createContext<Store | null>(null);

export function useStore() {
  const s = useContext(Ctx);
  if (!s) throw new Error("useStore fora do StoreProvider");
  return s;
}

export function useRequireLogin() {
  const router = useRouter();
  const pathname = usePathname();
  const [ok, setOk] = useState(false);
  useEffect(() => {
    if (getToken()) setOk(true);
    else router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [router, pathname]);
  return ok;
}

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [count, setCount] = useState(0);
  const [cats, setCats] = useState<Category[] | null>(null);
  const [catalogError, setCatalogError] = useState("");

  const refreshCart = useCallback(async () => {
    if (!getToken()) { setCount(0); return; }
    try { setCount(cartCount(await api<Cart>("/cart", { silent401: true }))); } catch {}
  }, []);

  const setCart = useCallback((c: Cart) => setCount(cartCount(c)), []);
  const catalog = useMemo(() => (cats ? buildCatalog(cats) : null), [cats]);

  const reloadCatalog = useCallback(() => {
    setCatalogError(""); setCats(null);
    api<Category[]>("/categories").then(setCats).catch((e) => setCatalogError(e.message));
  }, []);

  useEffect(() => {
    reloadCatalog();
    if (!getToken()) { setReady(true); return; }
    api<User>("/auth/me", { silent401: true })
      .then((u) => { setUser(u); return refreshCart(); })
      .catch(() => setUser(null))
      .finally(() => setReady(true));
  }, [reloadCatalog, refreshCart]);

  useEffect(() => {
    function expired() {
      setUser(null); setCount(0);
      if (!pathname.startsWith("/login")) router.push(`/login?next=${encodeURIComponent(pathname)}&expirada=1`);
    }
    window.addEventListener(SESSION_EXPIRED, expired);
    return () => window.removeEventListener(SESSION_EXPIRED, expired);
  }, [router, pathname]);

  const value = useMemo<Store>(() => ({
    user, ready, cartCount: count,
    setCart,
    refreshCart,
    catalog,
    catalogError, reloadCatalog,
    signIn: (sid, u) => { setToken(sid); setUser(u); refreshCart(); },
    signOut: async () => {
      await api("/auth/logout", { method: "POST", silent401: true }).catch(() => {});
      setToken(null); setUser(null); setCount(0);
      router.push("/");
    },
  }), [user, ready, count, setCart, catalog, catalogError, refreshCart, reloadCatalog, router]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
