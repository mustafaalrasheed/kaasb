"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { messagesApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useWebSocket } from "@/lib/use-websocket";
import type { WsMessageData } from "@/lib/use-websocket";
import { toast } from "sonner";
import type { ConversationSummary, MessageDetail } from "@/types/message";
import { useLocale } from "@/providers/locale-provider";

export default function MessagesPage() {
  const { user } = useAuthStore();
  const { locale } = useLocale();
  const ar = locale === "ar";

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConvo, setActiveConvo] = useState<ConversationSummary | null>(null);
  const [messages, setMessages] = useState<MessageDetail[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeConvoRef = useRef<ConversationSummary | null>(null);
  activeConvoRef.current = activeConvo;

  // === Data fetching ===

  const fetchConversations = useCallback(async () => {
    try {
      const res = await messagesApi.getConversations();
      setConversations(res.data.conversations);
    } catch {
      toast.error(ar ? "تعذّر تحميل المحادثات" : "Failed to load conversations");
    } finally {
      setLoading(false);
    }
  }, [ar]);

  const fetchMessages = useCallback(async (convoId: string) => {
    try {
      const res = await messagesApi.getMessages(convoId);
      setMessages(res.data.messages.reverse()); // Show oldest first
    } catch {
      toast.error(ar ? "تعذّر تحميل الرسائل" : "Failed to load messages");
    }
  }, [ar]);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  useEffect(() => {
    if (!activeConvo) return;
    fetchMessages(activeConvo.id);
    const interval = setInterval(() => {
      if (!document.hidden && activeConvoRef.current) {
        fetchMessages(activeConvoRef.current.id);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [activeConvo?.id, fetchMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // === WebSocket (real-time push) ===

  const handleWsMessage = useCallback((data: WsMessageData) => {
    const currentConvo = activeConvoRef.current;

    if (currentConvo && data.conversation_id === currentConvo.id) {
      const newMsg: MessageDetail = {
        id: data.id,
        content: data.content,
        is_read: false,
        sender: {
          id: data.sender_id,
          username: "",
          first_name: data.sender_name,
          last_name: "",
          avatar_url: data.sender_avatar,
        },
        created_at: data.created_at,
      };
      setMessages((prev) => [...prev, newMsg]);
    }

    fetchConversations();
  }, [fetchConversations]);

  useWebSocket({ onMessage: handleWsMessage, enabled: !!user });

  // === Send message ===

  const handleSend = async () => {
    if (!newMessage.trim() || !activeConvo || sending) return;
    const content = newMessage.trim();
    setNewMessage("");

    if (user) {
      const optimistic: MessageDetail = {
        id: `tmp-${Date.now()}`,
        content,
        is_read: true,
        sender: {
          id: user.id,
          username: user.username,
          first_name: user.first_name,
          last_name: user.last_name,
          avatar_url: user.avatar_url ?? undefined,
        },
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, optimistic]);
    }

    try {
      setSending(true);
      await messagesApi.sendMessage(activeConvo.id, { content });
      fetchConversations();
    } catch {
      toast.error(ar ? "تعذّر إرسال الرسالة" : "Failed to send message");
      setMessages((prev) => prev.filter((m) => !m.id.startsWith("tmp-")));
      setNewMessage(content);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const selectConversation = (c: ConversationSummary) => {
    setActiveConvo(c);
    setConversations((prev) =>
      prev.map((conv) => (conv.id === c.id ? { ...conv, unread_count: 0 } : conv))
    );
  };

  const timeAgo = (date: string) => {
    const diff = Date.now() - new Date(date).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return ar ? "الآن" : "now";
    if (mins < 60) return ar ? `${mins}د` : `${mins}m`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return ar ? `${hrs}س` : `${hrs}h`;
    return ar ? `${Math.floor(hrs / 24)}ي` : `${Math.floor(hrs / 24)}d`;
  };

  const avatarLetters = (first: string, last: string) =>
    `${first?.[0] ?? ""}${last?.[0] ?? ""}`.toUpperCase();

  return (
    <div className="flex h-[calc(100vh-80px)] bg-white">
      {/* Sidebar: Conversation List */}
      <div className={`w-72 ${ar ? "border-l" : "border-r"} border-gray-200 flex flex-col shrink-0`}>
        <div className="p-4 border-b border-gray-100">
          <h2 className="font-bold text-gray-900 text-base">
            {ar ? "الرسائل" : "Messages"}
          </h2>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex gap-3 animate-pulse">
                  <div className="w-10 h-10 rounded-full bg-gray-200 shrink-0" />
                  <div className="flex-1 space-y-1.5 pt-1">
                    <div className="h-3 bg-gray-200 rounded w-3/4" />
                    <div className="h-2.5 bg-gray-100 rounded w-full" />
                  </div>
                </div>
              ))}
            </div>
          ) : conversations.length === 0 ? (
            <div className="p-8 text-center text-gray-400 text-sm">
              {ar ? "لا توجد محادثات بعد" : "No conversations yet"}
            </div>
          ) : (
            conversations.map((c) => (
              <button
                key={c.id}
                onClick={() => selectConversation(c)}
                className={`w-full p-3 text-start border-b border-gray-50 hover:bg-gray-50 transition-colors ${
                  activeConvo?.id === c.id
                    ? `bg-brand-50 ${ar ? "border-r-2 border-r-brand-500" : "border-l-2 border-l-brand-500"}`
                    : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="relative shrink-0">
                    {c.other_user.avatar_url ? (
                      <img
                        src={c.other_user.avatar_url}
                        alt=""
                        className="w-10 h-10 rounded-full object-cover"
                      />
                    ) : (
                      <div className="w-10 h-10 bg-brand-100 rounded-full flex items-center justify-center text-sm font-semibold text-brand-700">
                        {avatarLetters(c.other_user.first_name, c.other_user.last_name)}
                      </div>
                    )}
                    {c.unread_count > 0 && (
                      <span className="absolute -top-0.5 -start-0.5 w-4 h-4 bg-brand-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                        {c.unread_count > 9 ? "9+" : c.unread_count}
                      </span>
                    )}
                  </div>

                  <div className="flex-1 min-w-0 text-start">
                    <div className="flex items-center justify-between gap-1">
                      <span className={`text-sm truncate ${c.unread_count > 0 ? "font-semibold text-gray-900" : "font-medium text-gray-700"}`}>
                        {c.other_user.first_name} {c.other_user.last_name}
                      </span>
                      {c.last_message_at && (
                        <span className="text-[11px] text-gray-400 shrink-0">
                          {timeAgo(c.last_message_at)}
                        </span>
                      )}
                    </div>
                    <p className={`text-xs truncate mt-0.5 ${c.unread_count > 0 ? "text-gray-700" : "text-gray-400"}`}>
                      {c.last_message_text || (ar ? "لا توجد رسائل" : "No messages")}
                    </p>
                    {c.job && (
                      <p className="text-[10px] text-brand-400 truncate mt-0.5">
                        {c.job.title}
                      </p>
                    )}
                  </div>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Chat View */}
      <div className="flex-1 flex flex-col min-w-0">
        {activeConvo ? (
          <>
            {/* Header */}
            <div className="px-5 py-3.5 border-b border-gray-200 bg-white flex items-center gap-3">
              {activeConvo.other_user.avatar_url ? (
                <img
                  src={activeConvo.other_user.avatar_url}
                  alt=""
                  className="w-9 h-9 rounded-full object-cover"
                />
              ) : (
                <div className="w-9 h-9 bg-brand-100 rounded-full flex items-center justify-center text-sm font-semibold text-brand-700">
                  {avatarLetters(activeConvo.other_user.first_name, activeConvo.other_user.last_name)}
                </div>
              )}
              <div>
                <div className="font-semibold text-gray-900 text-sm">
                  {activeConvo.other_user.first_name} {activeConvo.other_user.last_name}
                </div>
                {activeConvo.job && (
                  <div className="text-xs text-gray-400">
                    {ar ? "بشأن:" : "Re:"} {activeConvo.job.title}
                  </div>
                )}
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2 bg-gray-50">
              {messages.map((msg) => {
                const isMe = msg.sender.id === user?.id;
                const isOptimistic = msg.id.startsWith("tmp-");
                return (
                  <div key={msg.id} className={`flex ${isMe ? "justify-end" : "justify-start"}`}>
                    <div
                      className={`max-w-[72%] rounded-2xl px-4 py-2.5 ${
                        isMe
                          ? "bg-brand-500 text-white rounded-br-sm"
                          : "bg-white text-gray-900 border border-gray-200 rounded-bl-sm"
                      } ${isOptimistic ? "opacity-70" : ""}`}
                    >
                      <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                      <p className={`text-[11px] mt-1 ${isMe ? "text-brand-200" : "text-gray-400"}`}>
                        {new Date(msg.created_at).toLocaleTimeString(ar ? "ar-IQ" : "en-US", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="px-4 py-3 border-t border-gray-200 bg-white">
              <div className="flex gap-2 items-end">
                <textarea
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={ar ? "اكتب رسالتك..." : "Type a message..."}
                  rows={1}
                  className="flex-1 border border-gray-300 rounded-xl px-4 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                  style={{ minHeight: "42px", maxHeight: "120px" }}
                  onInput={(e) => {
                    const el = e.currentTarget;
                    el.style.height = "auto";
                    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
                  }}
                />
                <button
                  onClick={handleSend}
                  disabled={!newMessage.trim() || sending}
                  className="shrink-0 w-10 h-10 flex items-center justify-center bg-brand-500 text-white rounded-xl hover:bg-brand-600 disabled:opacity-40 transition-colors"
                  aria-label={ar ? "إرسال" : "Send"}
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </button>
              </div>
              <p className="text-[10px] text-gray-400 mt-1.5 text-center">
                {ar ? "Enter للإرسال · Shift+Enter لسطر جديد" : "Enter to send · Shift+Enter for new line"}
              </p>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400 gap-3">
            <svg className="w-14 h-14 text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p className="text-sm">{ar ? "اختر محادثة للبدء" : "Select a conversation to start"}</p>
          </div>
        )}
      </div>
    </div>
  );
}
