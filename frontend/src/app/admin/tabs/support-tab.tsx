"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { adminApi, messagesApi } from "@/lib/api";
import type {
  ConversationSummary,
  MessageDetail,
  SupportTicketStatus,
} from "@/types/message";
import { toast } from "sonner";
import { backendUrl, getApiError } from "@/lib/utils";

interface SupportTabProps {
  ar: boolean;
  dateLocale: string;
}

export function SupportTab({ ar, dateLocale }: SupportTabProps) {
  const [threads, setThreads] = useState<ConversationSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [onlyUnread, setOnlyUnread] = useState(false);
  const [statusFilter, setStatusFilter] = useState<SupportTicketStatus | "">("open");
  const [mineOnly, setMineOnly] = useState(false);
  const [loading, setLoading] = useState(true);

  const [active, setActive] = useState<ConversationSummary | null>(null);
  const [messages, setMessages] = useState<MessageDetail[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);
  const [ticketActionLoading, setTicketActionLoading] = useState(false);

  const scrollEndRef = useRef<HTMLDivElement>(null);

  const fetchThreads = useCallback(async () => {
    try {
      setLoading(true);
      const res = await adminApi.getSupportConversations({
        only_unread: onlyUnread,
        status: statusFilter || undefined,
        mine: mineOnly || undefined,
      });
      setThreads(res.data.conversations);
      setTotal(res.data.total);
    } catch (err) {
      toast.error(getApiError(err, ar ? "تعذّر تحميل تذاكر الدعم" : "Failed to load support tickets"));
    } finally {
      setLoading(false);
    }
  }, [onlyUnread, statusFilter, mineOnly, ar]);

  const fetchMessages = useCallback(async (convoId: string) => {
    try {
      setMessagesLoading(true);
      const res = await messagesApi.getMessages(convoId);
      setMessages(res.data.messages.slice().reverse());
    } catch (err) {
      toast.error(getApiError(err, ar ? "تعذّر تحميل الرسائل" : "Failed to load messages"));
    } finally {
      setMessagesLoading(false);
    }
  }, [ar]);

  useEffect(() => {
    fetchThreads();
  }, [fetchThreads]);

  useEffect(() => {
    if (!active) return;
    fetchMessages(active.id);
  }, [active?.id, fetchMessages]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    scrollEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!active || !reply.trim() || sending) return;
    const content = reply.trim();
    setReply("");
    setSending(true);
    try {
      await messagesApi.sendMessage(active.id, { content });
      await fetchMessages(active.id);
      fetchThreads();
    } catch (err) {
      toast.error(getApiError(err, ar ? "تعذّر الإرسال" : "Failed to send"));
      setReply(content);
    } finally {
      setSending(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const runTicketAction = async (
    action: "claim" | "resolve" | "reopen",
    successMsg: string,
    errorMsg: string,
  ) => {
    if (!active || ticketActionLoading) return;
    setTicketActionLoading(true);
    try {
      const fn =
        action === "claim" ? adminApi.claimSupportTicket
        : action === "resolve" ? adminApi.resolveSupportTicket
        : adminApi.reopenSupportTicket;
      const res = await fn(active.id);
      setActive(res.data);
      toast.success(successMsg);
      fetchThreads();
    } catch (err) {
      toast.error(getApiError(err, errorMsg));
    } finally {
      setTicketActionLoading(false);
    }
  };

  const handleClaim = () =>
    runTicketAction(
      "claim",
      ar ? "تم استلام التذكرة" : "Ticket claimed",
      ar ? "تعذّر استلام التذكرة" : "Failed to claim ticket",
    );

  const handleResolve = () =>
    runTicketAction(
      "resolve",
      ar ? "تم إغلاق التذكرة" : "Ticket resolved",
      ar ? "تعذّر الإغلاق" : "Failed to resolve",
    );

  const handleReopen = () =>
    runTicketAction(
      "reopen",
      ar ? "تم إعادة فتح التذكرة" : "Ticket reopened",
      ar ? "تعذّر إعادة الفتح" : "Failed to reopen",
    );

  const statusLabel = (s: SupportTicketStatus | null | undefined) => {
    if (!s) return "";
    if (ar) return s === "open" ? "مفتوحة" : s === "in_progress" ? "قيد المعالجة" : "مغلقة";
    return s === "open" ? "Open" : s === "in_progress" ? "In Progress" : "Resolved";
  };

  const statusPillClass = (s: SupportTicketStatus | null | undefined) => {
    if (s === "in_progress") return "bg-blue-100 text-blue-700";
    if (s === "resolved") return "bg-gray-100 text-gray-600";
    return "bg-amber-100 text-amber-800";
  };

  const avatarLetters = (f: string, l: string) =>
    `${f?.[0] ?? ""}${l?.[0] ?? ""}`.toUpperCase();

  const formatTime = (iso: string) =>
    new Date(iso).toLocaleString(dateLocale, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex items-center gap-4 flex-wrap">
        <div>
          <h2 className="font-semibold text-gray-900">
            {ar ? "صندوق الدعم" : "Support Inbox"}
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {ar
              ? `${total} تذكرة${onlyUnread ? " بانتظار الرد" : ""}`
              : `${total} ticket${total !== 1 ? "s" : ""}${onlyUnread ? " awaiting reply" : ""}`}
          </p>
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as SupportTicketStatus | "")}
          className="ms-auto border border-gray-300 rounded-lg px-3 py-1.5 text-sm"
        >
          <option value="">{ar ? "كل الحالات" : "All statuses"}</option>
          <option value="open">{ar ? "مفتوحة" : "Open"}</option>
          <option value="in_progress">{ar ? "قيد المعالجة" : "In Progress"}</option>
          <option value="resolved">{ar ? "مغلقة" : "Resolved"}</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            checked={mineOnly}
            onChange={(e) => setMineOnly(e.target.checked)}
            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          {ar ? "المُسندة لي" : "Assigned to me"}
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            checked={onlyUnread}
            onChange={(e) => setOnlyUnread(e.target.checked)}
            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          {ar ? "غير المقروءة فقط" : "Unread only"}
        </label>
        <button
          onClick={fetchThreads}
          className="text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          {ar ? "تحديث" : "Refresh"}
        </button>
      </div>

      <div className="flex h-[70vh]">
        {/* Thread list */}
        <div className={`w-80 shrink-0 ${ar ? "border-l" : "border-r"} border-gray-200 overflow-y-auto`}>
          {loading ? (
            <div className="p-4 space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex gap-3 animate-pulse">
                  <div className="w-10 h-10 rounded-full bg-gray-200 shrink-0" />
                  <div className="flex-1 space-y-1.5 pt-1">
                    <div className="h-3 bg-gray-200 rounded w-2/3" />
                    <div className="h-2.5 bg-gray-100 rounded w-full" />
                  </div>
                </div>
              ))}
            </div>
          ) : threads.length === 0 ? (
            <div className="p-8 text-center text-gray-400 text-sm">
              {ar
                ? (onlyUnread ? "لا توجد تذاكر بانتظار الرد" : "لا توجد تذاكر دعم")
                : (onlyUnread ? "No tickets awaiting reply" : "No support tickets")}
            </div>
          ) : (
            threads.map((t) => (
              <button
                key={t.id}
                onClick={() => setActive(t)}
                className={`w-full p-3 text-start border-b border-gray-50 hover:bg-gray-50 transition-colors ${
                  active?.id === t.id ? "bg-blue-50" : ""
                }`}
              >
                <div className="flex items-start gap-3">
                  {t.other_user.avatar_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={backendUrl(t.other_user.avatar_url)}
                      alt=""
                      className="w-10 h-10 rounded-full object-cover shrink-0"
                    />
                  ) : (
                    <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-sm font-semibold text-blue-700 shrink-0">
                      {avatarLetters(t.other_user.first_name, t.other_user.last_name)}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <span className={`text-sm truncate ${t.unread_count > 0 ? "font-semibold text-gray-900" : "font-medium text-gray-700"}`}>
                        {t.other_user.first_name} {t.other_user.last_name}
                      </span>
                      {t.unread_count > 0 && (
                        <span className="shrink-0 bg-red-500 text-white text-[10px] font-bold rounded-full px-1.5 py-0.5">
                          {t.unread_count > 9 ? "9+" : t.unread_count}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 truncate mt-0.5">
                      @{t.other_user.username}
                    </p>
                    <div className="flex items-center gap-1 mt-1 flex-wrap">
                      {t.support_status && (
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${statusPillClass(t.support_status)}`}>
                          {statusLabel(t.support_status)}
                        </span>
                      )}
                      {t.support_assignee && (
                        <span className="text-[10px] text-gray-500 truncate">
                          {ar ? "لـ" : "by"} @{t.support_assignee.username}
                        </span>
                      )}
                    </div>
                    <p className={`text-xs truncate mt-1 ${t.unread_count > 0 ? "text-gray-800" : "text-gray-400"}`}>
                      {t.last_message_text || (ar ? "لا رسائل" : "No messages")}
                    </p>
                    {t.last_message_at && (
                      <p className="text-[10px] text-gray-400 mt-0.5">
                        {formatTime(t.last_message_at)}
                      </p>
                    )}
                  </div>
                </div>
              </button>
            ))
          )}
        </div>

        {/* Thread view */}
        <div className="flex-1 flex flex-col min-w-0 bg-gray-50">
          {!active ? (
            <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
              {ar ? "اختر تذكرة للرد" : "Select a ticket to reply"}
            </div>
          ) : (
            <>
              <div className="px-5 py-3 border-b border-gray-200 bg-white flex items-start gap-3 flex-wrap">
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-sm text-gray-900 flex items-center gap-2 flex-wrap">
                    <span>
                      {active.other_user.first_name} {active.other_user.last_name}
                    </span>
                    <span className="text-gray-400 font-normal">@{active.other_user.username}</span>
                    {active.support_status && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${statusPillClass(active.support_status)}`}>
                        {statusLabel(active.support_status)}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    {ar ? "تذكرة دعم" : "Support ticket"}
                    {" · "}
                    {active.message_count} {ar ? "رسالة" : "messages"}
                    {active.support_assignee && (
                      <>
                        {" · "}
                        {ar ? "المسؤول" : "Handled by"} @{active.support_assignee.username}
                      </>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {active.support_status !== "in_progress" && active.support_status !== "resolved" && (
                    <button
                      onClick={handleClaim}
                      disabled={ticketActionLoading}
                      className="px-3 py-1.5 text-xs font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40"
                    >
                      {ar ? "استلام" : "Claim"}
                    </button>
                  )}
                  {active.support_status === "in_progress" && (
                    <button
                      onClick={handleResolve}
                      disabled={ticketActionLoading}
                      className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-40"
                    >
                      {ar ? "إغلاق" : "Resolve"}
                    </button>
                  )}
                  {active.support_status === "resolved" && (
                    <button
                      onClick={handleReopen}
                      disabled={ticketActionLoading}
                      className="px-3 py-1.5 text-xs font-medium bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-40"
                    >
                      {ar ? "إعادة فتح" : "Reopen"}
                    </button>
                  )}
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-2">
                {messagesLoading ? (
                  <div className="text-center text-gray-400 text-sm py-8">
                    {ar ? "جاري التحميل..." : "Loading..."}
                  </div>
                ) : messages.length === 0 ? (
                  <div className="text-center text-gray-400 text-sm py-8">
                    {ar ? "لا رسائل" : "No messages"}
                  </div>
                ) : (
                  messages.map((m) => {
                    const isSystem = m.is_system || m.sender_role === "system";
                    if (isSystem) {
                      return (
                        <div key={m.id} className="flex justify-center">
                          <div className="max-w-[80%] bg-gray-100 text-gray-600 text-xs px-3 py-1.5 rounded-full text-center whitespace-pre-wrap">
                            {m.content}
                          </div>
                        </div>
                      );
                    }
                    const isAdmin = m.sender_role === "admin";
                    return (
                      <div key={m.id} className={`flex ${isAdmin ? "justify-end" : "justify-start"}`}>
                        <div
                          className={`max-w-[75%] rounded-2xl px-4 py-2.5 ${
                            isAdmin
                              ? "bg-blue-500 text-white rounded-br-sm"
                              : "bg-white text-gray-900 border border-gray-200 rounded-bl-sm"
                          }`}
                        >
                          <p className={`text-[11px] mb-0.5 ${isAdmin ? "text-blue-100" : "text-gray-500"}`}>
                            {isAdmin
                              ? `${ar ? "الدعم" : "Support"}${m.sender.username ? ` · @${m.sender.username}` : ""}`
                              : `${m.sender.first_name} ${m.sender.last_name}`}
                          </p>
                          <p className="text-sm whitespace-pre-wrap leading-relaxed">{m.content}</p>
                          <p className={`text-[10px] mt-1 ${isAdmin ? "text-blue-100" : "text-gray-400"}`}>
                            {formatTime(m.created_at)}
                          </p>
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={scrollEndRef} />
              </div>

              <div className="px-4 py-3 border-t border-gray-200 bg-white">
                <div className="flex gap-2 items-end">
                  <textarea
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    onKeyDown={handleKey}
                    placeholder={ar ? "اكتب ردّك..." : "Type your reply..."}
                    rows={1}
                    className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    style={{ minHeight: "40px", maxHeight: "120px" }}
                    onInput={(e) => {
                      const el = e.currentTarget;
                      el.style.height = "auto";
                      el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
                    }}
                  />
                  <button
                    onClick={handleSend}
                    disabled={!reply.trim() || sending}
                    className="shrink-0 px-4 h-10 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-40 transition-colors"
                  >
                    {sending
                      ? (ar ? "..." : "...")
                      : (ar ? "إرسال" : "Send")}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
