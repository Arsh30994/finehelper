"use client";

import { FormEvent, startTransition, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
      <motion.div
        className="absolute inset-0 scale-110 bg-cover bg-center"
        style={{ backgroundImage: "url(/auth-atmosphere.png)" }}
        initial={{ scale: 1.12, opacity: 0.85 }}
        animate={{ scale: 1.05, opacity: 1 }}
        transition={{ duration: 8, ease: "easeOut" }}
        aria-hidden
      />
      <div className="absolute inset-0 bg-gradient-to-br from-wine-800/55 via-wine-700/35 to-lagoon-500/25 backdrop-blur-[2px]" aria-hidden />

      <motion.div
        className="relative z-10 w-full max-w-md"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="mb-6 text-center text-white drop-shadow">
          <p className="font-display text-4xl tracking-tight">Finehelper</p>
          <p className="mt-2 text-sm text-white/80">Dataset → train → eval → deploy</p>
        </div>

        <form onSubmit={onSubmit} className="rounded-3xl border border-white/40 bg-white/95 p-8 shadow-soft backdrop-blur-md">
          <p className="text-sm font-semibold text-wine-500">Finehelper</p>
          <AnimatePresence mode="wait">
            <motion.div
              key={mode}
              initial={{ opacity: 0, x: mode === "login" ? -12 : 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: mode === "login" ? 12 : -12 }}
              transition={{ duration: 0.22 }}
            >
              <h1 className="mt-2 font-display text-3xl leading-tight text-wine-800">
                {mode === "login" ? "Welcome back to your workbench." : "Create your fine-tune space."}
              </h1>
              <p className="mt-2 text-sm text-zinc-500">
                {mode === "login"
                  ? "Sign in to continue training, evaluating, and deploying models."
                  : "Spin up an org, then version data and ship gated fine-tunes."}
              </p>
            </motion.div>
          </AnimatePresence>

          <div className="mt-7 space-y-4">
            <AnimatePresence initial={false}>
              {mode === "signup" && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="space-y-4 overflow-hidden"
                >
                  <label className="block text-xs font-semibold text-wine-700">
                    Name
                    <input name="name" required={mode === "signup"} className="fh-input mt-1.5" placeholder="Ada" />
                  </label>
                  <label className="block text-xs font-semibold text-wine-700">
                    Organization
                    <input name="org_name" required={mode === "signup"} className="fh-input mt-1.5" placeholder="Acme Labs" />
                  </label>
                </motion.div>
              )}
            </AnimatePresence>
            <label className="block text-xs font-semibold text-wine-700">
              Email address
              <input name="email" type="email" required className="fh-input mt-1.5" placeholder="you@email.com" />
            </label>
            <label className="block text-xs font-semibold text-wine-700">
              Password
              <input name="password" type="password" minLength={8} required className="fh-input mt-1.5" placeholder="••••••••" />
            </label>
          </div>

          <ErrorText>{error}</ErrorText>

          <motion.button
            type="submit"
            disabled={pending}
            className="fh-btn-primary mt-6 w-full"
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.98 }}
          >
            {pending ? "Working…" : mode === "login" ? "Sign in →" : "Create account →"}
          </motion.button>

          <p className="mt-5 text-center text-sm text-zinc-600">
            {mode === "login" ? "New to Finehelper? " : "Have an account? "}
            <button
              type="button"
              className="font-semibold text-wine-600 underline underline-offset-2"
              onClick={() => startTransition(() => setMode(mode === "login" ? "signup" : "login"))}
            >
              {mode === "login" ? "Create an account" : "Sign in"}
            </button>
          </p>
        </form>
      </motion.div>
    </div>
  );
}
