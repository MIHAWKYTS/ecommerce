"use client";
import { useState } from "react";
import { hashHue } from "@/lib/format";

const FICTICIO = /^https?:\/\/[^/]*exemplo\.com\//i;

export default function ProductImage({ id, name, src, className = "" }: { id: string; name: string; src?: string; className?: string }) {
  const [failed, setFailed] = useState(false);
  const usable = src && !FICTICIO.test(src) && !failed;
  if (usable) {
    return <img src={src} alt={name} loading="lazy" onError={() => setFailed(true)} className={`aspect-square w-full object-cover ${className}`} />;
  }
  const hue = hashHue(id);
  const label = name.match(/\d+$/)?.[0] ?? name.slice(0, 2).toUpperCase();
  return (
    <div role="img" aria-label={name}
      className={`relative flex aspect-square w-full items-center justify-center overflow-hidden ${className}`}
      style={{ background: `linear-gradient(135deg, hsl(${hue} 70% 92%), hsl(${(hue + 40) % 360} 65% 82%))` }}>
      <svg viewBox="0 0 24 24" className="h-1/3 w-1/3 opacity-60" fill="none" stroke={`hsl(${hue} 45% 35%)`} strokeWidth="1.5" aria-hidden>
        <path d="M6 7h12l-1 13H7L6 7Z" strokeLinejoin="round" />
        <path d="M9 7a3 3 0 0 1 6 0" strokeLinecap="round" />
      </svg>
      <span className="absolute bottom-2 right-3 text-xs font-semibold" style={{ color: `hsl(${hue} 40% 30%)` }}>#{label}</span>
    </div>
  );
}
