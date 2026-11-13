"use client";
import { useState } from "react";
import { hashHue } from "@/lib/format";

export default function CategoryThumb({ id, slug, label }: { id: string; slug: string; label: string }) {
  const [failed, setFailed] = useState(false);
  if (!failed) {
    return <img src={`/produtos/${slug}/1.jpg`} alt="" loading="lazy" onError={() => setFailed(true)}
      className="h-12 w-12 shrink-0 rounded-lg object-cover" />;
  }
  const hue = hashHue(id);
  return (
    <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg text-sm font-bold"
      style={{ background: `hsl(${hue} 70% 92%)`, color: `hsl(${hue} 45% 30%)` }}>
      {label.match(/[\d.]+$/)?.[0] ?? label.slice(0, 2)}
    </span>
  );
}
