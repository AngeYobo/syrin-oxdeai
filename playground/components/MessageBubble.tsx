"use client";

import { useState } from "react";
import { MessageInfoButton } from "./MessageInfoButton";
import { ImageViewerModal } from "./ImageViewerModal";
import type { MessageAttachment } from "@/hooks/useStream";

export interface MessageData {
  role: "user" | "assistant";
  content: string;
  attachments?: MessageAttachment[];
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

function AttachmentPreview({ att }: { att: MessageAttachment }) {
  const [modalOpen, setModalOpen] = useState(false);
  const ext = att.type === "video" ? "mp4" : "png";
  const filename = `generated-${Date.now()}.${ext}`;

  if (att.type === "image") {
    return (
      <div className="message-attachment">
        <button
          type="button"
          className="message-attachment-link"
          onClick={() => setModalOpen(true)}
          title="View full size"
        >
          <img src={att.url} alt="" />
        </button>
        <a
          href={att.url}
          download={filename}
          className="message-attachment-download"
          title="Download"
        >
          ↓ Download
        </a>
        <ImageViewerModal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          src={att.url}
          downloadFilename={filename}
        />
      </div>
    );
  }

  if (att.type === "video") {
    return (
      <div className="message-attachment message-attachment-video">
        <video src={att.url} controls className="message-attachment-video-el" />
        <a
          href={att.url}
          download={filename}
          className="message-attachment-download"
          title="Download"
        >
          ↓ Download
        </a>
      </div>
    );
  }

  return null;
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
      {message.attachments && message.attachments.length > 0 && (
        <div className="message-attachments">
          {message.attachments.map((att, i) => (
            <AttachmentPreview key={i} att={att} />
          ))}
        </div>
      )}
      {message.meta && <div className="meta">{message.meta}</div>}
    </div>
  );
}
