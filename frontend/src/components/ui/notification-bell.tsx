"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { notificationsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";

export function NotificationBell() {
  const { isAuthenticated } = useAuthStore();
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    if (!isAuthenticated) return;

    const fetch = async () => {
      try {
        const res = await notificationsApi.getUnreadCount();
        setUnreadCount(res.data.count ?? 0);
      } catch {
        // Silent — don't disrupt UI on polling failure
      }
    };

    fetch();
    const interval = setInterval(fetch, 30_000);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  if (!isAuthenticated) return null;

  return (
    <Link
      href="/dashboard/notifications"
      className="relative inline-flex items-center text-gray-600 hover:text-gray-900"
      aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ""}`}
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
