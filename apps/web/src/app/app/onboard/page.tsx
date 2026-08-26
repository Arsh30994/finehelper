"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { trustConsent, trustOnboard } from "@/api";
import { FadeUp } from "@/components/motion";
import { ErrorText, Field, PageHeader, btnPrimaryClass } from "@/components/ui";
import { useToast } from "@/components/providers/toast-provider";

const OCCUPATIONS = [
  { value: "kirana", label: "Kirana / shop" },
  { value: "gig", label: "Gig worker" },
  { value: "vendor", label: "Vendor" },
  { value: "farmer", label: "Farmer" },
  { value: "other", label: "Other" },
];

export default function OnboardPage() {
  const router = useRouter();
  const toast = useToast();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [consented, setConsented] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!consented) {
      setError("Please grant data-share consent to continue");
      return;
    }
    setPending(true);
    setError("");
    const fd = new FormData(e.currentTarget);
    try {
      await trustConsent(["upi_6m", "bills", "recharges", "peers"]);
      await trustOnboard({
        upi_id: String(fd.get("upi_id")),
        bank_name: String(fd.get("bank_name") || "Demo Bank"),
        bank_account_last4: String(fd.get("bank_account_last4") || "4242"),
        occupation: String(fd.get("occupation") || "kirana"),
      });
      toast.success("Demo UPI linked");
      router.push("/app");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "failed";
      setError(msg);
      toast.error(msg);
    } finally {
      setPending(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Link demo signals"
        description="Mock consent + demo UPI / bank — not real NPCI or bank connectivity."
      />
      <FadeUp>
        <form onSubmit={onSubmit} className="space-y-5 rounded-2xl border border-mist-300 bg-mist-100/90 p-6">
          <label className="flex items-start gap-3 text-sm text-zinc-400">
            <input
              type="checkbox"
              className="mt-1"
              checked={consented}
              onChange={(e) => setConsented(e.target.checked)}
            />
            <span>
              I consent to TrustMesh using synthetic 6-month UPI, bill, recharge, and peer signals for a demo Trust
              Score. This is not CIBIL and does not move real money.
            </span>
          </label>

          <Field label="Demo UPI ID">
            <input name="upi_id" required className="fh-input" placeholder="you@oksbi" defaultValue="demo.kirana@oksbi" />
          </Field>
          <Field label="Mock bank">
            <input name="bank_name" className="fh-input" defaultValue="Demo Bank" />
          </Field>
          <Field label="Account last 4">
            <input
              name="bank_account_last4"
              className="fh-input"
              defaultValue="4242"
              minLength={4}
              maxLength={4}
              pattern="[0-9]{4}"
              required
            />
          </Field>
          <Field label="Occupation">
            <select name="occupation" className="fh-input" defaultValue="kirana">
              {OCCUPATIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </Field>

          <ErrorText>{error}</ErrorText>
          <button type="submit" className={btnPrimaryClass} disabled={pending}>
            {pending ? "Saving…" : "Continue to Trust Home"}
          </button>
        </form>
      </FadeUp>
    </>
  );
}
