import Link from "next/link";

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="card flex flex-col items-center gap-3 px-6 py-10 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-rose-50 text-2xl text-rose-600">!</div>
      <p className="max-w-md text-sm text-ink">{message}</p>
      {onRetry && <button className="btn-ghost" onClick={onRetry}>Tentar de novo</button>}
    </div>
  );
}

export function EmptyState({ title, text, action }: { title: string; text?: string; action?: { href: string; label: string } }) {
  return (
    <div className="card flex flex-col items-center gap-2 px-6 py-12 text-center">
      <p className="text-lg font-semibold">{title}</p>
      {text && <p className="max-w-md text-sm text-muted">{text}</p>}
      {action && <Link href={action.href} className="btn-primary mt-2">{action.label}</Link>}
    </div>
  );
}

export function Alert({ tone, children }: { tone: "error" | "success" | "info"; children: React.ReactNode }) {
  const cls = {
    error: "border-rose-200 bg-rose-50 text-rose-800",
    success: "border-emerald-200 bg-emerald-50 text-emerald-800",
    info: "border-brand-100 bg-brand-50 text-brand-900",
  }[tone];
  return <div role={tone === "error" ? "alert" : "status"} className={`rounded-lg border px-4 py-3 text-sm ${cls}`}>{children}</div>;
}

export function Breadcrumb({ items }: { items: { href?: string; label: string }[] }) {
  return (
    <nav aria-label="Navegação" className="mb-4 flex flex-wrap items-center gap-1 text-sm text-muted">
      {items.map((it, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <span aria-hidden>›</span>}
          {it.href ? <Link href={it.href} className="hover:text-brand-600 hover:underline">{it.label}</Link> : <span className="text-ink">{it.label}</span>}
        </span>
      ))}
    </nav>
  );
}
