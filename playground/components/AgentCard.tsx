"use client";

import { DescribeData } from "@/lib/api";

interface AgentCardProps {
  describe: DescribeData | null;
  isOpen?: boolean;
  onToggle?: () => void;
}

export function AgentCard({ describe, isOpen = false, onToggle }: AgentCardProps) {
  if (!describe) return null;

  const tools = describe.tools;
  const toolList = Array.isArray(tools)
    ? tools.map((t) => (typeof t === "string" ? { name: t, description: "" } : t))
    : [];

  return (
    <details
      className="agent-card"
      open={isOpen}
      onToggle={onToggle ? () => onToggle() : undefined}
    >
      <summary>Agent details</summary>
      <div className="agent-card-content">
        <p className="agent-card-desc">{describe.description}</p>
        {toolList.length > 0 && (
          <div className="agent-card-section">
            <strong>Tools</strong>
            <ul>
              {toolList.map((t, i) => (
                <li key={i}>
                  <code>{t.name}</code>
                  {t.description && <span> — {t.description}</span>}
                </li>
              ))}
            </ul>
          </div>
        )}
        {describe.budget && (
          <div className="agent-card-section">
            <strong>Budget</strong>
            <p>
              ${Number(describe.budget.spent ?? 0).toFixed(4)} spent · $
              {Number(describe.budget.remaining ?? 0).toFixed(4)} remaining (
              {Number(describe.budget.percent_used ?? 0).toFixed(1)}% used)
            </p>
          </div>
        )}
      </div>
    </details>
  );
}
