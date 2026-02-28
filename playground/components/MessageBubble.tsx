"use client";

import { MessageInfoButton } from "./MessageInfoButton";

export interface MessageData {
  role: "user" | "assistant";
  content: string;
  meta?: string;
  isError?: boolean;
  events?: Array<{ hook: string; ctx: Record<string, unknown> }>;
  cost?: number;
  tokens?: Record<string, number>;
}

interface MessageBubbleProps {
  message: MessageData;
  onShowTrace?: (events: Array<{ hook: string; ctx: Record<string, unknown> }>) => void;
  debug?: boolean;
}

export function MessageBubble({ message, onShowTrace, debug }: MessageBubbleProps) {
  const hasTrace = debug && message.events && message.events.length > 0;

  return (
    <div className={`message ${message.role} ${message.isError ? "error" : ""}`}>
      <div className="message-header">
        <span className="content">{message.content}</span>
        {hasTrace && onShowTrace && (
          <MessageInfoButton onClick={() => onShowTrace(message.events!)} title="View trace" />
        )}
      </div>
      {message.meta && <div className="meta">{message.meta}</div>}
    </div>
  );
}
