"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { listDeployments, listJobs, listProjects, listRuns } from "@/api";
import type { Deployment, Job, Project, Run } from "@/types";
import { useAuth } from "@/components/providers/auth-provider";
import { AnimatedNumber, FadeUp, Skeleton, Stagger, StaggerItem } from "@/components/motion";
import { EmptyState, MetricRow, MonoId, PageHeader, Panel, StatusBadge, btnAccentClass, btnPrimaryClass } from "@/components/ui";

export default function OverviewPage() {
  const { me: profile } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [deps, setDeps] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [p, j, r, d] = await Promise.all([
          listProjects().catch(() => []),
          listJobs().catch(() => []),
          listRuns().catch(() => []),
          listDeployments().catch(() => []),
        ]);
        if (!alive) return;
        setProjects(p);
        setJobs(j);
        setRuns(r);
        setDeps(d);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const activeJobs = jobs.filter((j) => !["succeeded", "failed", "cancelled"].includes(j.status)).length;
  const stageCount = [projects.length > 0, runs.length > 0, jobs.some((j) => j.type === "eval"), deps.length > 0].filter(
    Boolean,
  ).length;
  const progress = stageCount * 25;

  if (loading) {
    return (
      <div className="space-y-5">
        <Skeleton className="h-12 w-72" />
        <div className="grid gap-5 lg:grid-cols-2">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
        <Skeleton className="h-48" />
      </div>
    );
  }

  return (
    <>
      <PageHeader
        title="Your fine-tune dashboard"
        description="Track datasets, training jobs, eval gates, and deployments in one calm workbench."
        actions={
          <div className="flex gap-2">
            <Link href="/app/projects" className={btnPrimaryClass}>
              Open projects
            </Link>
            <Link href="/app/playground" className={btnAccentClass}>
              Try playground
            </Link>
          </div>
        }
      />

      <Stagger className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <StaggerItem>
          <section className="fh-card p-6">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-wine-500">Workbench pulse</p>
            <p className="mt-2 font-display text-5xl text-wine-600">
              <AnimatedNumber value={runs.length} />
            </p>
            <p className="mt-1 text-sm text-zinc-500">Runs available to eval or chat against</p>
            <div className="mt-4 inline-flex items-center gap-2 rounded-full bg-lagoon-100 px-3 py-1 text-xs text-wine-700">
              <span className="h-1.5 w-1.5 rounded-full bg-wine-500" />
              Status: {activeJobs > 0 ? `${activeJobs} jobs in flight` : "Idle — ready for next train"}
            </div>
          </section>
        </StaggerItem>

        <StaggerItem>
          <section className="fh-card p-6">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="font-display text-2xl text-wine-600">Next step</h2>
              <span className="text-wine-400">↗</span>
            </div>
            <p className="text-sm text-zinc-500">
              {projects.length === 0
                ? "Create a project, upload chat JSONL, then start a dry_run train."
                : deps.length === 0
                  ? "Eval a run on a golden suite, then promote to a deployment."
                  : "Open the playground and chat with a promoted deployment."}
            </p>
            <div className="mt-5 h-2 overflow-hidden rounded-full bg-mist-200">
              <motion.div
                className="h-full rounded-full bg-wine-500"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
              />
            </div>
            <p className="mt-2 text-right text-xs text-zinc-500">{stageCount}/4 pipeline stages</p>
          </section>
        </StaggerItem>
      </Stagger>

      <FadeUp delay={0.12} className="mt-5 grid gap-5 lg:grid-cols-2">
        <section className="fh-card p-6">
          <div className="mb-4 flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-wine-100 font-display text-2xl text-wine-600">
              {(profile?.user?.name || profile?.org?.name || "F").slice(0, 1).toUpperCase()}
            </div>
            <div>
              <span className="inline-flex items-center gap-1 rounded-full bg-wine-500 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                ✓ Active
              </span>
              <h2 className="mt-1 font-display text-2xl text-wine-700">{profile?.user?.name || "—"}</h2>
              <p className="text-sm text-zinc-500">
                {profile?.org?.name || "Org"} · {profile?.role || "member"}
              </p>
            </div>
          </div>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-[11px] uppercase tracking-wide text-zinc-400">Org slug</dt>
              <dd className="font-mono text-wine-600">{profile?.org?.slug || "—"}</dd>
            </div>
            <div>
              <dt className="text-[11px] uppercase tracking-wide text-zinc-400">Auth</dt>
              <dd className="text-wine-600">{profile?.via || "—"}</dd>
            </div>
          </dl>
        </section>

        <section className="fh-card p-6">
          <h2 className="font-display text-2xl text-wine-600">Org credential</h2>
          <div className="mt-3">
            <MetricRow label="Projects" hint="Fine-tune workspaces" value={<AnimatedNumber value={projects.length} />} />
            <MetricRow label="Jobs" hint="Ingest · train · eval · deploy" value={<AnimatedNumber value={jobs.length} />} />
            <MetricRow label="Deployments" hint="Live chat targets" value={<AnimatedNumber value={deps.length} />} />
          </div>
          <Link href="/app/projects" className={`${btnAccentClass} mt-4 w-full`}>
            Continue to projects →
          </Link>
        </section>
      </FadeUp>

      <FadeUp delay={0.18} className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-display text-xl text-wine-600">Recent jobs</h2>
          <Link href="/app/jobs" className="text-sm text-wine-500 hover:underline">
            View all
          </Link>
        </div>
        <Panel>
          {jobs.length === 0 ? <EmptyState>No jobs yet — create a project and upload a dataset.</EmptyState> : null}
          {jobs.slice(0, 6).map((j) => (
            <Link
              key={j.id}
              href={`/app/jobs/${j.id}`}
              className="flex items-center justify-between gap-3 px-4 py-3 text-sm transition hover:bg-mist-100/80"
            >
              <div className="flex items-center gap-3">
                <MonoId id={j.id} />
                <span>{j.type}</span>
              </div>
              <StatusBadge status={j.status} />
            </Link>
          ))}
        </Panel>
      </FadeUp>
    </>
  );
}
