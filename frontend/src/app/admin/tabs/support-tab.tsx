"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { adminApi, messagesApi } from "@/lib/api";
import type {
  ConversationSummary,
  MessageDetail,
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
  const [onlyUnread, setOnlyUnread] = useState(true);
  const [loading, setLoading] = useState(true);

  const [active, setActive] = useState<ConversationSummary | null>(null);
  const [messages, setMessages] = useState<MessageDetail[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [reply, setReply] = useState("");
  const [sending, setSending] = useState(false);

  const scrollEndRef = useRef<HTMLDivElement>(null);

  const fetchThreads = useCallback(async () => {
    try {
      setLoading(true);
      const res = await adminApi.getSupportConversations({ only_unread: onlyUnread });
      setThreads(res.data.conversations);
      setTotal(res.data.total);
    } catch (err) {
      toast.error(getApiError(err, ar ? "تعذّر تحميل تذاكر الدعم" : "Failed to load support tickets"));
    } finally {
      setLoading(false);
    }
  }, [onlyUnread, ar]);

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
        <label className="ms-auto flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            checked={onlyUnread}
            onChange={(e) => setOnlyUnread(e.target.checked)}
            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          {ar ? "إظهار غير المقروءة فقط" : "Unread only"}
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
              <div className="px-5 py-3 border-b border-gray-200 bg-white">
                <div className="font-semibold text-sm text-gray-900">
                  {active.other_user.first_name} {active.other_user.last_name}
                  <span className="text-gray-400 font-normal ms-2">@{active.other_user.username}</span>
                </div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {ar ? "تذكرة دعم" : "Support ticket"}
                  {" · "}
                  {active.message_count}
                  {" "}
                  {ar ? "رسالة" : "messages"}
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
