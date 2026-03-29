import { GigsCatalog } from "@/components/gigs/gigs-catalog";
import { gigsApi } from "@/lib/api";

export const metadata = { title: "الخدمات | كاسب" };

export default async function GigsPage() {
  let categories: unknown[] = [];
  try {
    const res = await gigsApi.getCategories();
    categories = res.data?.data || res.data || [];
  } catch {}

  return <GigsCatalog initialCategories={categories} />;
}
