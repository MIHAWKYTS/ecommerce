import { orderStatus } from "@/lib/format";

export default function StatusBadge({ status }: { status: string }) {
  const s = orderStatus(status);
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${s.tone}`}>{s.label}</span>;
}
