import { cookies } from "next/headers";

export default async function Loading() {
  const cookieStore = await cookies();
  const ar = cookieStore.get("locale")?.value !== "en";

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="text-center">
        <div className="inline-block w-8 h-8 border-4 border-brand-200 border-t-brand-500 rounded-full animate-spin" />
        <p className="mt-4 text-sm text-gray-500">
          {ar ? "جاري التحميل..." : "Loading..."}
        </p>
      </div>
    </div>
  );
}
