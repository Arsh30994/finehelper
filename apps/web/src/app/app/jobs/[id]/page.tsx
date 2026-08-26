"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import AppShell from "../../app-shell";
import { getJob, getJobEvents } from "@/api";
import Link from "next/link";

type Job = { id: string; type: string; status: string; result?: unknown; error?: string | null };
type Event = { id: string; kind: string; message: string; created_at: string };

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [events, setEvents] = useState<Event[]>([]);

  useEffect(() => {
    let stop = false;
    async function poll() {
      while (!stop) {
        try {
          const [j, ev] = await Promise.all([
            getJob(id),
            getJobEvents(id),
          ]);
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
    <AppShell>
      <p className="text-xs text-zinc-500 mb-2">
        <Link href="/app/jobs">Jobs</Link>
      </p>
      <h1 className="text-2xl font-medium font-mono">{id.slice(0, 8)}</h1>
      <p className="text-sm text-zinc-500 mt-1 mb-6">
        {job?.type} · {job?.status}
      </p>
      {job?.error && <pre className="text-xs text-red-400 whitespace-pre-wrap mb-4">{job.error}</pre>}
      {job?.result != null && (
        <pre className="text-xs bg-ink-900 border border-ink-700 rounded p-4 overflow-auto mb-6">
          {JSON.stringify(job.result, null, 2)}
        </pre>
      )}
      <h2 className="text-sm uppercase tracking-wide text-zinc-500 mb-2">Event log</h2>
      <ul className="text-xs font-mono space-y-1 bg-ink-900 border border-ink-700 rounded p-4 max-h-[480px] overflow-auto">
        {events.map((e) => (
          <li key={e.id}>
            <span className="text-zinc-500">{e.kind}</span> {e.message}
          </li>
        ))}
      </ul>
    </AppShell>
  );
}
