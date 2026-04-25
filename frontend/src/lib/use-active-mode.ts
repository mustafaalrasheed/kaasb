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

// Module-level pub/sub so multiple useActiveMode subscribers (navbar +
// dashboard layout + dashboard pages) update synchronously when ANY
// instance calls setMode. Without this, clicking "Switch to Selling" in
// the navbar updated the navbar but the dashboard sidebar stayed stale
// until the next route change.
const _modeSubscribers = new Set<(mode: ActiveMode) => void>();
function _broadcastMode(next: ActiveMode) {
    for (const cb of _modeSubscribers) cb(next);
}

export function useActiveMode(defaultMode: ActiveMode = "client"): {
    mode: ActiveMode;
    setMode: (mode: ActiveMode) => void;
} {
    const [mode, setModeState] = useState<ActiveMode>(defaultMode);

    // Hydrate from cookie + subscribe to cross-component updates so
    // setMode() in any other component (the navbar) propagates here too.
    useEffect(() => {
        const stored = readCookie(COOKIE_NAME);
        if (stored === "client" || stored === "freelancer") {
            setModeState(stored);
        } else {
            // First visit — persist the default so subsequent reads have
            // a stable value even without user interaction.
            writeCookie(COOKIE_NAME, defaultMode, COOKIE_MAX_AGE_DAYS);
        }
        const onChange = (next: ActiveMode) => setModeState(next);
        _modeSubscribers.add(onChange);
        return () => {
            _modeSubscribers.delete(onChange);
        };
    }, [defaultMode]);

    const setMode = (next: ActiveMode) => {
        writeCookie(COOKIE_NAME, next, COOKIE_MAX_AGE_DAYS);
        setModeState(next);
        _broadcastMode(next);
    };

    return { mode, setMode };
}

/**
 * UI-effective role: "admin" for superusers, the active marketplace mode
 * for authenticated non-admins (so dashboard pages, sidebar links, and
 * action gates flip together with the navbar toggle), and the user's
 * primary_role for guests / unauthenticated states.
 *
 * Use this — NOT raw \`user.primary_role\` — for any UI that should
 * follow the navbar's "Switch to Selling" / "Switch to Buying" toggle.
 * Server-side authorization still keys off primary_role + is_superuser
 * because the cookie can be tampered with client-side.
 */
export function useEffectiveRole(
    user: { primary_role?: string; is_superuser?: boolean } | null | undefined,
    isAuthenticated: boolean,
): "client" | "freelancer" | "admin" | undefined {
    const primary = user?.primary_role;
    const defaultMode: ActiveMode = primary === "freelancer" ? "freelancer" : "client";
    const { mode } = useActiveMode(defaultMode);
    if (user?.is_superuser) return "admin";
    if (!isAuthenticated || !primary) return primary as "client" | "freelancer" | undefined;
    if (primary === "admin") return "admin";
    return mode;
}
