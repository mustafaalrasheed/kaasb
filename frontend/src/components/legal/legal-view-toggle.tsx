"use client";

import { useEffect, useState } from "react";

type View = "both" | "ar" | "en";
const STORAGE_KEY = "kaasb_legal_view";

function applyClass(view: View) {
  const el = document.documentElement;
  el.classList.remove("legal-lang-ar", "legal-lang-en");
  if (view === "ar") el.classList.add("legal-lang-ar");
  if (view === "en") el.classList.add("legal-lang-en");
}

export function LegalViewToggle() {
  const [view, setView] = useState<View>("both");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    try {
      const stored = localStorage.getItem(STORAGE_KEY) as View | null;
      if (stored === "ar" || stored === "en" || stored === "both") {
        setView(stored);
        applyClass(stored);
      }
    } catch {
      /* ignore */
    }
    return () => applyClass("both");
  }, []);

  const choose = (next: View) => {
    setView(next);
    applyClass(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  };

  if (!mounted) {
    return <div className="h-10" aria-hidden="true" />;
  }

  const base =
    "px-3 py-1.5 text-xs sm:text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500";
  const active = "bg-brand-500 text-white";
  const inactive = "bg-white text-gray-700 hover:bg-gray-50";

  return (
    <div
      role="radiogroup"
      aria-label="Legal document language view"
      className="inline-flex rounded-lg border border-gray-200 overflow-hidden shadow-sm"
    >
      <button
        type="button"
        role="radio"
        aria-checked={view === "both"}
        onClick={() => choose("both")}
        className={`${base} ${view === "both" ? active : inactive} border-e border-gray-200`}
      >
        Both · كلاهما
      </button>
      <button
        type="button"
        role="radio"
        aria-checked={view === "ar"}
        onClick={() => choose("ar")}
        className={`${base} ${view === "ar" ? active : inactive} border-e border-gray-200`}
      >
        العربية فقط
      </button>
      <button
        type="button"
        role="radio"
        aria-checked={view === "en"}
        onClick={() => choose("en")}
        className={`${base} ${view === "en" ? active : inactive}`}
      >
        English only
      </button>
    </div>
  );
}
