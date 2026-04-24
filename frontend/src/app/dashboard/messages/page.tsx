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

const TYPING_INDICATOR_MS = 3000;
const TYPING_EMIT_MIN_MS = 1100;

// Shape of the structured error body returned by the backend when a send is
// rejected because of the off-platform-contact filter. ``code`` is stable —
// "email" / "phone" / "url" / "external_app" / "blocked" / "suspended".
interface ChatErrorBody {
  detail?: string;
  code?: string;
  violation_count?: number;
  suspended_until?: string | null;
}

interface AxiosLikeError {
  response?: { data?: ChatErrorBody };
}

function extractChatError(err: unknown): ChatErrorBody | null {
  const maybe = (err as AxiosLikeError | null)?.response?.data;
  return maybe && typeof maybe === "object" ? maybe : null;
}

function formatCountdown(msLeft: number, ar: boolean): string {
  if (msLeft <= 0) return ar ? "انتهى" : "ended";
  const totalSec = Math.floor(msLeft / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

function MessagesContent() {
  const { user } = useAuthStore();
  const { locale } = useLocale();
  const ar = locale === "ar";
  const searchParams = useSearchParams();
  const withUserId = searchParams.get("with");
  // Context passed through from job / proposal / order pages so the initiation
  // gate can verify the pair has a legit relationship. Without these, a
  // plain "?with=" cold-DM falls back to the prior-relationship check and is
  // rejected for strangers (Fiverr-hybrid rule).
  const composeJobId = searchParams.get("job");
  const composeOrderId = searchParams.get("order");

  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConvo, setActiveConvo] = useState<ConversationSummary | null>(null);
  const [messages, setMessages] = useState<MessageDetail[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [composeRecipient, setComposeRecipient] = useState<string | null>(null);
  const [supportModal, setSupportModal] = useState(false);
  const [supportMsg, setSupportMsg] = useState("");
  const [supportSending, setSupportSending] = useState(false);
  // Mobile: whether the chat panel is shown (vs the conversation list)
  const [mobileChatOpen, setMobileChatOpen] = useState(false);

  const [presence, setPresence] = useState<Record<string, PresenceInfo>>({});
  const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());

  // Chat policy state — suspension timestamp + violation counter. Seeded from
  // the authenticated user and updated in place when a send call returns a
  // structured error (so we don't need a round-trip to refresh /auth/me).
  const [suspendedUntil, setSuspendedUntil] = useState<string | null>(
    user?.chat_suspended_until ?? null
  );
  const [violationCount, setViolationCount] = useState<number>(
    user?.chat_violations ?? 0
  );
  // Ticks every second while suspended so the countdown re-renders.
  const [nowTick, setNowTick] = useState<number>(() => Date.now());

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeConvoRef = useRef<ConversationSummary | null>(null);
  activeConvoRef.current = activeConvo;
  const typingTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const lastTypingEmitRef = useRef<number>(0);
  // AbortController for in-flight message fetches — cancel stale ones on convo switch
  const fetchAbortRef = useRef<AbortController | null>(null);

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
    // Cancel any previous in-flight fetch
    fetchAbortRef.current?.abort();
    const controller = new AbortController();
    fetchAbortRef.current = controller;
    try {
      const res = await messagesApi.getMessages(convoId);
      // If this fetch was superseded, discard results
      if (controller.signal.aborted) return;
      setMessages(res.data.messages.reverse());
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "CanceledError") return;
      if (controller.signal.aborted) return;
      toast.error(ar ? "تعذّر تحميل الرسائل" : "Failed to load messages");
    }
  }, [ar]);

  const fetchPresence = useCallback(async (convos: ConversationSummary[]) => {
    const ids = convos.map((c) => c.other_user.id);
    if (ids.length === 0) return;
    try {
      const res = await messagesApi.getPresence(ids);
      const next: Record<string, PresenceInfo> = {};
      for (const p of res.data.users as PresenceInfo[]) next[p.user_id] = p;
      setPresence((prev) => ({ ...prev, ...next }));
    } catch {
      // Presence is non-critical
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

  useEffect(() => {
    return () => {
      fetchAbortRef.current?.abort();
      const timers = typingTimersRef.current;
      for (const t of timers.values()) clearTimeout(t);
      timers.clear();
    };
  }, []);

  // Re-seed suspension state when the authenticated user changes (e.g. after
  // an auth refresh that pulled fresh chat_* fields).
  useEffect(() => {
    setSuspendedUntil(user?.chat_suspended_until ?? null);
    setViolationCount(user?.chat_violations ?? 0);
  }, [user?.chat_suspended_until, user?.chat_violations]);

  // Tick the countdown once per second, but only while actually suspended —
  // no reason to re-render every second when the banner isn't visible.
  useEffect(() => {
    if (!suspendedUntil) return;
    const until = new Date(suspendedUntil).getTime();
    if (until <= Date.now()) {
      setSuspendedUntil(null);
      return;
    }
    const i = setInterval(() => {
      const now = Date.now();
      setNowTick(now);
      if (now >= until) {
        setSuspendedUntil(null);
        clearInterval(i);
      }
    }, 1000);
    return () => clearInterval(i);
  }, [suspendedUntil]);

  const suspendedMsLeft = suspendedUntil
    ? new Date(suspendedUntil).getTime() - nowTick
    : 0;
  const isSuspended = suspendedMsLeft > 0;

  // === WebSocket ===

  const handleWsMessage = useCallback((data: WsMessageData) => {
    const currentConvo = activeConvoRef.current;

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

  const handleContactSupport = async () => {
    if (!supportMsg.trim() || supportSending) return;
    setSupportSending(true);
    try {
      const res = await messagesApi.contactSupport(supportMsg.trim());
      const convo = res.data as ConversationSummary;
      setSupportModal(false);
      setSupportMsg("");
      setConversations((prev) => {
        const exists = prev.find((c) => c.id === convo.id);
        return exists ? prev : [convo, ...prev];
      });
      selectConversation(convo);
      toast.success(ar ? "تم إرسال رسالتك للدعم" : "Support message sent");
    } catch {
      toast.error(ar ? "تعذّر التواصل مع الدعم" : "Failed to contact support");
    } finally {
      setSupportSending(false);
    }
  };

  const { sendTyping } = useWebSocket({
    onMessage: handleWsMessage,
    onMessagesRead: handleMessagesRead,
    onTyping: handleTyping,
    enabled: !!user,
  });

  // === Send message ===

  const handleChatError = (err: unknown, fallbackMsg: string) => {
    const body = extractChatError(err);
    if (body?.code === "suspended" && body.suspended_until) {
      setSuspendedUntil(body.suspended_until);
      setViolationCount(body.violation_count ?? violationCount);
      toast.error(
        ar
          ? "تم تعليق محادثاتك بسبب انتهاك سياسة التواصل"
          : "Chat suspended for violating off-platform policy"
      );
      return;
    }
    if (body?.code) {
      // Non-suspended filter rejection (blocked — 2nd violation).
      setViolationCount(body.violation_count ?? violationCount);
      toast.error(
        ar
          ? "تم حجب رسالتك لاحتوائها على معلومات اتصال خارجية"
          : "Message blocked — contains off-platform contact info"
      );
      return;
    }
    toast.error(body?.detail || fallbackMsg);
  };

  const handleWarning = (msg: MessageDetail) => {
    if (!msg.chat_warning_code) return;
    const count = msg.chat_violation_count ?? null;
    setViolationCount(count ?? violationCount);
    toast.warning(
      ar
        ? `تم حذف معلومات الاتصال من رسالتك. التكرار القادم سيؤدي لحجب الرسالة${count ? ` (${count}/3)` : ""}.`
        : `Contact info was removed from your message. Next violation will block the message${count ? ` (${count}/3)` : ""}.`,
      { duration: 6000 }
    );
  };

  const handleSend = async () => {
    if (!newMessage.trim() || sending) return;
    if (isSuspended) {
      toast.error(
        ar
          ? "محادثاتك معلقة مؤقتاً — لا يمكن الإرسال الآن"
          : "Chat is temporarily suspended — cannot send"
      );
      return;
    }
    const content = newMessage.trim();

    if (!activeConvo && composeRecipient) {
      setSending(true);
      setNewMessage("");
      try {
        const res = await messagesApi.startConversation({
          recipient_id: composeRecipient,
          initial_message: content,
          ...(composeJobId ? { job_id: composeJobId } : {}),
          ...(composeOrderId ? { order_id: composeOrderId } : {}),
        });
        const newConvo = res.data as ConversationSummary;
        setComposeRecipient(null);
        setConversations((prev) => [newConvo, ...prev]);
        setActiveConvo(newConvo);
      } catch (err) {
        handleChatError(
          err,
          ar ? "تعذّر بدء المحادثة" : "Failed to start conversation"
        );
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
      setMessages((prev) => prev.map((m) => m.id === tmpId ? realMsg : m));
      handleWarning(realMsg);
      fetchConversations();
    } catch (err) {
      handleChatError(
        err,
        ar ? "تعذّر إرسال الرسالة" : "Failed to send message"
      );
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
    setMobileChatOpen(true);
    setConversations((prev) =>
      prev.map((conv) => (conv.id === c.id ? { ...conv, unread_count: 0 } : conv))
    );
  };

  const handleMobileBack = () => {
    setMobileChatOpen(false);
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
    // Label describes the CONVERSATION type, not the other user's role.
    // "Support" alone under an admin's name read as a role tag on that
    // admin; "Support ticket" makes the context clear.
    if (c.conversation_type === "support") return ar ? "تذكرة دعم" : "Support ticket";
    if (c.conversation_type === "order") return ar ? "محادثة طلب" : "Order chat";
    return null;
  };

  const activeOtherTyping =
    activeConvo && typingUsers.has(activeConvo.other_user.id);

  // Sidebar border: physical classes since flex order already handles RTL side
  const sidebarBorder = ar ? "border-l border-l-gray-200" : "border-r border-r-gray-200";

  return (
    <div className="flex h-[calc(100vh-160px)] bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Sidebar: Conversation List — hidden on mobile when chat is open */}
      <div
        className={`
          ${sidebarBorder} flex flex-col shrink-0
          w-full md:w-72
          ${mobileChatOpen ? "hidden md:flex" : "flex"}
        `}
      >
        <div className="p-4 border-b border-gray-100 flex items-center justify-between gap-2">
          <h2 className="font-bold text-gray-900 text-base">
            {ar ? "الرسائل" : "Messages"}
          </h2>
          <button
            onClick={() => setSupportModal(true)}
            className="shrink-0 flex items-center gap-1.5 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-2 rounded-lg transition-colors font-medium"
            title={ar ? "تواصل مع الدعم" : "Contact Support"}
          >
            <svg className="w-3.5 h-3.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
            <span>{ar ? "الدعم" : "Support"}</span>
          </button>
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
              const isActive = activeConvo?.id === c.id;
              return (
                <button
                  key={c.id}
                  onClick={() => selectConversation(c)}
                  className={`w-full p-3 text-start border-b border-gray-50 hover:bg-gray-50 transition-colors ${
                    isActive
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

      {/* Chat View — hidden on mobile when list is shown */}
      <div
        className={`
          flex-1 flex flex-col min-w-0
          ${mobileChatOpen ? "flex" : "hidden md:flex"}
        `}
      >
        {!activeConvo && composeRecipient ? (
          <>
            <div className="px-5 py-3.5 border-b border-gray-200 bg-white flex items-center gap-3">
              <button
                onClick={handleMobileBack}
                className="md:hidden p-1.5 rounded-lg hover:bg-gray-100 text-gray-600"
                aria-label={ar ? "رجوع" : "Back"}
              >
                <svg className={`w-5 h-5 ${ar ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div>
                <div className="font-semibold text-gray-900 text-sm">
                  {ar ? "محادثة جديدة" : "New conversation"}
                </div>
                <div className="text-xs text-gray-400">
                  {ar ? "اكتب رسالتك الأولى لبدء المحادثة" : "Type your first message to start chatting"}
                </div>
              </div>
            </div>
            <div className="flex-1 bg-gray-50" />
            {isSuspended && (
              <SuspensionBanner
                ar={ar}
                msLeft={suspendedMsLeft}
                violations={violationCount}
              />
            )}
            <MessageInput
              ar={ar}
              value={newMessage}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              onSend={handleSend}
              sending={sending}
              disabled={isSuspended}
            />
          </>
        ) : activeConvo ? (
          <>
            {/* Header */}
            <div className="px-4 py-3.5 border-b border-gray-200 bg-white flex items-center gap-3">
              {/* Back button — mobile only */}
              <button
                onClick={handleMobileBack}
                className="md:hidden shrink-0 p-1.5 rounded-lg hover:bg-gray-100 text-gray-600"
                aria-label={ar ? "رجوع" : "Back"}
              >
                <svg className={`w-5 h-5 ${ar ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
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
              <div className="min-w-0 flex-1">
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

            {/* Messages — always LTR for bubble positioning; text uses dir=auto */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2 bg-gray-50" dir="ltr">
              {messages.map((msg) => {
                const isSystem = msg.is_system || msg.sender_role === "system";
                if (isSystem) {
                  return (
                    <div key={msg.id} className="flex justify-center">
                      <div className="max-w-[80%] bg-gray-100 text-gray-600 text-xs px-3 py-1.5 rounded-full text-center whitespace-pre-wrap" dir="auto">
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
                      <p className="text-sm whitespace-pre-wrap leading-relaxed" dir="auto">{msg.content}</p>
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

            {isSuspended && (
              <SuspensionBanner
                ar={ar}
                msLeft={suspendedMsLeft}
                violations={violationCount}
              />
            )}
            <MessageInput
              ar={ar}
              value={newMessage}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              onSend={handleSend}
              sending={sending}
              disabled={isSuspended}
            />
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

      {/* Contact Support Modal — bottom sheet on mobile, centered dialog on desktop */}
      {supportModal && (
        <div
          className="fixed inset-0 z-50 bg-black/40 flex items-end sm:items-center justify-center sm:p-4"
          onClick={(e) => { if (e.target === e.currentTarget) { setSupportModal(false); setSupportMsg(""); } }}
        >
          <div className="bg-white w-full sm:max-w-md sm:rounded-2xl rounded-t-2xl shadow-xl flex flex-col max-h-[90vh]">
            {/* Drag handle — mobile only */}
            <div className="flex justify-center pt-3 pb-1 sm:hidden">
              <div className="w-10 h-1 bg-gray-300 rounded-full" />
            </div>

            <div className="px-5 pt-4 pb-2 sm:pt-6 sm:pb-2 flex items-start justify-between gap-3">
              <div>
                <h3 className="font-bold text-gray-900 text-base">
                  {ar ? "تواصل مع الدعم" : "Contact Support"}
                </h3>
                <p className="text-sm text-gray-500 mt-0.5">
                  {ar
                    ? "سيرد عليك فريق الدعم في أقرب وقت ممكن."
                    : "Our support team will reply as soon as possible."}
                </p>
              </div>
              <button
                onClick={() => { setSupportModal(false); setSupportMsg(""); }}
                className="shrink-0 p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                aria-label={ar ? "إغلاق" : "Close"}
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="px-5 pb-5 flex flex-col gap-3 overflow-y-auto">
              <textarea
                value={supportMsg}
                onChange={(e) => setSupportMsg(e.target.value)}
                placeholder={ar ? "اكتب رسالتك..." : "Describe your issue..."}
                rows={4}
                dir="auto"
                autoFocus
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
              />
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => { setSupportModal(false); setSupportMsg(""); }}
                  className="px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-xl transition-colors"
                >
                  {ar ? "إلغاء" : "Cancel"}
                </button>
                <button
                  onClick={handleContactSupport}
                  disabled={!supportMsg.trim() || supportSending}
                  className="flex-1 sm:flex-none px-5 py-2.5 text-sm bg-brand-500 text-white rounded-xl hover:bg-brand-600 disabled:opacity-40 transition-colors font-medium"
                >
                  {supportSending ? (ar ? "جارٍ الإرسال..." : "Sending...") : (ar ? "إرسال" : "Send Message")}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Extracted to avoid duplication between compose and active-convo modes
function MessageInput({
  ar,
  value,
  onChange,
  onKeyDown,
  onSend,
  sending,
  disabled = false,
}: {
  ar: boolean;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  onSend: () => void;
  sending: boolean;
  disabled?: boolean;
}) {
  return (
    <div className="px-4 py-3 border-t border-gray-200 bg-white">
      <div className="flex gap-2 items-end">
        <textarea
          value={value}
          onChange={onChange}
          onKeyDown={onKeyDown}
          placeholder={
            disabled
              ? (ar ? "لا يمكن الإرسال حالياً" : "Sending is disabled")
              : (ar ? "اكتب رسالتك..." : "Type a message...")
          }
          rows={1}
          dir="auto"
          disabled={disabled}
          className="flex-1 border border-gray-300 rounded-xl px-4 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed"
          style={{ minHeight: "42px", maxHeight: "120px" }}
          onInput={(e) => {
            const el = e.currentTarget;
            el.style.height = "auto";
            el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
          }}
        />
        <button
          onClick={onSend}
          disabled={!value.trim() || sending || disabled}
          className="shrink-0 w-10 h-10 flex items-center justify-center bg-brand-500 text-white rounded-xl hover:bg-brand-600 disabled:opacity-40 transition-colors"
          aria-label={ar ? "إرسال" : "Send"}
        >
          {/* Arrow flips in RTL via the parent dir attribute */}
          <svg
            className={`w-5 h-5 ${ar ? "rotate-180" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
      <p className="text-[10px] text-gray-400 mt-1.5 text-center">
        {ar ? "Enter للإرسال · Shift+Enter لسطر جديد" : "Enter to send · Shift+Enter for new line"}
      </p>
    </div>
  );
}

function SuspensionBanner({
  ar,
  msLeft,
  violations,
}: {
  ar: boolean;
  msLeft: number;
  violations: number;
}) {
  const countdown = formatCountdown(msLeft, ar);
  return (
    <div
      className="px-4 py-3 bg-red-50 border-t border-red-200 text-red-800 text-sm flex items-start gap-3"
      role="alert"
    >
      <svg className="w-5 h-5 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 9v2m0 4h.01M5.07 19h13.86c1.54 0 2.5-1.67 1.73-3L13.73 4a2 2 0 00-3.46 0L3.34 16c-.77 1.33.19 3 1.73 3z" />
      </svg>
      <div className="flex-1 min-w-0">
        <div className="font-semibold">
          {ar ? "تم تعليق محادثاتك مؤقتاً" : "Chat temporarily suspended"}
        </div>
        <div className="text-xs mt-0.5 text-red-700">
          {ar
            ? `بسبب ${violations} انتهاكات لسياسة التواصل. يمكنك الإرسال مرة أخرى بعد ${countdown}.`
            : `Due to ${violations} off-platform policy violations. You can send again in ${countdown}.`}
        </div>
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
