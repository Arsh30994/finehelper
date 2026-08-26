"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import AppShell from "../../app-shell";
import { compareRuns } from "@/api";
import Link from "next/link";

type RunBundle = {
  id: string;
  backend: string;
  base_model: string;
  metrics?: Record<string, number> | null;
  evals: { id: string; passed: boolean; metrics: Record<string, number> }[];
};

function CompareInner() {
  const params = useSearchParams();
  const aId = params.get("a") || "";
  const bId = params.get("b") || "";
  const [data, setData] = useState<{ a: RunBundle; b: RunBundle } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!aId || !bId) return;
    compareRuns(aId, bId)
      .then(setData)
      .catch((e) => setError(String(e.message || e)));
  }, [aId, bId]);

  const metrics = new Set([
    ...Object.keys(data?.a.metrics || {}),
    ...Object.keys(data?.b.metrics || {}),
    ...Object.keys(data?.a.evals[0]?.metrics || {}),
    ...Object.keys(data?.b.evals[0]?.metrics || {}),
  ]);

  return (
    <AppShell>
      <h1 className="text-2xl font-medium mb-2">Compare runs</h1>
      <p className="text-sm text-zinc-500 mb-6">
        Pairwise eval on the same golden suite. Pass <span className="font-mono">?a=&amp;b=</span> run ids.
      </p>
      {error && <p className="text-xs text-red-400">{error}</p>}
      {!aId || !bId ? (
        <p className="text-sm text-zinc-500">Select two runs from a project page to compare.</p>
      ) : (
        <table className="w-full text-sm border border-ink-700">
          <thead>
            <tr className="text-left text-zinc-500">
              <th className="p-3 font-normal">Field</th>
              <th className="p-3 font-normal">
                <Link className="text-copper-300" href={`/app/runs/${aId}`}>
                  {aId.slice(0, 8)}
                </Link>
              </th>
              <th className="p-3 font-normal">
                <Link className="text-copper-300" href={`/app/runs/${bId}`}>
                  {bId.slice(0, 8)}
                </Link>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-t border-ink-700">
              <td className="p-3 text-zinc-500">Backend</td>
              <td className="p-3">{data?.a.backend}</td>
              <td className="p-3">{data?.b.backend}</td>
            </tr>
            <tr className="border-t border-ink-700">
              <td className="p-3 text-zinc-500">Base model</td>
              <td className="p-3">{data?.a.base_model}</td>
              <td className="p-3">{data?.b.base_model}</td>
            </tr>
            {[...metrics].map((m) => (
              <tr key={m} className="border-t border-ink-700">
                <td className="p-3 text-zinc-500">{m}</td>
                <td className="p-3 font-mono text-xs">{(data?.a.evals[0]?.metrics[m] ?? data?.a.metrics?.[m]) ?? "—"}</td>
                <td className="p-3 font-mono text-xs">{(data?.b.evals[0]?.metrics[m] ?? data?.b.metrics?.[m]) ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </AppShell>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<p className="p-8 text-sm text-zinc-500">Loading comparison…</p>}>
      <CompareInner />
    </Suspense>
  );
}
