"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchConfig, PlaygroundConfig } from "@/lib/api";

export function useConfig() {
  const [config, setConfig] = useState<PlaygroundConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchConfig();
      setConfig(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load config");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { config, loading, error };
}
