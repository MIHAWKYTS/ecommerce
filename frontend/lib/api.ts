export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const PAGE_SIZE = 20;

export type Category = { id: string; parent_id: string | null; name: string; slug: string };
export type Product = { id: string; category_id: string; sku: string; name: string; description: string | null; price: string; images: string[] };
export type Stock = { product_id: string; available: number };
export type CartItem = { product_id: string; name: string; price: string; quantity: number; subtotal: string; available: number };
export type Cart = { items: CartItem[]; total: string };
export type Address = { id: string; street: string; number: string; complement: string | null; city: string; state: string; zip_code: string };
export type Order = { id: string; status: string; total: string; created_at: string };
export type OrderItem = { product_id: string; name: string; quantity: number; unit_price: string; subtotal: string };
export type OrderDetail = Order & {
  items_total: string; distinct_items: number; total_units: number;
  payment: { method: string | null; status: string | null }; items: OrderItem[];
};
export type User = { id: string; name: string };

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export const SESSION_EXPIRED = "session-expired";

export function getToken(): string | null {
  try { return localStorage.getItem("session_id"); } catch { return null; }
}
export function setToken(t: string | null) {
  try { t ? localStorage.setItem("session_id", t) : localStorage.removeItem("session_id"); } catch {}
}

export async function api<T>(path: string, init: RequestInit & { silent401?: boolean } = {}): Promise<T> {
  const { silent401, ...req } = init;
  const token = getToken();
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, {
      ...req,
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...req.headers },
    });
  } catch {
    throw new ApiError(0, "Não foi possível falar com o servidor. Verifique a conexão e tente de novo.");
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && token) {
      setToken(null);
      if (!silent401) window.dispatchEvent(new Event(SESSION_EXPIRED));
    }
    const d = (data as { detail?: unknown }).detail;
    throw new ApiError(res.status, typeof d === "string" ? d : res.status === 422 ? "Dados inválidos." : "Erro na requisição.");
  }
  return data as T;
}

export const cartCount = (c: Cart | null | undefined) => (c ? c.items.reduce((n, i) => n + i.quantity, 0) : 0);
