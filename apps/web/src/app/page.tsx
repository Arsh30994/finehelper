"use client";

import { FormEvent, startTransition, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Eye, EyeOff, Lock, Mail, User } from "lucide-react";
import { login, setSession, signup } from "@/api";
import { useAuth } from "@/components/providers/auth-provider";
import { useToast } from "@/components/providers/toast-provider";
import { ErrorText } from "@/components/ui";

export default function HomePage() {
  const router = useRouter();
  const { status, refresh } = useAuth();
  const toast = useToast();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [showPass, setShowPass] = useState(false);

  useEffect(() => {
    if (status === "authenticated") router.replace("/app");
  }, [status, router]);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setPending(true);
    const fd = new FormData(e.currentTarget);
    try {
      const data =
        mode === "login"
          ? await login({ email: String(fd.get("email")), password: String(fd.get("password")) })
          : await signup({
              email: String(fd.get("email")),
              password: String(fd.get("password")),
              name: String(fd.get("name")),
              org_name: String(fd.get("org_name")),
            });
      setSession(data.token, data.org);
      await refresh();
      toast.success(mode === "login" ? "Welcome back" : "Workspace created");
      startTransition(() => router.push("/app"));
    } catch (err) {
      const message = err instanceof Error ? err.message : "failed";
      setError(message);
      toast.error("Could not sign in — check your details");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-12">
      <div className="pointer-events-none absolute inset-0 fh-horizon" aria-hidden />
      {/* Soft gold spotlight — static, not neon pulse */}
      <div
        className="pointer-events-none absolute -right-20 -top-24 h-[28rem] w-[28rem] rounded-full bg-wine-500/[0.09] blur-[100px]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.5) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
        }}
        aria-hidden
      />

      <motion.div
        className="relative z-10 w-full max-w-[420px]"
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="mb-8 text-center">
          <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-wine-500/25 bg-gradient-to-br from-[#2a2418] to-[#14110c] shadow-soft">
            <span className="font-display text-lg font-semibold text-wine-400">T</span>
          </div>
          <p className="font-display text-2xl font-semibold tracking-tight text-white">TrustMesh</p>
          <p className="mt-1.5 text-sm text-zinc-500">Thin-file trust for credit-invisible India</p>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-[1.75rem] border border-white/[0.07] bg-gradient-to-b from-[#161616] to-[#101010] p-8 shadow-soft"
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={mode}
              initial={{ opacity: 0, x: mode === "login" ? -10 : 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: mode === "login" ? 10 : -10 }}
              transition={{ duration: 0.2 }}
            >
              <h1 className="font-display text-[1.75rem] font-semibold leading-tight tracking-tight text-white">
                {mode === "login" ? (
                  <>
                    Welcome <span className="text-wine-500">Back</span>
                  </>
                ) : (
                  <>
                    Create your <span className="text-wine-500">space</span>
                  </>
                )}
              </h1>
              <p className="mt-2 text-sm leading-relaxed text-zinc-500">
                {mode === "login"
                  ? "Sign in to your Trust Score, signals, and voice agent."
                  : "Consent, link demo UPI, and score thin-file digital trails."}
              </p>
            </motion.div>
          </AnimatePresence>

          <div className="mt-7 space-y-3.5">
            <AnimatePresence initial={false}>
              {mode === "signup" && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="space-y-3.5 overflow-hidden"
                >
                  <label className="block text-[11px] font-medium uppercase tracking-wide text-zinc-500">
                    Name
                    <div className="relative mt-1.5">
                      <User className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />
                      <input
                        name="name"
                        required={mode === "signup"}
                        className="fh-input pl-10"
                        placeholder="Your name"
                      />
                    </div>
                  </label>
                  <label className="block text-[11px] font-medium uppercase tracking-wide text-zinc-500">
                    Organization
                    <input
                      name="org_name"
                      required={mode === "signup"}
                      className="fh-input mt-1.5"
                      placeholder="Acme Labs"
                    />
                  </label>
                </motion.div>
              )}
            </AnimatePresence>

            <label className="block text-[11px] font-medium uppercase tracking-wide text-zinc-500">
              Email
              <div className="relative mt-1.5">
                <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />
                <input
                  name="email"
                  type="email"
                  required
                  className="fh-input pl-10"
                  placeholder="you@email.com"
                />
              </div>
            </label>

            <label className="block text-[11px] font-medium uppercase tracking-wide text-zinc-500">
              Password
              <div className="relative mt-1.5">
                <Lock className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />
                <input
                  name="password"
                  type={showPass ? "text" : "password"}
                  minLength={10}
                  required
                  className="fh-input pl-10 pr-11"
                  placeholder="10+ chars, mixed"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
                  onClick={() => setShowPass((v) => !v)}
                  aria-label={showPass ? "Hide password" : "Show password"}
                >
                  {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </label>
          </div>

          <ErrorText>{error}</ErrorText>

          <motion.button
            type="submit"
            disabled={pending}
            className="fh-btn-primary mt-6 w-full justify-between px-5 py-3"
            whileHover={{ scale: 1.005 }}
            whileTap={{ scale: 0.985 }}
          >
            <span>{pending ? "Working…" : mode === "login" ? "Sign In" : "Create account"}</span>
            <ArrowRight className="h-4 w-4 opacity-90" />
          </motion.button>

          <p className="mt-6 text-center text-sm text-zinc-500">
            {mode === "login" ? "Don't have an account? " : "Have an account? "}
            <button
              type="button"
              className="font-semibold text-wine-500 hover:text-wine-400"
              onClick={() => startTransition(() => setMode(mode === "login" ? "signup" : "login"))}
            >
              {mode === "login" ? "Sign Up" : "Sign In"}
            </button>
          </p>
          {mode === "login" ? (
            <p className="mt-3 text-center text-[11px] text-zinc-600">demo@trustmesh.app · Demo!Trust94</p>
          ) : null}
        </form>
      </motion.div>
    </div>
  );
}
