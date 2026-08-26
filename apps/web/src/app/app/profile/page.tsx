"use client";

import Link from "next/link";
import { Shield, Fingerprint, CheckCircle2 } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { useTrustDashboard } from "@/hooks/use-trust-dashboard";
import { FadeUp, Skeleton } from "@/components/motion";
import { btnAccentClass, btnGhostClass, btnPrimaryClass } from "@/components/ui";

export default function ProfilePage() {
  const { me: profile, signOut } = useAuth();
  const { data, loading } = useTrustDashboard({ autofill: true });
  const trust = data?.profile;
  const sec = profile?.user?.security;

  if (loading) return <Skeleton className="m-4 h-64" />;

  return (
    <div className="px-4 pb-8 pt-4">
      <FadeUp className="space-y-5">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-wine-500 text-2xl font-semibold text-white">
            {(profile?.user?.name || "?").slice(0, 1).toUpperCase()}
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-ink-800">{profile?.user?.name}</h1>
            <p className="text-sm text-zinc-500">{profile?.user?.email}</p>
          </div>
        </div>

        <div className="rounded-3xl border border-mist-300 bg-mist-100 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Shield className="h-4 w-4 text-wine-500" />
            <h2 className="font-semibold text-ink-800">Security</h2>
          </div>
          <ul className="space-y-2 text-sm">
            <li className="flex items-center justify-between">
              <span className="text-zinc-400">Email</span>
              <span className="flex items-center gap-1 text-xs">
                {sec?.email_verified || profile?.user?.email_verified ? (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5 text-lagoon-500" /> Verified
                  </>
                ) : (
                  "Not verified"
                )}
              </span>
            </li>
            <li className="flex items-center justify-between">
              <span className="text-zinc-400">Phone</span>
              <span className="flex items-center gap-1 text-xs">
                {sec?.phone_verified || profile?.user?.phone_verified ? (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5 text-lagoon-500" /> Verified
                  </>
                ) : (
                  "Not verified"
                )}
              </span>
            </li>
            <li className="flex items-center justify-between">
              <span className="text-zinc-400">Fingerprint</span>
              <span className="flex items-center gap-1 text-xs">
                {sec?.biometric_enabled || profile?.user?.biometric_enabled ? (
                  <>
                    <Fingerprint className="h-3.5 w-3.5 text-wine-500" /> On
                  </>
                ) : (
                  "Off"
                )}
              </span>
            </li>
          </ul>
          <Link href="/app/security" className={`${btnPrimaryClass} mt-4 w-full`}>
            Open security
          </Link>
        </div>

        <div className="rounded-3xl border border-mist-300 p-4 text-sm">
          <p className="text-xs uppercase tracking-wide text-zinc-400">Linked demo UPI</p>
          <p className="mt-1 font-medium text-ink-800">{trust?.upi_id || "Not linked"}</p>
          <p className="mt-1 text-zinc-500">
            {trust?.bank_name || "Demo Bank"}
            {trust?.bank_account_last4 ? ` ····${trust.bank_account_last4}` : ""}
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link href="/app/onboard" className={btnAccentClass}>
              Update onboarding
            </Link>
            <Link href="/app/score" className={btnAccentClass}>
              Trust Score
            </Link>
            <button type="button" className={btnGhostClass} onClick={signOut}>
              Sign out
            </button>
          </div>
        </div>
      </FadeUp>
    </div>
  );
}
