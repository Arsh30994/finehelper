"use client";

import { useCallback, useEffect, useState } from "react";
import { trustBootstrap, trustDashboard } from "@/api";
import type { TrustDashboard } from "@/types";

/** Factors from API are 0–100; tolerate legacy 0–1. */
export function factorPercent(v: number): number {
  if (!Number.isFinite(v)) return 0;
  return Math.max(0, Math.min(100, Math.round(v <= 1 ? v * 100 : v)));
}

export function useTrustDashboard(opts?: { autofill?: boolean }) {
  const autofill = opts?.autofill !== false;
  const [data, setData] = useState<TrustDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filling, setFilling] = useState(false);

  const refresh = useCallback(async () => {
    setError("");
    try {
      const d = await trustDashboard();
      setData(d);
      return d;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "failed to load";
      setError(msg);
      throw e;
    }
  }, []);

  const ensureAssumedData = useCallback(async () => {
    setFilling(true);
    setError("");
    try {
      const d = await trustBootstrap({ occupation: "kirana", quality: "good", force: false });
      setData(d);
      return d;
    } catch (e) {
      const msg = e instanceof Error ? e.message : "failed to load assumed data";
      setError(msg);
      throw e;
    } finally {
      setFilling(false);
    }
  }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        let d = await trustDashboard();
        if (!alive) return;
        const empty = !d.score || !d.signals_summary;
        if (autofill && empty) {
          setFilling(true);
          try {
            d = await trustBootstrap({ occupation: "kirana", quality: "good", force: false });
          } finally {
            if (alive) setFilling(false);
          }
        }
        if (alive) setData(d);
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : "failed to load");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [autofill]);

  return { data, loading, filling, error, setError, refresh, setData, ensureAssumedData };
}
