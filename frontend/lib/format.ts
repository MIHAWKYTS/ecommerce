export const brl = (v: string | number) =>
  Number(v).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export const shortId = (id: string) => id.slice(0, 8).toUpperCase();

export const dataHora = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });

const ORDER_STATUS: Record<string, { label: string; tone: string }> = {
  paid: { label: "Pago", tone: "bg-emerald-50 text-emerald-700 ring-emerald-200" },
  pending: { label: "Pendente", tone: "bg-amber-50 text-amber-700 ring-amber-200" },
  cancelled: { label: "Cancelado", tone: "bg-rose-50 text-rose-700 ring-rose-200" },
};
export const orderStatus = (s: string) => ORDER_STATUS[s] ?? { label: s, tone: "bg-slate-100 text-slate-700 ring-slate-200" };

const PAYMENT_STATUS: Record<string, string> = { approved: "Aprovado", pending: "Pendente", failed: "Recusado" };
export const paymentStatus = (s: string | null) => (s ? PAYMENT_STATUS[s] ?? s : "Sem pagamento");

export const PAYMENT_METHODS = [
  { id: "pix", label: "Pix", hint: "Aprovação imediata" },
  { id: "credit_card", label: "Cartão de crédito", hint: "Pagamento simulado" },
  { id: "boleto", label: "Boleto", hint: "Pagamento simulado" },
] as const;
export const paymentMethod = (m: string | null) => PAYMENT_METHODS.find((p) => p.id === m)?.label ?? m ?? "-";

export function hashHue(s: string) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return h % 360;
}
