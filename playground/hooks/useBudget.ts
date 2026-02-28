"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface BudgetData {
  limit?: number;
  remaining?: number;
  spent?: number;
  percent_used?: number;
}

export function useBudget(apiBase: string, agentName: string, enabled: boolean) {
  const [budget, setBudget] = useState<BudgetData | null>(null);
  const hasBudgetRef = useRef<boolean | null>(null);

  const load = useCallback(async () => {
    if (!apiBase || !enabled) return;
    if (hasBudgetRef.current === false) return;
    const path = agentName ? `${agentName}/budget` : "budget";
    const url = `${apiBase.replace(/\/$/, "")}/${path}`;
    try {
      const res = await fetch(url);
      if (res.status === 404) {
        hasBudgetRef.current = false;
        setBudget(null);
        return;
      }
      if (!res.ok) return;
      const data: BudgetData = await res.json();
      hasBudgetRef.current = true;
      setBudget(data);
    } catch {
      setBudget(null);
    }
  }, [apiBase, agentName, enabled]);

  const updateFromStream = useCallback((data: BudgetData | null) => {
    hasBudgetRef.current = data != null;
    setBudget(data);
  }, []);

  useEffect(() => {
    hasBudgetRef.current = null;
    setBudget(null);
    if (!enabled) return;
    load();
  }, [enabled, agentName, load]);

  const formatBudget = (): string | null => {
    if (!budget) return null;
    const pct = budget.percent_used ?? 0;
    const spent = budget.spent != null ? `$${Number(budget.spent).toFixed(4)}` : "";
    const remaining = budget.remaining != null ? `$${Number(budget.remaining).toFixed(4)}` : "";
    return `${spent} spent · ${remaining} remaining (${pct.toFixed(1)}% used)`;
  };

  return { budget, formatBudget, refresh: load, updateFromStream };
}
