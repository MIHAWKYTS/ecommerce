import type { Category } from "./api";

export type CatView = Category & { display: string; parentDisplay: string | null };
export type CatalogTree = { roots: (CatView & { children: CatView[] })[]; byId: Map<string, CatView>; leaves: CatView[] };

const collator = new Intl.Collator("pt-BR", { numeric: true, sensitivity: "base" });
const ROOT_NUM = /(\d+)\s*$/;
const SEED_CHILD = /^Subcategoria \d+\.\d+$/;
const SLUG_TAIL = /-(\d+)$/;

export function buildCatalog(cats: Category[]): CatalogTree {
  const byId = new Map<string, CatView>();
  const rootsRaw = cats.filter((c) => !c.parent_id);
  for (const r of rootsRaw) byId.set(r.id, { ...r, display: r.name, parentDisplay: null });

  for (const c of cats) {
    if (!c.parent_id) continue;
    const parent = byId.get(c.parent_id);
    let display = c.name;
    const rootNum = parent?.name.match(ROOT_NUM)?.[1];
    const tail = c.slug.match(SLUG_TAIL)?.[1];
    if (rootNum && tail && SEED_CHILD.test(c.name)) display = `Subcategoria ${rootNum}.${tail}`;
    byId.set(c.id, { ...c, display, parentDisplay: parent?.display ?? null });
  }

  const roots = rootsRaw
    .map((r) => ({
      ...byId.get(r.id)!,
      children: cats.filter((c) => c.parent_id === r.id).map((c) => byId.get(c.id)!)
        .sort((a, b) => collator.compare(a.display, b.display)),
    }))
    .sort((a, b) => collator.compare(a.display, b.display));
  const leaves = roots.flatMap((r) => r.children);
  return { roots, byId, leaves };
}

const norm = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

export function searchCategories(tree: CatalogTree, q: string, limit = 8): CatView[] {
  const t = norm(q.trim());
  if (!t) return [];
  return tree.leaves.filter((c) => norm(c.display).includes(t) || norm(c.parentDisplay ?? "").includes(t)).slice(0, limit);
}
