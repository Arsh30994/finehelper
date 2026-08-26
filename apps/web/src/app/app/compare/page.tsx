"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { compareRuns } from "@/api";
import type { Run } from "@/types";
import { ErrorText, PageHeader } from "@/components/ui";

function CompareInner() {
  const params = useSearchParams();
  const aId = params.get("a") || "";
  const bId = params.get("b") || "";
  const [data, setData] = useState<{ a: Run; b: Run } | null>(null);
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
    ...Object.keys(data?.a.evals?.[0]?.metrics || {}),
    ...Object.keys(data?.b.evals?.[0]?.metrics || {}),
  ]);

  return (
    <>
      <PageHeader
        title="Compare runs"
        description={
          <>
            Pairwise eval on the same golden suite. Pass <span className="font-mono">?a=&amp;b=</span> run ids.
          </>
        }
      />
      <ErrorText>{error}</ErrorText>
      {!aId || !bId ? (
        <p className="text-sm text-zinc-500">Select two runs from a project page to compare.</p>
      ) : (
        <table className="fh-card w-full overflow-hidden text-sm">
          <thead>
            <tr className="bg-mist-100 text-left text-zinc-500">
              <th className="p-4 font-normal">Field</th>
              <th className="p-4 font-normal">
                <Link className="text-wine-600 hover:underline" href={`/app/runs/${aId}`}>
                  {aId.slice(0, 8)}
                </Link>
              </th>
              <th className="p-4 font-normal">
                <Link className="text-wine-600 hover:underline" href={`/app/runs/${bId}`}>
                  {bId.slice(0, 8)}
                </Link>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-t border-mist-200">
              <td className="p-4 text-zinc-500">Backend</td>
              <td className="p-4">{data?.a.backend}</td>
              <td className="p-4">{data?.b.backend}</td>
            </tr>
            <tr className="border-t border-mist-200">
              <td className="p-4 text-zinc-500">Base model</td>
              <td className="p-4">{data?.a.base_model}</td>
              <td className="p-4">{data?.b.base_model}</td>
            </tr>
            {[...metrics].map((m) => (
              <tr key={m} className="border-t border-mist-200">
                <td className="p-4 text-zinc-500">{m}</td>
                <td className="p-4 font-mono text-xs">{(data?.a.evals?.[0]?.metrics[m] ?? data?.a.metrics?.[m]) ?? "—"}</td>
                <td className="p-4 font-mono text-xs">{(data?.b.evals?.[0]?.metrics[m] ?? data?.b.metrics?.[m]) ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<p className="text-sm text-zinc-500">Loading comparison…</p>}>
      <CompareInner />
    </Suspense>
  );
}
