"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { createDeployment, getRun, startEval } from "@/api";
import type { Run } from "@/types";
import { EmptyState, MetricRow, PageHeader, Panel, btnAccentClass, btnGhostClass, btnPrimaryClass, inputClass } from "@/components/ui";

export default function RunPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [run, setRun] = useState<Run | null>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    getRun(id).then(setRun).catch((e) => setMsg(String(e.message || e)));
  }, [id]);

  async function runEval(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const file = fd.get("suite") as File;
    const text = await file.text();
    const items = text.trim().startsWith("[")
      ? JSON.parse(text)
      : text
          .split("\n")
          .filter(Boolean)
          .map((l) => JSON.parse(l));
    const job = await startEval({
      run_id: id,
      suite_inline: items,
      metrics: ["exact_match"],
      gate: { metric: "exact_match", min: Number(fd.get("min") || 0.8) },
    });
    setMsg(`eval job ${job.job_id}`);
    router.push(`/app/jobs/${job.job_id}`);
  }

  async function deploy() {
    const job = await createDeployment({ run_id: id, name: "prod" });
    router.push(`/app/jobs/${job.job_id}`);
  }

  return (
    <>
      <PageHeader
        title={<span className="font-mono">{id.slice(0, 8)}</span>}
        description={`${run?.backend || "…"} · ${run?.base_model || ""}`}
      />
      {msg && <p className="mb-4 text-xs text-wine-500">{msg}</p>}

      <div className="fh-card mb-6 grid gap-0 md:grid-cols-2">
        <div className="border-b border-mist-200 p-6 md:border-b-0 md:border-r">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-wine-500">Run identity</p>
          <h2 className="mt-2 font-display text-2xl text-wine-700">{run?.base_model || "Loading…"}</h2>
          <p className="mt-1 text-sm text-zinc-500">{run?.backend}</p>
          <dl className="mt-6 space-y-3 text-sm">
            <div>
              <dt className="text-[11px] uppercase text-zinc-400">Provider model</dt>
              <dd className="font-mono text-xs">{run?.provider_model_id || "—"}</dd>
            </div>
            <div>
              <dt className="text-[11px] uppercase text-zinc-400">Adapter</dt>
              <dd className="break-all font-mono text-xs">{run?.adapter_uri || "—"}</dd>
            </div>
            <div>
              <dt className="text-[11px] uppercase text-zinc-400">Train job</dt>
              <dd>
                <Link className="text-wine-500 hover:underline" href={`/app/jobs/${run?.job_id}`}>
                  {run?.job_id?.slice(0, 8)}
                </Link>
              </dd>
            </div>
          </dl>
        </div>
        <div className="p-6">
          <h3 className="font-display text-2xl text-wine-600">Training credential</h3>
          <div className="mt-3">
            <MetricRow label="Backend" hint="Where this run trained" value={run?.backend || "—"} />
            <MetricRow
              label="Metrics"
              hint="Logged training metrics"
              value={<span className="font-mono text-sm">{JSON.stringify(run?.metrics || {})}</span>}
            />
            <MetricRow label="Evals" hint="Golden suite reports" value={(run?.evals || []).length} />
          </div>
          <button onClick={deploy} className={`${btnAccentClass} mt-4 w-full`}>
            Deploy model →
          </button>
        </div>
      </div>

      <h2 className="mb-2 font-display text-xl text-wine-600">Evals</h2>
      <Panel className="mb-6 text-sm">
        {(run?.evals || []).length === 0 && (
          <EmptyState>No eval yet — a run is not production-ready until it has one.</EmptyState>
        )}
        {(run?.evals || []).map((ev) => (
          <div key={ev.id} className="flex justify-between px-4 py-3">
            <span className="font-mono text-xs">{ev.id.slice(0, 8)}</span>
            <span>{ev.passed ? "passed" : "gate failed"}</span>
            <span className="font-mono text-xs">{JSON.stringify(ev.metrics)}</span>
          </div>
        ))}
      </Panel>

      <form onSubmit={runEval} className="fh-card flex flex-wrap items-end gap-3 p-5">
        <label className="text-xs font-semibold text-wine-700">
          Golden suite (JSONL)
          <input name="suite" type="file" required accept=".jsonl,.json" className="mt-1.5 block text-sm" />
        </label>
        <label className="text-xs font-semibold text-wine-700">
          Min exact_match
          <input name="min" defaultValue="0.8" className={`mt-1.5 block ${inputClass} w-24`} />
        </label>
        <button className={btnPrimaryClass}>Run eval</button>
        <Link href={`/app/playground`} className={btnGhostClass}>
          Chat in playground
        </Link>
      </form>
    </>
  );
}
