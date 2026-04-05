"use client";

import { useState, useEffect, useCallback } from "react";
import { notificationsApi } from "@/lib/api";
import { toast } from "sonner";
import type { NotificationDetail } from "@/types/notification";
import { NOTIFICATION_ICONS } from "@/types/notification";

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationDetail[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "unread">("all");

  const fetchNotifications = useCallback(async () => {
    try {
      setLoading(true);
      const res = await notificationsApi.getNotifications({
        unread_only: filter === "unread",
        page,
        page_size: 20,
      });
      setNotifications(res.data.notifications);
      setUnreadCount(res.data.unread_count);
      setTotal(res.data.total);
    } catch {
      toast.error("تعذّر تحميل الإشعارات");
    } finally {
      setLoading(false);
    }
  }, [page, filter]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead();
      toast.success("تم تحديد جميع الإشعارات كمقروءة");
      fetchNotifications();
    } catch {
      toast.error("تعذّر تحديث الإشعارات");
    }
  };

  const handleMarkRead = async (id: string) => {
    try {
      await notificationsApi.markRead({ notification_ids: [id] });
      fetchNotifications();
    } catch {
      // Silent fail
    }
  };

  const getLink = (n: NotificationDetail): string | null => {
    if (!n.link_type || !n.link_id) return null;
    const links: Record<string, string> = {
      contract: `/dashboard/contracts/${n.link_id}`,
      job: `/jobs/${n.link_id}`,
      proposal: `/dashboard/my-proposals`,
      message: `/dashboard/messages`,
    };
    return links[n.link_type] || null;
  };

  const totalPages = Math.ceil(total / 20);

  return (
    <div className="p-6 max-w-3xl mx-auto space-y-4" dir="rtl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">الإشعارات</h1>
          {unreadCount > 0 && (
            <p className="text-sm text-gray-500 mt-1">
              {unreadCount} غير مقروء
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <select
            value={filter}
            onChange={(e) => {
              setFilter(e.target.value as "all" | "unread");
              setPage(1);
            }}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            <option value="all">الكل</option>
            <option value="unread">غير المقروءة</option>
          </select>
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="px-4 py-2 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              تحديد الكل كمقروء
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : notifications.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          {filter === "unread" ? "لا توجد إشعارات غير مقروءة" : "لا توجد إشعارات بعد"}
        </div>
      ) : (
        <div className="space-y-2">
          {notifications.map((n) => {
            const link = getLink(n);
            const Wrapper = link ? "a" : "div";
            return (
              <Wrapper
                key={n.id}
                {...(link ? { href: link } : {})}
                onClick={() => !n.is_read && handleMarkRead(n.id)}
                className={`block p-4 rounded-lg border transition cursor-pointer ${
                  n.is_read
                    ? "bg-white border-gray-100"
                    : "bg-blue-50 border-blue-200 hover:bg-blue-100"
                }`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-xl shrink-0">
                    {NOTIFICATION_ICONS[n.type] || "🔔"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className={`text-sm font-medium truncate ${
                          n.is_read ? "text-gray-700" : "text-gray-900"
                        }`}
                      >
                        {n.title}
                      </span>
                      <span className="text-xs text-gray-400 shrink-0">
                        {new Date(n.created_at).toLocaleDateString("ar-IQ", {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>
                    <p className="text-sm text-gray-500 mt-0.5">{n.message}</p>
                  </div>
                  {!n.is_read && (
                    <span className="w-2 h-2 bg-blue-500 rounded-full mt-2 shrink-0" />
                  )}
                </div>
              </Wrapper>
            );
          })}
        </div>
      )}

      {total > 20 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
          >
            السابق
          </button>
          <span className="text-sm text-gray-600">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= totalPages}
            className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
          >
            التالي
          </button>
        </div>
      )}
    </div>
  );
}
