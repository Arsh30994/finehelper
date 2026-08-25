"use client";

import { FormEvent, useEffect, useState } from "react";
import AppShell from "../app-shell";
import { api } from "@/lib/api";

type Deployment = { id: string; name: string; backend: string; run_id: string };
type Run = { id: string; provider_model_id?: string; backend: string };

export default function PlaygroundPage() {
  const [deps, setDeps] = useState<Deployment[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [reply, setReply] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<Deployment[]>("/v1/deployments").then(setDeps).catch(() => setDeps([]));
    api<Run[]>("/v1/runs").then(setRuns).catch(() => setRuns([]));
  }, []);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setReply("");
    const fd = new FormData(e.currentTarget);
    try {
      const data = await api<{ choices: { message: { content: string } }[] }>("/v1/chat/completions", {
        method: "POST",
        body: JSON.stringify({
          deployment_id: fd.get("deployment_id") || null,
          run_id: fd.get("run_id") || null,
          messages: [{ role: "user", content: fd.get("message") }],
        }),
      });
      setReply(data.choices[0].message.content);
    } catch (err) {
      setError(err instanceof Error ? err.message : "chat failed");
    }
  }

  return (
    <AppShell>
      <h1 className="text-2xl font-medium mb-2">Playground</h1>
      <p className="text-sm text-zinc-500 mb-8">OpenAI-compatible /v1/chat/completions against a run or deployment.</p>
      <form onSubmit={onSubmit} className="space-y-4 max-w-xl">
        <label className="block text-xs text-zinc-500">
          Deployment
          <select name="deployment_id" className="mt-1 w-full bg-ink-800 border border-ink-700 rounded px-3 py-2 text-sm">
            <option value="">—</option>
            {deps.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.backend})
              </option>
            ))}
          </select>
        </label>
        <label className="block text-xs text-zinc-500">
          Or run
          <select name="run_id" className="mt-1 w-full bg-ink-800 border border-ink-700 rounded px-3 py-2 text-sm">
            <option value="">—</option>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                {r.id.slice(0, 8)} {r.backend} {r.provider_model_id || ""}
              </option>
            ))}
          </select>
        </label>
        <textarea name="message" required rows={4} className="w-full bg-ink-800 border border-ink-700 rounded px-3 py-2 text-sm" placeholder="Ask the fine-tune…" />
        <button className="bg-copper-500 text-ink-950 text-sm font-medium rounded px-4 py-2">Send</button>
      </form>
      {error && <p className="text-xs text-red-400 mt-4 break-all">{error}</p>}
      {reply && <pre className="mt-6 text-sm whitespace-pre-wrap bg-ink-900 border border-ink-700 rounded p-4">{reply}</pre>}
    </AppShell>
  );
}
