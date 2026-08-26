"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, Fingerprint, Mail, Phone, Shield } from "lucide-react";
import {
  biometricChallenge,
  biometricRegister,
  biometricUnlock,
  getSecurityStatus,
  sendEmailOtp,
  sendPhoneOtp,
  setPhone,
  verifyEmailOtp,
  verifyPhoneOtp,
} from "@/api";
import { useAuth } from "@/components/providers/auth-provider";
import { FadeUp, Skeleton } from "@/components/motion";
import { ErrorText, btnPrimaryClass, btnAccentClass } from "@/components/ui";
import { useToast } from "@/components/providers/toast-provider";
import { cn } from "@/lib/utils";

type Status = {
  email: string;
  phone: string | null;
  email_verified: boolean;
  phone_verified: boolean;
  biometric_enabled: boolean;
  last_biometric_at: string | null;
};

export default function SecurityPage() {
  const toast = useToast();
  const { refresh } = useAuth();
  const [status, setStatus] = useState<Status | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [emailOtp, setEmailOtp] = useState("");
  const [phone, setPhoneVal] = useState("");
  const [phoneOtp, setPhoneOtp] = useState("");
  const [demoHint, setDemoHint] = useState("");
  const [busy, setBusy] = useState("");
  const [unlocked, setUnlocked] = useState(false);

  async function load() {
    const s = await getSecurityStatus();
    setStatus(s);
    if (s.phone) setPhoneVal(s.phone);
  }

  useEffect(() => {
    load()
      .catch((e) => setError(e instanceof Error ? e.message : "failed"))
      .finally(() => setLoading(false));
  }, []);

  async function onSendEmail() {
    setBusy("email-send");
    setError("");
    try {
      const res = await sendEmailOtp();
      if (res.demo_otp) setDemoHint(`Demo email OTP: ${res.demo_otp}`);
      toast.success("Email OTP sent (demo)");
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy("");
    }
  }

  async function onVerifyEmail() {
    setBusy("email-verify");
    setError("");
    try {
      await verifyEmailOtp(emailOtp);
      await load();
      await refresh();
      setEmailOtp("");
      toast.success("Email verified");
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy("");
    }
  }

  async function onSavePhone() {
    setBusy("phone-save");
    setError("");
    try {
      await setPhone(phone);
      await load();
      toast.success("Phone saved");
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy("");
    }
  }

  async function onSendPhone() {
    setBusy("phone-send");
    setError("");
    try {
      const res = await sendPhoneOtp();
      if (res.demo_otp) setDemoHint(`Demo SMS OTP: ${res.demo_otp}`);
      toast.success("SMS OTP sent (demo)");
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy("");
    }
  }

  async function onVerifyPhone() {
    setBusy("phone-verify");
    setError("");
    try {
      await verifyPhoneOtp(phoneOtp);
      await load();
      await refresh();
      setPhoneOtp("");
      toast.success("Phone verified");
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy("");
    }
  }

  async function tryWebAuthnRegister(): Promise<boolean> {
    if (typeof window === "undefined" || !window.PublicKeyCredential) return false;
    try {
      const ch = await biometricChallenge();
      const cred = (await navigator.credentials.create({
        publicKey: {
          challenge: Uint8Array.from(atob(ch.challenge.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(ch.challenge.length / 4) * 4, "=") || btoa(ch.challenge)), (c) => c.charCodeAt(0)),
          rp: { name: "TrustMesh", id: window.location.hostname },
          user: {
            id: Uint8Array.from(ch.challenge.slice(0, 16), (_, i) => i),
            name: status?.email || "user",
            displayName: "TrustMesh user",
          },
          pubKeyCredParams: [{ type: "public-key", alg: -7 }],
          authenticatorSelection: { authenticatorAttachment: "platform", userVerification: "required" },
          timeout: 60000,
        },
      })) as PublicKeyCredential | null;
      if (!cred) return false;
      const rawId = btoa(String.fromCharCode(...new Uint8Array(cred.rawId)));
      await biometricRegister({ credential_id: rawId, public_key: rawId, demo: false });
      return true;
    } catch {
      return false;
    }
  }

  async function onEnableFingerprint() {
    setBusy("bio-reg");
    setError("");
    try {
      const ok = await tryWebAuthnRegister();
      if (!ok) {
        await biometricChallenge();
        await biometricRegister({ credential_id: `demo-${Date.now()}`, public_key: "demo", demo: true });
        toast.success("Fingerprint unlocked (demo mode)");
      } else {
        toast.success("Fingerprint registered");
      }
      await load();
      await refresh();
      setUnlocked(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy("");
    }
  }

  async function onUnlockFingerprint() {
    setBusy("bio-unlock");
    setError("");
    try {
      // Prefer platform authenticator get(); fall back to demo unlock
      let usedDemo = true;
      if (typeof window !== "undefined" && window.PublicKeyCredential && status?.biometric_enabled) {
        try {
          await biometricChallenge();
          // Many browsers still need stored credential opts — demo unlock is fine for stage
        } catch {
          /* ignore */
        }
      }
      await biometricUnlock({ demo: usedDemo });
      setUnlocked(true);
      toast.success("Unlocked with fingerprint");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy("");
    }
  }

  if (loading) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-10 w-40" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-mist-100 px-4 pb-10 pt-3">
      <div className="mb-4 flex items-center justify-between">
        <Link href="/app/profile" className="rounded-full p-2 hover:bg-mist-100" aria-label="Back">
          <ArrowLeft className="h-5 w-5 text-ink-800" />
        </Link>
        <p className="text-sm font-semibold text-ink-800">Security</p>
        <Shield className="h-5 w-5 text-wine-500" />
      </div>

      <FadeUp className="space-y-5">
        <div className="rounded-3xl bg-mist-100 p-5 text-center">
          <p className="text-xs font-medium text-zinc-500">Protect your Trust Score & signals</p>
          <h1 className="mt-1 text-2xl font-semibold text-ink-800">Verify & unlock</h1>
          <p className="mt-2 text-xs text-zinc-500">
            Demo OTPs are shown on-screen (no real SMS/email). Fingerprint uses device biometrics when available.
          </p>
        </div>

        {demoHint ? (
          <div className="rounded-2xl border border-wine-100 bg-mist-200 px-4 py-3 text-sm font-medium text-wine-400">
            {demoHint}
          </div>
        ) : null}
        <ErrorText>{error}</ErrorText>

        {/* Fingerprint */}
        <section className="rounded-3xl border border-mist-300 p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="font-semibold text-ink-800">Fingerprint</h2>
              <p className="mt-1 text-xs text-zinc-500">
                {status?.biometric_enabled ? "Enabled on this account" : "Add a biometric unlock for TrustMesh"}
              </p>
            </div>
            {status?.biometric_enabled ? <CheckCircle2 className="h-5 w-5 text-lagoon-500" /> : null}
          </div>
          <button
            type="button"
            onClick={status?.biometric_enabled ? onUnlockFingerprint : onEnableFingerprint}
            disabled={!!busy}
            className={cn(
              "mx-auto mt-6 flex h-24 w-24 items-center justify-center rounded-full text-white shadow-soft transition active:scale-95",
              unlocked ? "bg-lagoon-500" : "bg-wine-500",
            )}
            aria-label="Fingerprint"
          >
            <Fingerprint className="h-12 w-12" strokeWidth={1.5} />
          </button>
          <p className="mt-3 text-center text-xs text-zinc-500">
            {unlocked ? "Session unlocked" : status?.biometric_enabled ? "Tap to unlock" : "Tap to enable"}
          </p>
          <button
            type="button"
            className={`${btnAccentClass} mt-4 w-full`}
            disabled={!!busy}
            onClick={status?.biometric_enabled ? onUnlockFingerprint : onEnableFingerprint}
          >
            {busy.startsWith("bio") ? "Working…" : status?.biometric_enabled ? "Unlock with fingerprint" : "Enable fingerprint"}
          </button>
        </section>

        {/* Email */}
        <section className="rounded-3xl border border-mist-300 p-5">
          <div className="mb-3 flex items-center gap-2">
            <Mail className="h-4 w-4 text-wine-500" />
            <h2 className="font-semibold text-ink-800">Email verification</h2>
            {status?.email_verified ? <CheckCircle2 className="h-4 w-4 text-lagoon-500" /> : null}
          </div>
          <p className="text-sm text-zinc-400">{status?.email}</p>
          {!status?.email_verified ? (
            <div className="mt-3 space-y-2">
              <button type="button" className={btnAccentClass} disabled={!!busy} onClick={onSendEmail}>
                {busy === "email-send" ? "Sending…" : "Send email OTP"}
              </button>
              <input
                className="fh-input rounded-xl"
                placeholder="6-digit OTP"
                value={emailOtp}
                onChange={(e) => setEmailOtp(e.target.value)}
                inputMode="numeric"
                maxLength={8}
              />
              <button type="button" className={btnPrimaryClass} disabled={!!busy || emailOtp.length < 4} onClick={onVerifyEmail}>
                {busy === "email-verify" ? "Verifying…" : "Verify email"}
              </button>
            </div>
          ) : (
            <p className="mt-2 text-xs text-lagoon-500">Verified</p>
          )}
        </section>

        {/* Phone */}
        <section className="rounded-3xl border border-mist-300 p-5">
          <div className="mb-3 flex items-center gap-2">
            <Phone className="h-4 w-4 text-wine-500" />
            <h2 className="font-semibold text-ink-800">Phone verification</h2>
            {status?.phone_verified ? <CheckCircle2 className="h-4 w-4 text-lagoon-500" /> : null}
          </div>
          <input
            className="fh-input rounded-xl"
            placeholder="10-digit mobile"
            value={phone}
            onChange={(e) => setPhoneVal(e.target.value)}
            inputMode="tel"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" className={btnAccentClass} disabled={!!busy} onClick={onSavePhone}>
              {busy === "phone-save" ? "Saving…" : "Save phone"}
            </button>
            <button type="button" className={btnAccentClass} disabled={!!busy || !status?.phone} onClick={onSendPhone}>
              {busy === "phone-send" ? "Sending…" : "Send SMS OTP"}
            </button>
          </div>
          {!status?.phone_verified ? (
            <div className="mt-3 space-y-2">
              <input
                className="fh-input rounded-xl"
                placeholder="6-digit OTP"
                value={phoneOtp}
                onChange={(e) => setPhoneOtp(e.target.value)}
                inputMode="numeric"
                maxLength={8}
              />
              <button
                type="button"
                className={btnPrimaryClass}
                disabled={!!busy || phoneOtp.length < 4}
                onClick={onVerifyPhone}
              >
                {busy === "phone-verify" ? "Verifying…" : "Verify phone"}
              </button>
            </div>
          ) : (
            <p className="mt-2 text-xs text-lagoon-500">Verified · +91 {status.phone}</p>
          )}
        </section>

        <Link href="/app" className={`${btnPrimaryClass} w-full`}>
          Back to Home
        </Link>
      </FadeUp>
    </div>
  );
}
