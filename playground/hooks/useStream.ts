"use client";

import { useCallback } from "react";
import { StreamChunk } from "@/lib/api";

export interface BudgetData {
  limit?: number;
  remaining?: number;
  spent?: number;
  percent_used?: number;
}

export interface MessageData {
  role: "user" | "assistant";
  content: string;
  meta?: string;
  isError?: boolean;
  events?: Array<{ hook: string; ctx: Record<string, unknown> }>;
  cost?: number;
  tokens?: Record<string, number>;
}

export interface ActivityEntry {
  id: string;
  kind: "status" | "hook";
  label: string;
}

function formatHookLabel(hook: string, ctx: Record<string, unknown>): string {
  const tool = ctx?.tool ?? ctx?.tool_name;
  const agent = ctx?.agent_type ?? ctx?.agent ?? ctx?.agent_name;
  const model = ctx?.model ?? ctx?.model_name;
  const remaining = ctx?.remaining ?? ctx?.budget_remaining;
  const task = ctx?.task;

  switch (hook) {
    case "agent.run.start":
      return "Agent run started";
    case "agent.run.end":
      return "Agent run complete";
    case "agent.init":
      return "Agent initialized";
    case "agent.reset":
      return "Agent reset";
    case "llm.request.start":
      return model ? `LLM: ${model}` : "LLM call started";
    case "llm.request.end":
      return "LLM call complete";
    case "llm.retry":
      return "LLM retry";
    case "llm.fallback":
      return "LLM fallback";
    case "tool.call.start":
      return tool ? `Tool "${tool}" called` : "Tool called";
    case "tool.call.end":
      return tool ? `Tool "${tool}" complete` : "Tool complete";
    case "tool.error":
      return tool ? `Tool "${tool}" error` : "Tool error";
    case "budget.check":
      return "Budget check";
    case "budget.threshold":
      return remaining != null
        ? `Cost threshold ($${Number(remaining).toFixed(2)} remaining)`
        : "Cost threshold hit";
    case "budget.exceeded":
      return "Budget exceeded";
    case "guardrail.input":
      return "Guardrail input";
    case "guardrail.output":
      return "Guardrail output";
    case "guardrail.blocked":
      return "Guardrail blocked";
    case "memory.store":
      return "Memory store";
    case "memory.recall":
      return "Memory recall";
    case "memory.forget":
      return "Memory forget";
    case "checkpoint.save":
      return "Checkpoint save";
    case "checkpoint.load":
      return "Checkpoint load";
    case "dynamic.pipeline.start":
      return task ? `Dynamic pipeline: ${String(task).slice(0, 40)}...` : "Dynamic pipeline start";
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
      return "Pipeline start";
    case "pipeline.end":
      return "Pipeline end";
    case "pipeline.agent.start":
      return agent ? `Pipeline: ${agent}` : "Pipeline agent started";
    case "pipeline.agent.complete":
      return agent ? `Pipeline: ${agent} done` : "Pipeline agent complete";
    case "handoff.start":
      return "Handoff start";
    case "handoff.end":
      return "Handoff end";
    case "spawn.start":
      return "Spawn start";
    case "spawn.end":
      return "Spawn end";
    case "hitl.pending":
      return "Human-in-the-loop pending";
    case "hitl.approved":
      return "Human-in-the-loop approved";
    case "hitl.rejected":
      return "Human-in-the-loop rejected";
    case "output.validation.start":
      return "Output validation start";
    case "output.validation.success":
      return "Output validation success";
    case "output.validation.failed":
      return "Output validation failed";
    default:
      return hook.replace(/\./g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

function parseStreamChunk(line: string): StreamChunk | null {
  if (!line.startsWith("data: ")) return null;
  try {
    return JSON.parse(line.slice(6)) as StreamChunk;
  } catch {
    return null;
  }
}

export interface StreamCallbacks {
  onStatus: (label: string) => void;
  onHook: (hook: string, ctx: Record<string, unknown>) => void;
  onText: (accumulated: string) => void;
  onBudget?: (data: BudgetData) => void;
  onDone: (opts: {
    cost?: number;
    tokens?: Record<string, number>;
    events?: Array<{ hook: string; ctx: Record<string, unknown> }>;
    budget?: BudgetData;
  }) => void;
  onError: (err: Error) => void;
}

export function createStreamProcessor(
  callbacks: StreamCallbacks
): (reader: ReadableStreamDefaultReader<Uint8Array>) => Promise<void> {
  return async (reader) => {
    const decoder = new TextDecoder();
    let buf = "";

    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() || "";

        for (const line of lines) {
          const data = parseStreamChunk(line);
          if (!data) continue;

          const type = (data as { type?: string }).type;

          if (type === "status") {
            const msg = (data as { message?: string }).message;
            if (msg) callbacks.onStatus(msg);
            continue;
          }

          if (type === "hook") {
            const { hook, ctx } = data as { hook: string; ctx: Record<string, unknown> };
            callbacks.onHook(hook, ctx || {});
            continue;
          }

          if (type === "budget") {
            const b = data as BudgetData;
            if (callbacks.onBudget) callbacks.onBudget(b);
            continue;
          }

          if (type === "done") {
            const d = data as {
              cost?: number;
              tokens?: Record<string, number>;
              events?: Array<{ hook: string; ctx: Record<string, unknown> }>;
              budget?: BudgetData;
            };
            callbacks.onDone({
              cost: d.cost,
              tokens: d.tokens,
              events: d.events,
              budget: d.budget,
            });
            continue;
          }

          if (type === "text") {
            const acc = (data as { accumulated?: string }).accumulated ?? "";
            callbacks.onText(acc);
            continue;
          }

          // Legacy format
          if ((data as { done?: boolean }).done) {
            const d = data as {
              cost?: number;
              tokens?: Record<string, number>;
              events?: Array<{ hook: string; ctx: Record<string, unknown> }>;
              budget?: BudgetData;
            };
            callbacks.onDone({
              cost: d.cost,
              tokens: d.tokens,
              events: d.events,
              budget: d.budget,
            });
          } else if ((data as { text?: string }).text != null) {
            const acc = (data as { accumulated?: string }).accumulated ?? "";
            callbacks.onText(acc);
          }
        }
      }
    } catch (err) {
      callbacks.onError(err instanceof Error ? err : new Error(String(err)));
    }
  };
}

export function formatHookLabelForActivity(hook: string, ctx: Record<string, unknown>): string {
  return formatHookLabel(hook, ctx);
}
