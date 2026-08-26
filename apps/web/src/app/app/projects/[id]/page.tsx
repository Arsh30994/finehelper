"use client";

import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import AppShell from "../../app-shell";
import { createDataset, getDataset, getProject, listDatasets, listJobs, listRuns, startTrain, uploadDatasetFile } from "@/api";
import Link from "next/link";

type Project = { id: string; name: string; slug: string; default_backend: string; default_base_model: string };
type Dataset = { id: string; name: string };
type Version = {
  id: string;
  status: string;
  row_count: number;
  content_digest: string;
  stats?: { approx_tokens_p50?: number };
};
type Run = {
  id: string;
  backend: string;
  base_model: string;
  provider_model_id?: string;
  metrics?: Record<string, number>;
  created_at: string;
};
type Job = { id: string; type: string; status: string };

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [versions, setVersions] = useState<Record<string, Version[]>>({});
  const [runs, setRuns] = useState<Run[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const [p, ds, r, j] = await Promise.all([
      getProject(id),
      listDatasets(id),
      listRuns(id),
      listJobs(id),
    ]);
    setProject(p);
    setDatasets(ds);
    setRuns(r);
    setJobs(j);
    const vs: Record<string, Version[]> = {};
    for (const d of ds) {
      const full = await getDataset(d.id);
      vs[d.id] = full.versions;
    }
    setVersions(vs);
  }, [id]);

  useEffect(() => {
    load().catch((e) => setMsg(String(e.message || e)));
  }, [load]);

  async function onCreateDataset(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    await createDataset({ project_id: id, name: fd.get("name") });
    await load();
  }

  async function onUpload(datasetId: string, file: File) {
    setMsg("uploading…");
    const job = await uploadDatasetFile(datasetId, file, { format: "openai-chat" });
    setMsg(`ingest job ${job.job_id}`);
    setTimeout(() => load(), 2000);
  }

  async function train(versionId: string) {
    if (!project) return;
    const job = await startTrain({
      project_id: project.id,
      dataset_version_id: versionId,
      backend: project.default_backend,
    });
    setMsg(`train job ${job.job_id}`);
    setTimeout(() => load(), 2500);
  }

  return (
    <AppShell>
      <p className="text-xs text-zinc-500 mb-2">
        <Link href="/app">Projects</Link> / {project?.slug}
      </p>
      <h1 className="text-2xl font-medium">{project?.name}</h1>
      <p className="text-sm text-zinc-500 mt-1 mb-8">
        {project?.default_backend} · {project?.default_base_model}
      </p>
      {msg && <p className="text-xs text-copper-300 mb-4 font-mono">{msg}</p>}

      <section className="mb-10">
        <h2 className="text-sm uppercase tracking-wide text-zinc-500 mb-3">Datasets</h2>
        <form onSubmit={onCreateDataset} className="flex gap-2 mb-4">
          <input name="name" placeholder="support-v1" required className="bg-ink-800 border border-ink-700 rounded px-3 py-2 text-sm" />
          <button className="text-sm border border-ink-700 rounded px-3">New dataset</button>
        </form>
        <div className="space-y-4">
          {datasets.map((d) => (
            <div key={d.id} className="border border-ink-700 rounded p-4">
              <div className="flex items-center justify-between mb-3">
                <p className="font-medium">{d.name}</p>
                <label className="text-xs text-copper-300 cursor-pointer">
                  Upload JSONL
                  <input
                    type="file"
                    accept=".jsonl,.json,.csv"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) onUpload(d.id, f);
                    }}
                  />
                </label>
              </div>
              <table className="w-full text-xs">
                <thead className="text-zinc-500">
                  <tr>
                    <th className="text-left font-normal py-1">version</th>
                    <th className="text-left font-normal">status</th>
                    <th className="text-left font-normal">rows</th>
                    <th className="text-left font-normal">digest</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {(versions[d.id] || []).map((v) => (
                    <tr key={v.id} className="border-t border-ink-700">
                      <td className="py-2 font-mono">{v.id.slice(0, 8)}</td>
                      <td>{v.status}</td>
                      <td>{v.row_count}</td>
                      <td className="font-mono">{(v.content_digest || "").slice(0, 12)}</td>
                      <td className="text-right">
                        {v.status === "ready" && (
                          <button className="text-copper-300" onClick={() => train(v.id)}>
                            Train
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-10">
        <h2 className="text-sm uppercase tracking-wide text-zinc-500 mb-3">Runs</h2>
        <div className="border border-ink-700 rounded divide-y divide-ink-700">
          {runs.length === 0 && <p className="p-4 text-sm text-zinc-500">No runs yet.</p>}
          {runs.map((r) => (
            <Link key={r.id} href={`/app/runs/${r.id}`} className="flex justify-between px-4 py-3 text-sm hover:bg-ink-800">
              <span className="font-mono">{r.id.slice(0, 8)}</span>
              <span>
                {r.backend} · {r.base_model}
              </span>
              <span className="text-zinc-500">{r.provider_model_id || "—"}</span>
            </Link>
          ))}
        </div>
        {runs.length >= 2 && (
          <p className="text-xs mt-2">
            <Link className="text-copper-300" href={`/app/compare?a=${runs[0].id}&b=${runs[1].id}`}>
              Compare latest two runs
            </Link>
          </p>
        )}
      </section>

      <section>
        <h2 className="text-sm uppercase tracking-wide text-zinc-500 mb-3">Recent jobs</h2>
        <div className="border border-ink-700 rounded divide-y divide-ink-700 text-sm">
          {jobs.slice(0, 12).map((j) => (
            <Link key={j.id} href={`/app/jobs/${j.id}`} className="flex justify-between px-4 py-2 hover:bg-ink-800">
              <span className="font-mono text-xs">{j.id.slice(0, 8)}</span>
              <span>{j.type}</span>
              <span className={j.status === "failed" ? "text-red-400" : j.status === "succeeded" ? "text-copper-300" : "text-zinc-400"}>
                {j.status}
              </span>
            </Link>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
