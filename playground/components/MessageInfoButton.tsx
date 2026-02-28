"use client";

interface MessageInfoButtonProps {
  onClick: () => void;
  title?: string;
}

export function MessageInfoButton({ onClick, title = "Info" }: MessageInfoButtonProps) {
  return (
    <button
      type="button"
      className="info-btn"
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      title={title}
      aria-label={title}
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M12 16v-4M12 8h.01" />
      </svg>
    </button>
  );
}
