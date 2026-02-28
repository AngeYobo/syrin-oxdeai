"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchDescribe, DescribeData } from "@/lib/api";

export function useDescribe(apiBase: string, agentName: string, enabled: boolean) {
  const [describe, setDescribe] = useState<DescribeData | null>(null);

  const load = useCallback(async () => {
    if (!apiBase || !enabled) return;
    const data = await fetchDescribe(apiBase, agentName || undefined);
    setDescribe(data);
  }, [apiBase, agentName, enabled]);

  useEffect(() => {
    load();
  }, [load]);

  return { describe, refresh: load };
}
