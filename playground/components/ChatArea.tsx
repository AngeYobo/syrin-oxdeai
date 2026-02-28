"use client";

import { useRef, useEffect } from "react";
import { MessageBubble, MessageData } from "./MessageBubble";
import { PlaceholderBubble } from "./PlaceholderBubble";
import { ActivityItem } from "./ActivityItem";

export interface ActivityEntry {
  id: string;
  kind: "status" | "hook";
  label: string;
}

interface ChatAreaProps {
  messages: MessageData[];
  activities: ActivityEntry[];
  showPlaceholder: boolean;
  onShowTrace?: (
    events: Array<{ hook: string; ctx: Record<string, unknown> }>,
    message?: MessageData
  ) => void;
  debug?: boolean;
}

export function ChatArea({
  messages,
  activities,
  showPlaceholder,
  onShowTrace,
  debug,
}: ChatAreaProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, activities, showPlaceholder]);

  return (
    <div className="chat-messages" ref={scrollRef}>
      {messages.map((m, i) => (
        <MessageBubble
          key={i}
          message={m}
          onShowTrace={onShowTrace ? (evts) => onShowTrace(evts, m) : undefined}
          debug={debug}
        />
      ))}
      {activities.map((a) => (
        <ActivityItem key={a.id} label={a.label} kind={a.kind} />
      ))}
      {showPlaceholder && <PlaceholderBubble />}
    </div>
  );
}
