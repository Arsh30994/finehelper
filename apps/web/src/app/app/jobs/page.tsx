"use client";

import Link from "next/link";
import { Suspense, startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { listJobs } from "@/api";
import type { Job } from "@/types";
import { FadeUp, Skeleton } from "@/components/motion";
import { EmptyState, MonoId, PageHeader, Panel, StatusBadge, inputClass } from "@/components/ui";

function JobsInner() {
  const params = useSearchParams();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState(params.get("q") || "");
  const [statusFilter, setStatusFilter] = useState("all");
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    listJobs()
      .then(setJobs)
      .catch(() => setJobs([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = deferredQuery.trim().toLowerCase();
    return jobs.filter((j) => {
      if (statusFilter !== "all" && j.status !== statusFilter) return false;
      if (!q) return true;
      return j.id.toLowerCase().includes(q) || j.type.toLowerCase().includes(q) || (j.error || "").toLowerCase().includes(q);
    });
  }, [jobs, deferredQuery, statusFilter]);

  return (
    <>
      <PageHeader title="Jobs" description="Ingest, train, eval, and deploy work across your org." />
      <FadeUp className="mb-5 flex flex-wrap gap-2">
        <input
          value={query}
          onChange={(e) => startTransition(() => setQuery(e.target.value))}
          placeholder="Filter by id, type, error…"
          className={`${inputClass} max-w-sm`}
        />
        <select
          value={statusFilter}
          onChange={(e) => startTransition(() => setStatusFilter(e.target.value))}
          className={`${inputClass} w-auto`}
        >
          <option value="all">All statuses</option>
          <option value="queued">queued</option>
          <option value="running">running</option>
          <option value="succeeded">succeeded</option>
          <option value="failed">failed</option>
          <option value="cancelled">cancelled</option>
        </select>
      </FadeUp>

      {loading ? (
        <div className="space-y-2">
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
          <Skeleton className="h-12" />
        </div>
      ) : (
        <Panel className="text-sm">
          {filtered.length === 0 ? <EmptyState>No jobs match this filter.</EmptyState> : null}
          <AnimatePresence initial={false}>
            {filtered.map((j) => (
              <motion.div
                key={j.id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
              >
                <Link
                  href={`/app/jobs/${j.id}`}
                  className="grid grid-cols-2 gap-2 px-5 py-3.5 transition hover:bg-mist-100/80 sm:grid-cols-4"
                >
                  <MonoId id={j.id} />
                  <span className="capitalize text-wine-700">{j.type}</span>
                  <StatusBadge status={j.status} />
                  <span className="truncate text-zinc-500">{j.error || j.created_at}</span>
                </Link>
              </motion.div>
            ))}
          </AnimatePresence>
        </Panel>
      )}
    </>
  );
}

export default function JobsPage() {
  return (
    <Suspense fallback={<Skeleton className="h-40" />}>
      <JobsInner />
    </Suspense>
  );
}
