"use client";

function formatHookLabel(hook: string, ctx: Record<string, unknown>): string {
  const tool = ctx?.tool ?? ctx?.tool_name;
  const agent = ctx?.agent_type ?? ctx?.agent ?? ctx?.agent_name;
  const model = ctx?.model ?? ctx?.model_name;

  switch (hook) {
    case "agent.run.start":
      return "Agent run started";
    case "agent.run.end":
      return "Agent run complete";
    case "agent.init":
      return "Agent init";
    case "llm.request.start":
      return model ? `LLM: ${model}` : "LLM started";
    case "llm.request.end":
      return "LLM complete";
    case "tool.call.start":
      return tool ? `Tool "${tool}"` : "Tool called";
    case "tool.call.end":
      return tool ? `Tool "${tool}" done` : "Tool complete";
    case "tool.error":
      return "Tool error";
    case "budget.check":
      return "Budget check";
    case "budget.threshold":
      return "Cost threshold";
    case "budget.exceeded":
      return "Budget exceeded";
    case "guardrail.input":
    case "guardrail.output":
    case "guardrail.blocked":
      return hook.replace(/\./g, " ");
    case "memory.store":
    case "memory.recall":
    case "memory.forget":
      return hook.replace(/\./g, " ");
    case "checkpoint.save":
    case "checkpoint.load":
      return hook.replace(/\./g, " ");
    case "dynamic.pipeline.start":
      return "Dynamic pipeline start";
    case "dynamic.pipeline.plan":
      return "Dynamic pipeline plan";
    case "dynamic.pipeline.execute":
      return "Dynamic pipeline execute";
    case "dynamic.pipeline.agent.spawn":
      return agent ? `Spawned "${agent}"` : "Agent spawned";
    case "dynamic.pipeline.agent.complete":
      return agent ? `"${agent}" complete` : "Agent complete";
    case "dynamic.pipeline.end":
      return "Dynamic pipeline end";
    case "dynamic.pipeline.error":
      return "Dynamic pipeline error";
    case "pipeline.start":
    case "pipeline.end":
      return hook.replace(/\./g, " ");
    case "pipeline.agent.start":
      return agent ? `Pipeline: ${agent}` : "Pipeline started";
    case "pipeline.agent.complete":
      return agent ? `${agent} done` : "Pipeline complete";
    case "handoff.start":
    case "handoff.end":
    case "spawn.start":
    case "spawn.end":
    case "hitl.pending":
    case "hitl.approved":
    case "hitl.rejected":
    case "output.validation.start":
    case "output.validation.success":
    case "output.validation.failed":
      return hook.replace(/\./g, " ");
    default:
      return hook.replace(/\./g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

function EventCard({ hook, ctx }: { hook: string; ctx: Record<string, unknown> }) {
  const label = formatHookLabel(hook, ctx);
  const keys = Object.keys(ctx).filter(
    (k) => !["tokens", "token_usage"].includes(k) && ctx[k] != null
  );

  return (
    <div className="trace-event-card">
      <div className="trace-event-label">{label}</div>
      {keys.length > 0 && (
        <div className="trace-event-ctx">
          {keys.map((k) => (
            <div key={k} className="trace-event-row">
              <span className="trace-event-key">{k}:</span>
              <span className="trace-event-val">
                {typeof ctx[k] === "object" ? JSON.stringify(ctx[k]) : String(ctx[k])}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface TraceSidebarProps {
  events: Array<{ hook: string; ctx: Record<string, unknown> }>;
  cost?: number;
  tokens?: {
    total?: number;
    total_tokens?: number;
    input_tokens?: number;
    output_tokens?: number;
  };
  onClose: () => void;
  isOpen: boolean;
}

export function TraceSidebar({ events, cost, tokens, onClose, isOpen }: TraceSidebarProps) {
  if (!isOpen) return null;

  const totalTokens =
    tokens?.total_tokens ??
    tokens?.total ??
    (tokens?.input_tokens ?? 0) + (tokens?.output_tokens ?? 0);

  return (
    <>
      <div className="trace-sidebar-overlay" onClick={onClose} aria-hidden="true" />
      <aside className="trace-sidebar" role="dialog" aria-label="Reply trace">
        <div className="trace-sidebar-header">
          <h3>Reply trace</h3>
          <button
            type="button"
            className="trace-sidebar-close"
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <div className="trace-sidebar-body">
          {(cost != null || totalTokens > 0) && (
            <div className="trace-meta-cards">
              {cost != null && (
                <div className="trace-meta-card">
                  <span className="trace-meta-label">Cost</span>
                  <span className="trace-meta-val">${Number(cost).toFixed(6)}</span>
                </div>
              )}
              {totalTokens > 0 && (
                <div className="trace-meta-card">
                  <span className="trace-meta-label">Tokens</span>
                  <span className="trace-meta-val">{totalTokens}</span>
                </div>
              )}
            </div>
          )}
          <div className="trace-events-list">
            {events.map((e, i) => (
              <EventCard key={i} hook={e.hook} ctx={e.ctx} />
            ))}
          </div>
        </div>
      </aside>
    </>
  );
}
