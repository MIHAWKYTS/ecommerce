"use client";
import { useEffect, useState } from "react";

export default function QtyControl({ value, max = 999, onCommit, disabled, label = "Quantidade" }:
  { value: number; max?: number; onCommit: (n: number) => void; disabled?: boolean; label?: string }) {
  const [draft, setDraft] = useState(String(value));
  useEffect(() => setDraft(String(value)), [value]);
  const top = Math.max(1, Math.min(max, 999));

  function commit(n: number) {
    const v = Math.min(top, Math.max(1, Math.floor(n) || 1));
    setDraft(String(v));
    if (v !== value) onCommit(v);
  }

  const btn = "flex h-9 w-9 items-center justify-center text-lg text-ink transition hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-40";
  return (
    <div className="inline-flex items-center overflow-hidden rounded-lg border border-line bg-white">
      <button type="button" className={btn} aria-label="Diminuir" disabled={disabled || value <= 1} onClick={() => commit(value - 1)}>−</button>
      <input aria-label={label} inputMode="numeric" disabled={disabled}
        className="h-9 w-12 border-x border-line text-center text-sm outline-none disabled:bg-slate-50"
        value={draft}
        onChange={(e) => setDraft(e.target.value.replace(/\D/g, "").slice(0, 3))}
        onBlur={() => commit(Number(draft))}
        onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); (e.target as HTMLInputElement).blur(); } }} />
      <button type="button" className={btn} aria-label="Aumentar" disabled={disabled || value >= top} onClick={() => commit(value + 1)}>+</button>
    </div>
  );
}
