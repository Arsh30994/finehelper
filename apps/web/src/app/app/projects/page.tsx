"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { createProject, listProjects } from "@/api";
import type { Project } from "@/types";
import { useToast } from "@/components/providers/toast-provider";
import { FadeUp, Stagger, StaggerItem } from "@/components/motion";
import { EmptyState, ErrorText, PageHeader, Panel, btnPrimaryClass, inputClass } from "@/components/ui";

export default function ProjectsPage() {
  const toast = useToast();
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function refresh() {
    setProjects(await listProjects());
  }

  useEffect(() => {
    refresh().catch((e) => setError(String(e.message || e)));
  }, []);

  async function onCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPending(true);
    const fd = new FormData(e.currentTarget);
    try {
      await createProject({
        name: fd.get("name"),
        default_backend: fd.get("backend") || "dry_run",
        default_base_model: fd.get("base") || "gpt-4.1-mini",
      });
      (e.target as HTMLFormElement).reset();
      await refresh();
      toast.success("Project created");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not create project");
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <PageHeader title="Projects" description="A project is a task, a default backend, and a quality gate." />
      <ErrorText>{error}</ErrorText>
      <FadeUp>
        <form onSubmit={onCreate} className="fh-card mb-8 flex flex-wrap gap-2 p-4">
          <input name="name" placeholder="support-bot" required className={`${inputClass} w-48`} />
          <select name="backend" className={`${inputClass} w-auto`}>
            <option value="dry_run">dry_run</option>
            <option value="openai">openai</option>
            <option value="lora_modal">lora_modal</option>
            <option value="lora_local">lora_local</option>
          </select>
          <input name="base" placeholder="base model" className={`${inputClass} w-56`} />
          <button disabled={pending} className={btnPrimaryClass}>
            {pending ? "Creating…" : "Create project"}
          </button>
        </form>
      </FadeUp>
      <Panel>
        {projects.length === 0 && <EmptyState>No projects yet — create one to start ingesting data.</EmptyState>}
        <Stagger>
          {projects.map((p) => (
            <StaggerItem key={p.id}>
              <Link
                href={`/app/projects/${p.id}`}
                className="flex items-center justify-between px-5 py-4 transition hover:bg-mist-100/80"
              >
                <div>
                  <p className="font-display text-lg text-wine-700">{p.name}</p>
                  <p className="font-mono text-xs text-zinc-500">{p.slug}</p>
                </div>
                <p className="text-xs text-zinc-500">
                  {p.default_backend} · {p.default_base_model}
                </p>
              </Link>
            </StaggerItem>
          ))}
        </Stagger>
      </Panel>
    </>
  );
}
