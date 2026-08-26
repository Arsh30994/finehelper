"use client";

import { useEffect, useState } from "react";
import AppShell from "../app-shell";
import { listJobs } from "@/api";
import Link from "next/link";

type Job = { id: string; type: string; status: string; created_at: string; error?: string | null };

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  useEffect(() => {
    listJobs().then(setJobs).catch(() => setJobs([]));
  }, []);
  return (
    <AppShell>
      <h1 className="text-2xl font-medium mb-6">Jobs</h1>
      <div className="border border-ink-700 rounded divide-y divide-ink-700 text-sm">
        {jobs.map((j) => (
          <Link key={j.id} href={`/app/jobs/${j.id}`} className="grid grid-cols-4 px-4 py-2 hover:bg-ink-800">
            <span className="font-mono text-xs">{j.id.slice(0, 8)}</span>
            <span>{j.type}</span>
            <span>{j.status}</span>
            <span className="text-zinc-500 truncate">{j.error || j.created_at}</span>
          </Link>
        ))}
      </div>
    </AppShell>
  );
}
