"use client";

import { Suspense, useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { messagesApi } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useWebSocket } from "@/lib/use-websocket";
import type {
  WsMessageData,
  WsMessagesReadData,
  WsTypingData,
} from "@/lib/use-websocket";
import { toast } from "sonner";
import type {
  ConversationSummary,
  MessageDetail,
  PresenceInfo,
} from "@/types/message";
import { useLocale } from "@/providers/locale-provider";
import { backendUrl } from "@/lib/utils";

// How long a single inbound "typing" event keeps the indicator visible
// before we consider the user to have stopped typing.
const TYPING_INDICATOR_MS = 3000;

// Throttle outbound typing heartbeats. Backend hard-caps at 1/sec per
// conversation anyway, so we match that locally to avoid wasted socket frames.
const TYPING_EMIT_MIN_MS = 1100;

function MessagesContent() {
  const { user } = useAuthStore();
  const { locale } = useLocale();
  const ar = locale === "ar";
  const searchParams = useSearchParams();
  const withUserId = searchParams.get("with");

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConvo, setActiveConvo] = useState<ConversationSummary | null>(null);
  const [messages, setMessages] = useState<MessageDetail[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [composeRecipient, setComposeRecipient] = useState<string | null>(null);

  // Map of other_user.id → presence. Null last_seen_at means "never seen".
  const [presence, setPresence] = useState<Record<string, PresenceInfo>>({});
  // Set of user IDs we've seen a typing event from in the last TYPING_INDICATOR_MS.
  const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeConvoRef = useRef<ConversationSummary | null>(null);
  activeConvoRef.current = activeConvo;
  const typingTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const lastTypingEmitRef = useRef<number>(0);

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
      setMessages(res.data.messages.reverse()); // oldest first
    } catch {
      toast.error(ar ? "تعذّر تحميل الرسائل" : "Failed to load messages");
    }
  }, [ar]);

  // Batch presence fetch — runs after the conversation list loads and when it
  // changes (new conversations appear). Listed users' green dots come from
  // this call; WS events then keep the state fresh without re-polling.
  const fetchPresence = useCallback(async (convos: ConversationSummary[]) => {
    const ids = convos.map((c) => c.other_user.id);
    if (ids.length === 0) return;
    try {
      const res = await messagesApi.getPresence(ids);
      const next: Record<string, PresenceInfo> = {};
      for (const p of res.data.users as PresenceInfo[]) next[p.user_id] = p;
      setPresence((prev) => ({ ...prev, ...next }));
    } catch {
      // Presence is non-critical — silently skip on failure
    }
  }, []);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  useEffect(() => {
    if (!loading && conversations.length > 0) {
      fetchPresence(conversations);
    }
  }, [loading, conversations, fetchPresence]);

  // Auto-open conversation when ?with=<userId> is in the URL
  useEffect(() => {
    if (!withUserId || loading) return;
    const existing = conversations.find((c) => c.other_user.id === withUserId);
    if (existing) {
      selectConversation(existing);
      setComposeRecipient(null);
    } else {
      setComposeRecipient(withUserId);
    }
  }, [withUserId, conversations, loading]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!activeConvo) return;
    fetchMessages(activeConvo.id);
    // 30s fallback poll — catches messages sent while WS was reconnecting.
    // WebSocket push handles real-time delivery; this is just a safety net.
    const interval = setInterval(() => {
      if (!document.hidden && activeConvoRef.current) {
        fetchMessages(activeConvoRef.current.id);
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [activeConvo?.id, fetchMessages]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Cleanup pending typing timers on unmount
  useEffect(() => {
    return () => {
      const timers = typingTimersRef.current;
      for (const t of timers.values()) clearTimeout(t);
      timers.clear();
    };
  }, []);

  // === WebSocket (real-time push) ===

  const handleWsMessage = useCallback((data: WsMessageData) => {
    const currentConvo = activeConvoRef.current;

    // Seeing a message from a user implies they're online — flip their dot on.
    if (data.sender_id) {
      setPresence((prev) => ({
        ...prev,
        [data.sender_id]: {
          user_id: data.sender_id,
          is_online: true,
          last_seen_at: prev[data.sender_id]?.last_seen_at ?? null,
        },
      }));
    }

    if (currentConvo && data.conversation_id === currentConvo.id) {
      const newMsg: MessageDetail = {
        id: data.id,
        content: data.content,
        is_read: false,
        read_at: null,
        is_system: data.is_system ?? false,
        sender_role: data.sender_role,
        attachments: data.attachments ?? [],
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

  const handleMessagesRead = useCallback((data: WsMessagesReadData) => {
    // The other participant just opened the convo — flip our own ticks to ✓✓.
    setMessages((prev) =>
      prev.map((m) =>
        data.message_ids.includes(m.id)
          ? { ...m, is_read: true, read_at: data.read_at }
          : m
      )
    );
  }, []);

  const handleTyping = useCallback((data: WsTypingData) => {
    const currentConvo = activeConvoRef.current;
    if (!currentConvo || currentConvo.id !== data.conversation_id) return;
    if (data.user_id === user?.id) return;

    setTypingUsers((prev) => {
      if (prev.has(data.user_id)) return prev;
      const next = new Set(prev);
      next.add(data.user_id);
      return next;
    });

    const existing = typingTimersRef.current.get(data.user_id);
    if (existing) clearTimeout(existing);
    const t = setTimeout(() => {
      setTypingUsers((prev) => {
        if (!prev.has(data.user_id)) return prev;
        const next = new Set(prev);
        next.delete(data.user_id);
        return next;
      });
      typingTimersRef.current.delete(data.user_id);
    }, TYPING_INDICATOR_MS);
    typingTimersRef.current.set(data.user_id, t);
  }, [user?.id]);

  const { sendTyping } = useWebSocket({
    onMessage: handleWsMessage,
    onMessagesRead: handleMessagesRead,
    onTyping: handleTyping,
    enabled: !!user,
  });

  // === Send message ===

  const handleSend = async () => {
    if (!newMessage.trim() || sending) return;
    const content = newMessage.trim();

    // Compose mode: no existing conversation with this user — start one
    if (!activeConvo && composeRecipient) {
      setSending(true);
      setNewMessage("");
      try {
        const res = await messagesApi.startConversation({
          recipient_id: composeRecipient,
          initial_message: content,
        });
        const newConvo = res.data as ConversationSummary;
        setComposeRecipient(null);
        setConversations((prev) => [newConvo, ...prev]);
        setActiveConvo(newConvo);
      } catch {
        toast.error(ar ? "تعذّر بدء المحادثة" : "Failed to start conversation");
        setNewMessage(content);
      } finally {
        setSending(false);
      }
      return;
    }

    if (!activeConvo) return;
    setNewMessage("");

    const tmpId = `tmp-${Date.now()}`;
    if (user) {
      const optimistic: MessageDetail = {
        id: tmpId,
        content,
        is_read: true,
        read_at: null,
        is_system: false,
        sender_role: undefined,
        attachments: [],
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
      const res = await messagesApi.sendMessage(activeConvo.id, { content });
      const realMsg = res.data as MessageDetail;
      // Swap the optimistic placeholder for the confirmed server message.
      setMessages((prev) => prev.map((m) => m.id === tmpId ? realMsg : m));
      fetchConversations();
    } catch {
      toast.error(ar ? "تعذّر إرسال الرسالة" : "Failed to send message");
      setMessages((prev) => prev.filter((m) => m.id !== tmpId));
      setNewMessage(content);
    } finally {
      setSending(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setNewMessage(e.target.value);
    if (!activeConvo) return;
    const now = Date.now();
    if (now - lastTypingEmitRef.current < TYPING_EMIT_MIN_MS) return;
    lastTypingEmitRef.current = now;
    sendTyping(activeConvo.id);
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

  const otherPresenceText = (userId: string): string | null => {
    const p = presence[userId];
    if (!p) return null;
    if (p.is_online) return ar ? "متصل الآن" : "Online";
    if (!p.last_seen_at) return null;
    return ar
      ? `آخر ظهور ${timeAgo(p.last_seen_at)}`
      : `Last seen ${timeAgo(p.last_seen_at)}`;
  };

  const conversationTypeBadge = (c: ConversationSummary): string | null => {
    if (c.conversation_type === "support") return ar ? "الدعم" : "Support";
    if (c.conversation_type === "order") return ar ? "طلب" : "Order";
    return null;
  };

  const activeOtherTyping =
    activeConvo && typingUsers.has(activeConvo.other_user.id);

  return (
    <div className="flex h-[calc(100vh-160px)] bg-white rounded-lg border border-gray-200 overflow-hidden">
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
            conversations.map((c) => {
              const online = presence[c.other_user.id]?.is_online ?? false;
              const badge = conversationTypeBadge(c);
              return (
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
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={backendUrl(c.other_user.avatar_url)}
                          alt=""
                          className="w-10 h-10 rounded-full object-cover"
                        />
                      ) : (
                        <div className="w-10 h-10 bg-brand-100 rounded-full flex items-center justify-center text-sm font-semibold text-brand-700">
                          {avatarLetters(c.other_user.first_name, c.other_user.last_name)}
                        </div>
                      )}
                      {online && (
                        <span
                          className="absolute bottom-0 end-0 w-3 h-3 bg-green-500 border-2 border-white rounded-full"
                          aria-label={ar ? "متصل الآن" : "Online"}
                        />
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
                      <div className="flex items-center gap-1.5 mt-0.5">
                        {badge && (
                          <span className="text-[9px] uppercase tracking-wide bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                            {badge}
                          </span>
                        )}
                        {c.job && (
                          <p className="text-[10px] text-brand-400 truncate">
                            {c.job.title}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Chat View */}
      <div className="flex-1 flex flex-col min-w-0">
        {!activeConvo && composeRecipient ? (
          <>
            <div className="px-5 py-3.5 border-b border-gray-200 bg-white">
              <div className="font-semibold text-gray-900 text-sm">
                {ar ? "محادثة جديدة" : "New conversation"}
              </div>
              <div className="text-xs text-gray-400">
                {ar ? "اكتب رسالتك الأولى لبدء المحادثة" : "Type your first message to start chatting"}
              </div>
            </div>
            <div className="flex-1 bg-gray-50" />
            <div className="px-4 py-3 border-t border-gray-200 bg-white">
              <div className="flex gap-2 items-end">
                <textarea
                  value={newMessage}
                  onChange={handleInputChange}
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
            </div>
          </>
        ) : activeConvo ? (
          <>
            {/* Header */}
            <div className="px-5 py-3.5 border-b border-gray-200 bg-white flex items-center gap-3">
              <div className="relative shrink-0">
                {activeConvo.other_user.avatar_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={backendUrl(activeConvo.other_user.avatar_url)}
                    alt=""
                    className="w-9 h-9 rounded-full object-cover"
                  />
                ) : (
                  <div className="w-9 h-9 bg-brand-100 rounded-full flex items-center justify-center text-sm font-semibold text-brand-700">
                    {avatarLetters(activeConvo.other_user.first_name, activeConvo.other_user.last_name)}
                  </div>
                )}
                {presence[activeConvo.other_user.id]?.is_online && (
                  <span className="absolute bottom-0 end-0 w-2.5 h-2.5 bg-green-500 border-2 border-white rounded-full" />
                )}
              </div>
              <div className="min-w-0">
                <div className="font-semibold text-gray-900 text-sm truncate">
                  {activeConvo.other_user.first_name} {activeConvo.other_user.last_name}
                </div>
                <div className="text-xs text-gray-400 truncate">
                  {activeOtherTyping
                    ? (ar ? "يكتب..." : "typing...")
                    : otherPresenceText(activeConvo.other_user.id) ?? (
                        activeConvo.job
                          ? `${ar ? "بشأن:" : "Re:"} ${activeConvo.job.title}`
                          : ""
                      )}
                </div>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2 bg-gray-50">
              {messages.map((msg) => {
                const isSystem = msg.is_system || msg.sender_role === "system";
                if (isSystem) {
                  return (
                    <div key={msg.id} className="flex justify-center">
                      <div className="max-w-[80%] bg-gray-100 text-gray-600 text-xs px-3 py-1.5 rounded-full text-center whitespace-pre-wrap">
                        {msg.content}
                      </div>
                    </div>
                  );
                }

                const isMe = msg.sender.id === user?.id;
                const isOptimistic = msg.id.startsWith("tmp-");
                const readByOther = isMe && (msg.is_read || !!msg.read_at);
                const attachments = msg.attachments ?? [];
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
                      {attachments.length > 0 && (
                        <ul className="mt-2 space-y-1">
                          {attachments.map((a, i) => (
                            <li key={i}>
                              <a
                                href={backendUrl(a.url)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className={`text-xs underline ${isMe ? "text-brand-100" : "text-brand-600"} break-all`}
                              >
                                {a.filename || a.url}
                              </a>
                            </li>
                          ))}
                        </ul>
                      )}
                      <div className={`flex items-center gap-1 mt-1 ${isMe ? "justify-end" : "justify-start"}`}>
                        <span className={`text-[11px] ${isMe ? "text-brand-200" : "text-gray-400"}`}>
                          {new Date(msg.created_at).toLocaleTimeString(ar ? "ar-IQ" : "en-US", {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                        {isMe && !isOptimistic && (
                          <span
                            className={`text-[11px] ${readByOther ? "text-sky-200" : "text-brand-200/70"}`}
                            aria-label={readByOther ? (ar ? "مقروءة" : "Read") : (ar ? "تم الإرسال" : "Sent")}
                            title={readByOther ? (ar ? "مقروءة" : "Read") : (ar ? "تم الإرسال" : "Sent")}
                          >
                            {readByOther ? "✓✓" : "✓"}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
              {activeOtherTyping && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-2 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="px-4 py-3 border-t border-gray-200 bg-white">
              <div className="flex gap-2 items-end">
                <textarea
                  value={newMessage}
                  onChange={handleInputChange}
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

export default function MessagesPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <MessagesContent />
    </Suspense>
  );
}
