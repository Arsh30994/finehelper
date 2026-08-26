"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getJob, getJobEvents } from "@/api";
import type { Job, JobEvent } from "@/types";
import { PageHeader, StatusBadge } from "@/components/ui";

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);

  useEffect(() => {
    let stop = false;
    async function poll() {
      while (!stop) {
        try {
          const [j, ev] = await Promise.all([getJob(id), getJobEvents(id)]);
          setJob(j);
          setEvents(ev);
          if (["succeeded", "failed", "cancelled"].includes(j.status)) break;
        } catch {
          break;
        }
        await new Promise((r) => setTimeout(r, 1000));
      }
    }
    poll();
    return () => {
      stop = true;
    };
  }, [id]);

  return (
    <>
      <p className="mb-2 text-xs text-zinc-500">
        <Link href="/app/jobs" className="hover:text-wine-600">
          Jobs
        </Link>
      </p>
      <PageHeader
        title={<span className="font-mono">{id.slice(0, 8)}</span>}
        description={
          job ? (
            <span className="inline-flex items-center gap-2">
              <span className="capitalize">{job.type}</span>
              <StatusBadge status={job.status} />
            </span>
          ) : null
        }
      />
      {job?.error && <pre className="mb-4 whitespace-pre-wrap rounded-2xl bg-red-50 p-4 text-xs text-red-700">{job.error}</pre>}
      {job?.result != null && (
        <pre className="mb-6 overflow-auto rounded-2xl border border-mist-300 bg-white p-4 text-xs shadow-lift">
          {JSON.stringify(job.result, null, 2)}
        </pre>
      )}
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-zinc-500">Event log</h2>
      <ul className="max-h-[480px] space-y-1 overflow-auto rounded-2xl border border-mist-300 bg-white p-4 font-mono text-xs shadow-lift">
        {events.map((e) => (
          <li key={e.id}>
            <span className="text-lagoon-500">{e.kind}</span> {e.message}
          </li>
        ))}
      </ul>
    </>
  );
}
