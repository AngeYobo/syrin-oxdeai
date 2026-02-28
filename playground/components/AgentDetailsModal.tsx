"use client";

import { AgentIcon } from "./AgentIcon";
import { AgentOption, DescribeData } from "@/lib/api";

// Inline SVG icons — minimal, no deps
const IconInfo = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden
  >
    <circle cx="12" cy="12" r="10" />
    <path d="M12 16v-4M12 8h.01" />
  </svg>
);
const IconTools = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden
  >
    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
  </svg>
);
const IconBudget = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden
  >
    <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
    <path d="M1 10h22" />
  </svg>
);
const IconAgents = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden
  >
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
  </svg>
);
const IconWorkflow = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden
  >
    <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 17h6M17 14v6M14 14h.01" />
  </svg>
);

interface AgentDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  agents: AgentOption[];
  selectedAgent: string;
  onSelectAgent: (name: string) => void;
  describe: DescribeData | null;
  setupType?: "single" | "multi" | "dynamic_pipeline" | "pipeline";
}

export function AgentDetailsModal({
  isOpen,
  onClose,
  agents,
  selectedAgent,
  onSelectAgent,
  describe,
  setupType,
}: AgentDetailsModalProps) {
  if (!isOpen) return null;

  const tools = describe?.tools;
  const toolList = Array.isArray(tools)
    ? tools.map((t) => (typeof t === "string" ? { name: t, description: "" } : t))
    : [];
  const multiAgent = agents && agents.length > 1;
  const internalAgents = describe?.internal_agents ?? [];
  const isDynamicPipeline = setupType === "dynamic_pipeline" || internalAgents.length > 0;

  const currentAgent = agents.find((a) => a.name === selectedAgent);
  const displayName = describe?.name ?? currentAgent?.name ?? selectedAgent ?? "Agent";

  return (
    <>
      <div className="modal-overlay" onClick={onClose} aria-hidden="true" />
      <aside className="agent-details-modal" role="dialog" aria-label="Agent details">
        <div className="modal-header">
          <div className="modal-title-row">
            <AgentIcon size={22} />
            <div className="modal-title-wrap">
              <h2 className="modal-agent-name">{displayName}</h2>
              <span className="modal-subtitle">Agent details</span>
            </div>
          </div>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className="modal-body">
          {multiAgent && (
            <div className="modal-section modal-section-icon">
              <label>
                <IconAgents />
                <span>Select agent</span>
              </label>
              <p className="modal-hint">
                You can switch between agents and talk to each one directly.
              </p>
              <select
                value={selectedAgent}
                onChange={(e) => onSelectAgent(e.target.value)}
                className="agent-select-in-modal"
              >
                {agents.map((a) => (
                  <option key={a.name} value={a.name}>
                    {a.name} — {a.description ?? ""}
                  </option>
                ))}
              </select>
            </div>
          )}

          {isDynamicPipeline && internalAgents.length > 0 && (
            <div className="modal-section modal-section-icon">
              <label>
                <IconWorkflow />
                <span>Internal agents (used automatically)</span>
              </label>
              <p className="modal-hint">
                These {internalAgents.length} agents are invoked internally by the orchestrator
                based on your request. You chat with the orchestrator; it decides which agents to
                use.
              </p>
              <ul className="internal-agents-list">
                {internalAgents.map((name) => (
                  <li key={name}>
                    <AgentIcon size={14} />
                    <span>{name}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {describe && (
            <>
              <div className="modal-section modal-section-icon">
                <label>
                  <IconInfo />
                  <span>Description</span>
                </label>
                <p className="modal-desc">{describe.description || "No description."}</p>
              </div>

              {toolList.length > 0 && (
                <div className="modal-section modal-section-icon">
                  <label>
                    <IconTools />
                    <span>Tools</span>
                  </label>
                  <ul className="tool-list">
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
                <div className="modal-section modal-section-icon">
                  <label>
                    <IconBudget />
                    <span>Budget</span>
                  </label>
                  <div className="budget-stats">
                    <span>Spent: ${Number(describe.budget.spent ?? 0).toFixed(4)}</span>
                    <span>Remaining: ${Number(describe.budget.remaining ?? 0).toFixed(4)}</span>
                    <span>{Number(describe.budget.percent_used ?? 0).toFixed(1)}% used</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </aside>
    </>
  );
}
