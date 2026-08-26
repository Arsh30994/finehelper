"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getOrg } from "@/api";
import type { Org } from "@/types";
import { useAuth } from "@/components/providers/auth-provider";
import { FadeUp } from "@/components/motion";
import { MetricRow, PageHeader, btnGhostClass, btnPrimaryClass } from "@/components/ui";

export default function ProfilePage() {
  const { me: profile } = useAuth();
  const [org, setOrg] = useState<(Org & { role?: string; member_count?: number }) | null>(null);

  useEffect(() => {
    getOrg().then(setOrg).catch(() => setOrg(null));
  }, []);

  return (
    <>
      <PageHeader title="Profile" description="Your identity inside this Finehelper organization." />

      <FadeUp>
        <div className="fh-card overflow-hidden">
          <div className="grid gap-0 md:grid-cols-[1fr_1.1fr]">
            <div className="border-b border-mist-200 p-6 md:border-b-0 md:border-r">
              <div className="flex items-center gap-4">
                <div className="flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-wine-400 to-wine-700 font-display text-3xl text-white shadow-soft">
                  {(profile?.user?.name || "?").slice(0, 1).toUpperCase()}
                </div>
                <div>
                  <span className="inline-flex rounded-full bg-wine-500 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                    Verified session
                  </span>
                  <h2 className="mt-2 font-display text-3xl text-wine-700">{profile?.user?.name || "—"}</h2>
                  <p className="text-sm text-zinc-500">{profile?.user?.email}</p>
                </div>
              </div>
              <dl className="mt-8 grid grid-cols-2 gap-4 text-sm">
                <div>
                  <dt className="text-[11px] uppercase tracking-wide text-zinc-400">User id</dt>
                  <dd className="mt-1 font-mono text-xs text-wine-600">{profile?.user?.id?.slice(0, 12) || "—"}</dd>
                </div>
                <div>
                  <dt className="text-[11px] uppercase tracking-wide text-zinc-400">Role</dt>
                  <dd className="mt-1 capitalize text-wine-600">{profile?.role || "—"}</dd>
                </div>
                <div>
                  <dt className="text-[11px] uppercase tracking-wide text-zinc-400">Auth via</dt>
                  <dd className="mt-1 text-wine-600">{profile?.via || "—"}</dd>
                </div>
                <div>
                  <dt className="text-[11px] uppercase tracking-wide text-zinc-400">Members</dt>
                  <dd className="mt-1 text-wine-600">{org?.member_count ?? "—"}</dd>
                </div>
              </dl>
            </div>

            <div className="p-6">
              <h3 className="font-display text-2xl text-wine-600">Organization</h3>
              <p className="mt-1 text-sm text-zinc-500">Workspace credentials for training and deploy.</p>
              <div className="mt-4">
                <MetricRow
                  label="Org name"
                  hint="Display name"
                  value={<span className="font-display text-xl">{org?.name || profile?.org?.name || "—"}</span>}
                />
                <MetricRow
                  label="Slug"
                  hint="URL-safe identifier"
                  value={<span className="font-mono text-lg">{org?.slug || profile?.org?.slug || "—"}</span>}
                />
                <MetricRow
                  label="Your role"
                  hint="Permissions in this org"
                  value={<span className="capitalize">{org?.role || profile?.role || "—"}</span>}
                />
              </div>
              <div className="mt-6 flex flex-wrap gap-2">
                <Link href="/app/settings" className={btnPrimaryClass}>
                  Open settings
                </Link>
                <Link href="/app" className={btnGhostClass}>
                  Back to dashboard
                </Link>
              </div>
            </div>
          </div>
        </div>
      </FadeUp>
    </>
  );
}
