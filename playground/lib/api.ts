export interface AgentOption {
  name: string;
  description?: string;
}

export interface PlaygroundConfig {
  apiBase: string;
  agents: AgentOption[];
  debug: boolean;
  setup_type?: "single" | "multi" | "dynamic_pipeline" | "pipeline";
}

export interface BudgetData {
  limit?: number;
  remaining?: number;
  spent?: number;
  percent_used?: number;
}

export interface DescribeData {
  name: string;
  description: string;
  tools: string[] | Array<{ name: string; description?: string }>;
  budget?: BudgetData;
  internal_agents?: string[];
  setup_type?: "single" | "multi" | "dynamic_pipeline" | "pipeline";
}

export interface StreamChunkText {
  type?: "text";
  text?: string;
  accumulated?: string;
}

export interface StreamChunkDone {
  type?: "done";
  done?: boolean;
  cost?: number;
  budget_remaining?: number;
  tokens?: {
    total?: number;
    total_tokens?: number;
    input_tokens?: number;
    output_tokens?: number;
  };
  events?: Array<{ hook: string; ctx: Record<string, unknown> }>;
}

export interface StreamChunkStatus {
  type: "status";
  message: string;
}

export interface StreamChunkHook {
  type: "hook";
  hook: string;
  ctx: Record<string, unknown>;
}

export type StreamChunk =
  | StreamChunkText
  | StreamChunkDone
  | StreamChunkStatus
  | StreamChunkHook
  | (StreamChunkText & { done?: boolean });

export async function fetchConfig(baseUrl = ""): Promise<PlaygroundConfig> {
  const url = `${baseUrl || ""}./config`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch config");
  const data: PlaygroundConfig = await res.json();
  const apiBase = (data.apiBase || "").replace(/\/+$/, "");
  return { ...data, apiBase: apiBase ? `${apiBase}/` : "/" };
}

export async function fetchBudget(apiBase: string, agentName?: string): Promise<BudgetData | null> {
  const path = agentName ? `${agentName}/budget` : "budget";
  const url = `${apiBase.replace(/\/$/, "")}/${path}`;
  const res = await fetch(url);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchDescribe(
  apiBase: string,
  agentName?: string
): Promise<DescribeData | null> {
  const path = agentName ? `${agentName}/describe` : "describe";
  const url = `${apiBase.replace(/\/$/, "")}/${path}`;
  const res = await fetch(url);
  if (!res.ok) return null;
  return res.json();
}
