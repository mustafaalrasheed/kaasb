"use client";

import { useEffect, useRef, useCallback } from "react";
import { authApi } from "@/lib/api";
import type { MessageAttachment, SenderRole } from "@/types/message";

const WS_BASE =
  (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000")
    .replace(/^https/, "wss")
    .replace(/^http/, "ws");

export type WsMessage =
  | { type: "message"; data: WsMessageData }
  | { type: "messages_read"; data: WsMessagesReadData }
  | { type: "typing"; data: WsTypingData }
  | { type: "notification"; data: WsNotificationData }
  | { type: "notification_read"; data: WsNotificationReadData }
  | { type: "ping" };

export interface WsNotificationReadData {
  /** Number of notifications flipped to read. */
  marked: number;
  /** True when the server ran mark_all_read; false for a specific id list. */
  all: boolean;
}

export interface WsMessageData {
  conversation_id: string;
  id: string;
  content: string;
  sender_id: string;
  sender_name: string;
  sender_avatar?: string;
  sender_role?: SenderRole;
  is_system?: boolean;
  attachments?: MessageAttachment[];
  created_at: string;
}

export interface WsMessagesReadData {
  conversation_id: string;
  reader_id: string;
  message_ids: string[];
  read_at: string;
}

export interface WsTypingData {
  conversation_id: string;
  user_id: string;
}

import type { NotificationType } from "@/types/notification";

export interface WsNotificationData {
  id: string;
  title: string;
  message: string;
  type: NotificationType;
  link_type?: string;
  link_id?: string;
  created_at: string;
}

interface UseWebSocketOptions {
  onMessage?: (data: WsMessageData) => void;
  onMessagesRead?: (data: WsMessagesReadData) => void;
  onTyping?: (data: WsTypingData) => void;
  onNotification?: (data: WsNotificationData) => void;
  onNotificationRead?: (data: WsNotificationReadData) => void;
  enabled?: boolean;
}

export interface UseWebSocketApi {
  /**
   * Send an outbound typing heartbeat. Backend rate-limits to 1/sec per
   * conversation, so callers don't need to throttle tightly; once-per-keystroke
   * is fine. No-ops if the socket is not open.
   */
  sendTyping: (conversationId: string) => void;
}

/**
 * Establishes a WebSocket connection using a short-lived ticket (POST /auth/ws-ticket).
 * Auto-reconnects on disconnect with exponential back-off (max 30s).
 * Responds to server ping events with pong to keep the connection alive.
 */
export function useWebSocket({
  onMessage,
  onMessagesRead,
  onTyping,
  onNotification,
  onNotificationRead,
  enabled = true,
}: UseWebSocketOptions): UseWebSocketApi {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelay = useRef(1000);
  const mountedRef = useRef(true);

  const onMessageRef = useRef(onMessage);
  const onMessagesReadRef = useRef(onMessagesRead);
  const onTypingRef = useRef(onTyping);
  const onNotificationRef = useRef(onNotification);
  const onNotificationReadRef = useRef(onNotificationRead);
  onMessageRef.current = onMessage;
  onMessagesReadRef.current = onMessagesRead;
  onTypingRef.current = onTyping;
  onNotificationRef.current = onNotification;
  onNotificationReadRef.current = onNotificationRead;

  const connect = useCallback(async () => {
    if (!mountedRef.current || !enabled) return;

    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    let ticket: string;
    try {
      const res = await authApi.getWsTicket();
      ticket = res.data.ticket;
    } catch {
      scheduleReconnect();
      return;
    }

    if (!mountedRef.current) return;

    const ws = new WebSocket(`${WS_BASE}/api/v1/ws?ticket=${ticket}`);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectDelay.current = 1000;
    };

    ws.onmessage = (event) => {
      let parsed: WsMessage;
      try {
        parsed = JSON.parse(event.data) as WsMessage;
      } catch {
        return;
      }

      if (parsed.type === "ping") {
        ws.send(JSON.stringify({ type: "pong" }));
      } else if (parsed.type === "message") {
        onMessageRef.current?.(parsed.data);
      } else if (parsed.type === "messages_read") {
        onMessagesReadRef.current?.(parsed.data);
      } else if (parsed.type === "typing") {
        onTypingRef.current?.(parsed.data);
      } else if (parsed.type === "notification") {
        onNotificationRef.current?.(parsed.data);
      } else if (parsed.type === "notification_read") {
        onNotificationReadRef.current?.(parsed.data);
      }
    };

    ws.onerror = () => {
      // onclose fires after onerror — reconnect is handled there
    };

    ws.onclose = () => {
      wsRef.current = null;
      if (mountedRef.current) {
        scheduleReconnect();
      }
    };
  }, [enabled]); // eslint-disable-line react-hooks/exhaustive-deps

  function scheduleReconnect() {
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    reconnectTimer.current = setTimeout(() => {
      reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000);
      connect();
    }, reconnectDelay.current);
  }

  const sendTyping = useCallback((conversationId: string) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: "typing", conversation_id: conversationId }));
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    if (enabled) {
      connect();
    }
    return () => {
      mountedRef.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect, enabled]);

  return { sendTyping };
}
