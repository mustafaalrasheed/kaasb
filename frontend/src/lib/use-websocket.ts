"use client";

import { useEffect, useRef, useCallback } from "react";
import { authApi } from "@/lib/api";

const WS_BASE =
  (process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000")
    .replace(/^https/, "wss")
    .replace(/^http/, "ws");

export type WsMessage =
  | { type: "message"; data: WsMessageData }
  | { type: "notification"; data: WsNotificationData }
  | { type: "ping" };

export interface WsMessageData {
  conversation_id: string;
  id: string;
  content: string;
  sender_id: string;
  sender_name: string;
  sender_avatar?: string;
  created_at: string;
}

export interface WsNotificationData {
  id: string;
  title: string;
  message: string;
  type: string;
  link_type?: string;
  link_id?: string;
  created_at: string;
}

interface UseWebSocketOptions {
  onMessage?: (data: WsMessageData) => void;
  onNotification?: (data: WsNotificationData) => void;
  enabled?: boolean;
}

/**
 * Establishes a WebSocket connection using a short-lived ticket (POST /auth/ws-ticket).
 * Auto-reconnects on disconnect with exponential back-off (max 30s).
 * Responds to server ping events with pong to keep the connection alive.
 */
export function useWebSocket({
  onMessage,
  onNotification,
  enabled = true,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelay = useRef(1000);
  const mountedRef = useRef(true);

  const onMessageRef = useRef(onMessage);
  const onNotificationRef = useRef(onNotification);
  onMessageRef.current = onMessage;
  onNotificationRef.current = onNotification;

  const connect = useCallback(async () => {
    if (!mountedRef.current || !enabled) return;

    // Clean up any existing connection
    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    // Get a fresh ticket from the backend
    let ticket: string;
    try {
      const res = await authApi.getWsTicket();
      ticket = res.data.ticket;
    } catch {
      // Not authenticated or network error — retry after delay
      scheduleReconnect();
      return;
    }

    if (!mountedRef.current) return;

    const ws = new WebSocket(`${WS_BASE}/api/v1/ws?ticket=${ticket}`);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectDelay.current = 1000; // Reset back-off on successful connect
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
      } else if (parsed.type === "notification") {
        onNotificationRef.current?.(parsed.data);
      }
    };

    ws.onerror = () => {
      // onclose will fire after onerror — reconnect is handled there
    };

    ws.onclose = (event) => {
      wsRef.current = null;
      // 4001 = auth failure (invalid/expired ticket) — still retry after delay
      if (mountedRef.current) {
        scheduleReconnect();
      }
    };
  }, [enabled]);

  function scheduleReconnect() {
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    reconnectTimer.current = setTimeout(() => {
      // Exponential back-off: 1s → 2s → 4s → ... → 30s max
      reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000);
      connect();
    }, reconnectDelay.current);
  }

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
}
