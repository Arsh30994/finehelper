"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listDeployments } from "@/api";
import type { Deployment } from "@/types";
import { EmptyState, ErrorText, MonoId, PageHeader, Panel, StatusBadge, btnAccentClass } from "@/components/ui";

export default function DeploymentsPage() {
  const [deps, setDeps] = useState<Deployment[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    listDeployments()
      .then(setDeps)
      .catch((e) => setError(String(e.message || e)));
  }, []);

  return (
    <>
      <PageHeader
        title="Deployments"
        description="Promoted runs behind the OpenAI-compatible chat gateway."
        actions={
          <Link href="/app/playground" className={btnAccentClass}>
            Open playground
          </Link>
        }
      />
      <ErrorText>{error}</ErrorText>
      <Panel>
        {deps.length === 0 && !error ? (
          <EmptyState>No deployments yet. Promote a run from its detail page after eval passes.</EmptyState>
        ) : null}
        {deps.map((d) => (
          <div key={d.id} className="flex items-center justify-between px-5 py-4 text-sm">
            <div>
              <p className="font-display text-lg text-wine-700">{d.name}</p>
              <p className="mt-0.5 text-xs text-zinc-500">
                <MonoId id={d.id} /> · {d.backend}
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <StatusBadge status="live" />
              <Link className="text-wine-500 hover:underline" href={`/app/runs/${d.run_id}`}>
                run <MonoId id={d.run_id} />
              </Link>
            </div>
          </div>
        ))}
      </Panel>
    </>
  );
}
