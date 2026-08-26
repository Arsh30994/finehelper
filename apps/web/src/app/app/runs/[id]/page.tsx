"use client";

import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import AppShell from "../../app-shell";
import { createDeployment, getRun, startEval } from "@/api";
import Link from "next/link";

type EvalRow = { id: string; passed: boolean; metrics: Record<string, number> };
type Run = {
  id: string;
  backend: string;
  base_model: string;
  provider_model_id?: string | null;
  adapter_uri?: string | null;
  metrics?: Record<string, number> | null;
  hyperparams?: Record<string, unknown> | null;
  evals: EvalRow[];
  dataset_version_id: string;
  job_id: string;
};

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
    <AppShell>
      <h1 className="text-2xl font-medium font-mono">{id.slice(0, 8)}</h1>
      <p className="text-sm text-zinc-500 mt-1 mb-6">
        {run?.backend} · {run?.base_model}
      </p>
      {msg && <p className="text-xs text-copper-300 mb-4">{msg}</p>}
      <dl className="grid grid-cols-2 gap-3 text-sm mb-8">
        <dt className="text-zinc-500">Provider model</dt>
        <dd className="font-mono text-xs">{run?.provider_model_id || "—"}</dd>
        <dt className="text-zinc-500">Adapter</dt>
        <dd className="font-mono text-xs break-all">{run?.adapter_uri || "—"}</dd>
        <dt className="text-zinc-500">Metrics</dt>
        <dd className="font-mono text-xs">{JSON.stringify(run?.metrics || {})}</dd>
        <dt className="text-zinc-500">Train job</dt>
        <dd>
          <Link className="text-copper-300" href={`/app/jobs/${run?.job_id}`}>
            {run?.job_id?.slice(0, 8)}
          </Link>
        </dd>
      </dl>

      <h2 className="text-sm uppercase tracking-wide text-zinc-500 mb-2">Evals</h2>
      <div className="border border-ink-700 rounded divide-y divide-ink-700 text-sm mb-6">
        {(run?.evals || []).length === 0 && <p className="p-3 text-zinc-500">No eval yet — a run is not production-ready until it has one.</p>}
        {(run?.evals || []).map((ev) => (
          <div key={ev.id} className="px-3 py-2 flex justify-between">
            <span className="font-mono text-xs">{ev.id.slice(0, 8)}</span>
            <span>{ev.passed ? "passed" : "gate failed"}</span>
            <span className="font-mono text-xs">{JSON.stringify(ev.metrics)}</span>
          </div>
        ))}
      </div>

      <form onSubmit={runEval} className="flex items-end gap-3 mb-4">
        <label className="text-xs text-zinc-500">
          Golden suite (JSONL)
          <input name="suite" type="file" required accept=".jsonl,.json" className="block mt-1 text-sm" />
        </label>
        <label className="text-xs text-zinc-500">
          Min exact_match
          <input name="min" defaultValue="0.8" className="block mt-1 bg-ink-800 border border-ink-700 rounded px-2 py-1 w-20" />
        </label>
        <button className="bg-ink-700 rounded px-3 py-2 text-sm">Run eval</button>
      </form>
      <button onClick={deploy} className="text-sm text-copper-300">
        Deploy (blocked unless eval passed, unless you override via CLI)
      </button>
    </AppShell>
  );
}
