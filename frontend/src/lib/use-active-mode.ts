"use client";

import { useEffect, useState } from "react";

/**
 * User's active marketplace mode — "client" (buying services) or
 * "freelancer" (selling services). Stored in a client-side cookie so the
 * choice survives page reloads and tab restores.
 *
 * Defaults to the user's `primary_role` (set at signup), but the toggle
 * in the navbar lets dual-role users flip without changing their
 * profile. A CLIENT who wants to list a service can switch to freelancer
 * mode and see the Post Service / My Orders nav, without ever editing
 * their primary_role.
 *
 * Server-side the cookie is not read yet (the navbar is a client
 * component; SSR renders with the primary-role default and hydration
 * swaps to the cookie value). If that flash becomes noticeable we'll
 * move the read into a server component wrapper.
 */
export type ActiveMode = "client" | "freelancer";

const COOKIE_NAME = "kaasb_active_mode";
const COOKIE_MAX_AGE_DAYS = 365;

function readCookie(name: string): string | null {
    if (typeof document === "undefined") return null;
    const match = document.cookie
        .split(";")
        .map((s) => s.trim())
        .find((c) => c.startsWith(`${name}=`));
    return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

function writeCookie(name: string, value: string, maxAgeDays: number) {
    if (typeof document === "undefined") return;
    const maxAgeSec = maxAgeDays * 24 * 60 * 60;
    // SameSite=Lax + path=/ so the cookie is sent on all same-site
    // navigations including follow-up fetches. Not marked Secure because
    // the dev server at http://localhost:3000 needs to set it too; in
    // production Next.js serves over HTTPS so browsers promote it.
    document.cookie = `${name}=${encodeURIComponent(value)}; max-age=${maxAgeSec}; path=/; SameSite=Lax`;
}

export function useActiveMode(defaultMode: ActiveMode = "client"): {
    mode: ActiveMode;
    setMode: (mode: ActiveMode) => void;
} {
    const [mode, setModeState] = useState<ActiveMode>(defaultMode);

    // Hydrate from cookie after first client-side render.
    useEffect(() => {
        const stored = readCookie(COOKIE_NAME);
        if (stored === "client" || stored === "freelancer") {
            setModeState(stored);
        } else {
            // First visit — persist the default so subsequent reads have
            // a stable value even without user interaction.
            writeCookie(COOKIE_NAME, defaultMode, COOKIE_MAX_AGE_DAYS);
        }
    }, [defaultMode]);

    const setMode = (next: ActiveMode) => {
        writeCookie(COOKIE_NAME, next, COOKIE_MAX_AGE_DAYS);
        setModeState(next);
    };

    return { mode, setMode };
}
