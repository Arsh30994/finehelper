"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { createDataset, getDataset, getProject, listDatasets, listJobs, listRuns, startTrain, uploadDatasetFile } from "@/api";
import type { Dataset, DatasetVersion, Job, Project, Run } from "@/types";
import { EmptyState, MonoId, PageHeader, Panel, StatusBadge, btnGhostClass, inputClass } from "@/components/ui";

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [versions, setVersions] = useState<Record<string, DatasetVersion[]>>({});
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
    const vs: Record<string, DatasetVersion[]> = {};
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
    <>
      <p className="mb-2 text-xs text-zinc-500">
        <Link href="/app/projects" className="hover:text-wine-600">
          Projects
        </Link>{" "}
        / {project?.slug}
      </p>
      <PageHeader
        title={project?.name || "…"}
        description={`${project?.default_backend || ""} · ${project?.default_base_model || ""}`}
      />
      {msg && <p className="mb-4 font-mono text-xs text-wine-500">{msg}</p>}

      <section className="mb-10">
        <h2 className="mb-3 font-display text-xl text-wine-600">Datasets</h2>
        <form onSubmit={onCreateDataset} className="mb-4 flex gap-2">
          <input name="name" placeholder="support-v1" required className={inputClass} />
          <button className={btnGhostClass}>New dataset</button>
        </form>
        <div className="space-y-4">
          {datasets.map((d) => (
            <div key={d.id} className="fh-card p-5">
              <div className="mb-3 flex items-center justify-between">
                <p className="font-medium text-wine-700">{d.name}</p>
                <label className="cursor-pointer text-xs font-semibold text-wine-500 hover:underline">
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
                    <th className="py-1 text-left font-normal">version</th>
                    <th className="text-left font-normal">status</th>
                    <th className="text-left font-normal">rows</th>
                    <th className="text-left font-normal">digest</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {(versions[d.id] || []).map((v) => (
                    <tr key={v.id} className="border-t border-mist-200">
                      <td className="py-2.5">
                        <MonoId id={v.id} />
                      </td>
                      <td>
                        <StatusBadge status={v.status} />
                      </td>
                      <td>{v.row_count}</td>
                      <td className="font-mono">{(v.content_digest || "").slice(0, 12)}</td>
                      <td className="text-right">
                        {v.status === "ready" && (
                          <button className="font-semibold text-wine-500 hover:underline" onClick={() => train(v.id)}>
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
        <h2 className="mb-3 font-display text-xl text-wine-600">Runs</h2>
        <Panel>
          {runs.length === 0 && <EmptyState>No runs yet.</EmptyState>}
          {runs.map((r) => (
            <Link key={r.id} href={`/app/runs/${r.id}`} className="flex justify-between px-4 py-3 text-sm hover:bg-mist-100/80">
              <MonoId id={r.id} />
              <span>
                {r.backend} · {r.base_model}
              </span>
              <span className="text-zinc-500">{r.provider_model_id || "—"}</span>
            </Link>
          ))}
        </Panel>
        {runs.length >= 2 && (
          <p className="mt-2 text-xs">
            <Link className="text-wine-500 hover:underline" href={`/app/compare?a=${runs[0].id}&b=${runs[1].id}`}>
              Compare latest two runs
            </Link>
          </p>
        )}
      </section>

      <section>
        <h2 className="mb-3 font-display text-xl text-wine-600">Recent jobs</h2>
        <Panel className="text-sm">
          {jobs.slice(0, 12).map((j) => (
            <Link key={j.id} href={`/app/jobs/${j.id}`} className="flex justify-between px-4 py-2.5 hover:bg-mist-100/80">
              <MonoId id={j.id} />
              <span>{j.type}</span>
              <StatusBadge status={j.status} />
            </Link>
          ))}
        </Panel>
      </section>
    </>
  );
}
