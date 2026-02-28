"use client";

import { AgentOption } from "@/lib/api";

interface AgentSelectorProps {
  agents: AgentOption[];
  value: string;
  onChange: (name: string) => void;
}

export function AgentSelector({ agents, value, onChange }: AgentSelectorProps) {
  if (!agents || agents.length <= 1) return null;

  return (
    <div className="agent-selector">
      <label htmlFor="agent-select">Agent</label>
      <select id="agent-select" value={value} onChange={(e) => onChange(e.target.value)}>
        {agents.map((a) => (
          <option key={a.name} value={a.name}>
            {a.name} — {a.description ?? ""}
          </option>
        ))}
      </select>
    </div>
  );
}
