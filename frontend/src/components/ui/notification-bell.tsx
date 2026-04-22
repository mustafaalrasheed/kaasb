"use client";

import Link from "next/link";
import { useState, useEffect, useCallback } from "react";
import { notificationsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useWebSocket } from "@/lib/use-websocket";
import type { WsNotificationData, WsNotificationReadData } from "@/lib/use-websocket";

export function NotificationBell() {
  const { isAuthenticated, user } = useAuthStore();
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchCount = useCallback(async () => {
    try {
      const res = await notificationsApi.getUnreadCount();
      setUnreadCount(res.data.count ?? 0);
    } catch {
      // Silent — don't disrupt UI on refetch failure
    }
  }, []);

  // Initial + focus + online refetch — keeps the badge accurate without
  // the 30s polling interval. WebSocket push handles everything in between.
  useEffect(() => {
    if (!isAuthenticated) return;
    fetchCount();
    const onFocus = () => fetchCount();
    window.addEventListener("focus", onFocus);
    window.addEventListener("online", onFocus);
    return () => {
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("online", onFocus);
    };
  }, [isAuthenticated, fetchCount]);

  // Increment badge instantly on WebSocket push (no round-trip needed)
  const handleNotification = useCallback((_data: WsNotificationData) => {
    setUnreadCount((prev) => prev + 1);
  }, []);

  // Server-broadcast notification_read keeps every open tab and every
  // device in sync as soon as the user marks anything read anywhere.
  const handleNotificationRead = useCallback((data: WsNotificationReadData) => {
    if (data.all) {
      setUnreadCount(0);
    } else {
      setUnreadCount((prev) => Math.max(0, prev - Math.max(1, data.marked)));
    }
  }, []);

  useWebSocket({
    onNotification: handleNotification,
    onNotificationRead: handleNotificationRead,
    enabled: !!user,
  });

  // Same-tab optimistic decrement — the notifications page dispatches this
  // when the user interacts directly. WS keeps other tabs in sync; this
  // keeps the current tab instant even if the WS round-trip hasn't landed
  // yet. Clamped at 0 so a stale event can't push the badge negative.
  useEffect(() => {
    const onRead = (e: Event) => {
      const detail = (e as CustomEvent<{ count?: number }>).detail ?? {};
      const by = Math.max(1, detail.count ?? 1);
      setUnreadCount((prev) => Math.max(0, prev - by));
    };
    const onAllRead = () => setUnreadCount(0);
    window.addEventListener("kaasb:notifications:read", onRead);
    window.addEventListener("kaasb:notifications:all-read", onAllRead);
    return () => {
      window.removeEventListener("kaasb:notifications:read", onRead);
      window.removeEventListener("kaasb:notifications:all-read", onAllRead);
    };
  }, []);

  if (!isAuthenticated) return null;

  return (
    <Link
      href="/dashboard/notifications"
      className="relative inline-flex items-center text-gray-600 hover:text-gray-900"
      aria-label={`الإشعارات${unreadCount > 0 ? `، ${unreadCount} غير مقروء` : ""}`}
    >
      <svg
        className="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
        />
      </svg>
      {unreadCount > 0 && (
        <span className="absolute -top-1 -end-1 flex items-center justify-center h-4 min-w-4 px-1 text-[10px] font-bold bg-red-500 text-white rounded-full leading-none">
          {unreadCount > 99 ? "99+" : unreadCount}
        </span>
      )}
    </Link>
  );
}
