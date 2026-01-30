import { useCallback, useEffect, useRef, useState } from "react";
import type { WSMessage, QueryRequest } from "../types";

interface UseWebSocketOptions {
  onMessage?: (message: WSMessage) => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  sendMessage: (request: QueryRequest) => void;
  lastMessage: WSMessage | null;
}

export function useWebSocket(
  options: UseWebSocketOptions = {},
): UseWebSocketReturn {
  const {
    onMessage,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  const onMessageRef = useRef(onMessage);
  
  // Update ref when onMessage changes, but don't recreate connection
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("[WebSocket] Connected");
      setIsConnected(true);
      reconnectCountRef.current = 0;
    };

    ws.onclose = (event) => {
      console.log("[WebSocket] Disconnected", {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean,
      });
      setIsConnected(false);
      wsRef.current = null;

      // Attempt to reconnect
      if (reconnectCountRef.current < reconnectAttempts) {
        reconnectCountRef.current += 1;
        console.log(
          `[WebSocket] Reconnecting... (attempt ${reconnectCountRef.current}/${reconnectAttempts})`,
        );

        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, reconnectInterval);
      }
    };

    ws.onerror = (error) => {
      console.error("[WebSocket] Error:", error);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WSMessage;
        console.log("[WebSocket] Received message:", message.type);
        setLastMessage(message);
        // Use ref to call latest onMessage without recreating connection
        onMessageRef.current?.(message);
      } catch (error) {
        console.error("[WebSocket] Failed to parse message:", error, event.data);
      }
    };
  }, [reconnectAttempts, reconnectInterval]);

  const sendMessage = useCallback((request: QueryRequest) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(request));
    } else {
      console.error("[WebSocket] Not connected");
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    isConnected,
    sendMessage,
    lastMessage,
  };
}
