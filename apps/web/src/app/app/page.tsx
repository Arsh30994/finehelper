"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import AppShell from "../app-shell";
import { api } from "@/lib/api";

type Project = {
  id: string;
  name: string;
  slug: string;
  default_backend: string;
  default_base_model: string;
  task_type: string;
};

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState("");

  async function refresh() {
    setProjects(await api<Project[]>("/v1/projects"));
  }

  useEffect(() => {
    refresh().catch((e) => setError(String(e.message || e)));
  }, []);

  async function onCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    await api("/v1/projects", {
      method: "POST",
      body: JSON.stringify({
        name: fd.get("name"),
        default_backend: fd.get("backend") || "dry_run",
        default_base_model: fd.get("base") || "gpt-4.1-mini",
      }),
    });
    (e.target as HTMLFormElement).reset();
    await refresh();
  }

  return (
    <AppShell>
      <div className="flex items-end justify-between mb-8">
        <div>
          <h1 className="text-2xl font-medium">Projects</h1>
          <p className="text-sm text-zinc-500 mt-1">A project is a task, a default backend, and a quality gate.</p>
        </div>
      </div>
      {error && <p className="text-sm text-red-400 mb-4">{error}</p>}
      <form onSubmit={onCreate} className="flex gap-2 mb-8">
        <input name="name" placeholder="support-bot" required className="bg-ink-800 border border-ink-700 rounded px-3 py-2 text-sm w-48" />
        <select name="backend" className="bg-ink-800 border border-ink-700 rounded px-3 py-2 text-sm">
          <option value="dry_run">dry_run</option>
          <option value="openai">openai</option>
          <option value="lora_modal">lora_modal</option>
          <option value="lora_local">lora_local</option>
        </select>
        <input name="base" placeholder="base model" className="bg-ink-800 border border-ink-700 rounded px-3 py-2 text-sm w-56" />
        <button className="bg-copper-500 text-ink-950 text-sm font-medium rounded px-4">Create</button>
      </form>
      <div className="divide-y divide-ink-700 border border-ink-700 rounded">
        {projects.length === 0 && <p className="p-4 text-sm text-zinc-500">No projects yet.</p>}
        {projects.map((p) => (
          <Link key={p.id} href={`/app/projects/${p.id}`} className="flex items-center justify-between px-4 py-3 hover:bg-ink-800">
            <div>
              <p className="font-medium">{p.name}</p>
              <p className="text-xs text-zinc-500 font-mono">{p.slug}</p>
            </div>
            <p className="text-xs text-zinc-400">
              {p.default_backend} · {p.default_base_model}
            </p>
          </Link>
        ))}
      </div>
    </AppShell>
  );
}
