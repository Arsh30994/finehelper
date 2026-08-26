"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { trustConsent, trustOnboard, trustScan, type TrustScanResult } from "@/api";
import { FadeUp } from "@/components/motion";
import { ErrorText, PageHeader, btnAccentClass, btnPrimaryClass } from "@/components/ui";
import { useToast } from "@/components/providers/toast-provider";

const SCANNER_ID = "trustmesh-qr-reader";

const SAMPLE_QRS = [
  {
    label: "Blinkit groceries",
    raw: "upi://pay?pa=blinkit.demo@oksbi&pn=Blinkit&am=349&cu=INR&tn=Assumed%20demo",
  },
  {
    label: "Swiggy food",
    raw: "upi://pay?pa=swiggy.demo@ybl&pn=Swiggy&am=220&cu=INR",
  },
  {
    label: "Jio recharge",
    raw: "upi://pay?pa=jio.demo@paytm&pn=Jio%20Recharge&am=299&cu=INR",
  },
  {
    label: "TrustMesh merchant",
    raw: "trustmesh://merchant?name=Ravi%20Wholesale&upi=ravi.wholesale@oksbi&category=supplier&amount=1500",
  },
];

export default function ScannerPage() {
  const toast = useToast();
  const [scanning, setScanning] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [last, setLast] = useState<TrustScanResult | null>(null);
  const [manual, setManual] = useState("");
  const scannerRef = useRef<{ stop: () => Promise<void> } | null>(null);
  const handlingRef = useRef(false);

  const stopScanner = useCallback(async () => {
    const s = scannerRef.current;
    scannerRef.current = null;
    setScanning(false);
    if (s) {
      try {
        await s.stop();
      } catch {
        /* already stopped */
      }
    }
  }, []);

  useEffect(() => {
    return () => {
      void stopScanner();
    };
  }, [stopScanner]);

  async function ensureConsent() {
    try {
      await trustConsent();
      await trustOnboard({
        upi_id: "demo.kirana@oksbi",
        bank_name: "Demo Bank",
        bank_account_last4: "4242",
        occupation: "kirana",
      });
    } catch {
      /* may already be onboarded */
    }
  }

  async function submitRaw(raw: string) {
    if (!raw.trim() || handlingRef.current) return;
    handlingRef.current = true;
    setBusy(true);
    setError("");
    try {
      await ensureConsent();
      const result = await trustScan(raw.trim());
      setLast(result);
      toast.success(`Logged ${result.merchant.name} (demo)`);
      await stopScanner();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "scan failed";
      setError(msg);
      toast.error(msg);
    } finally {
      setBusy(false);
      handlingRef.current = false;
    }
  }

  async function startCamera() {
    setError("");
    await stopScanner();
    try {
      const { Html5Qrcode } = await import("html5-qrcode");
      const scanner = new Html5Qrcode(SCANNER_ID);
      scannerRef.current = scanner;
      setScanning(true);
      await scanner.start(
        { facingMode: "environment" },
        { fps: 8, qrbox: { width: 240, height: 240 } },
        (decoded) => {
          void submitRaw(decoded);
        },
        () => undefined,
      );
    } catch (e) {
      setScanning(false);
      scannerRef.current = null;
      const msg =
        e instanceof Error
          ? e.message
          : "Camera unavailable — use a sample QR or paste a UPI string below.";
      setError(msg);
    }
  }

  async function onFile(file: File | null) {
    if (!file) return;
    setError("");
    await stopScanner();
    try {
      const { Html5Qrcode } = await import("html5-qrcode");
      const scanner = new Html5Qrcode(SCANNER_ID);
      const decoded = await scanner.scanFile(file, true);
      await submitRaw(decoded);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read QR from image");
    }
  }

  return (
    <>
      <PageHeader
        title="Scan QR"
        description="Camera or image QR → logged as an assumed spend signal for Trust Score. Demo only — no money moves."
      />

      <FadeUp className="space-y-5">
        <div className="rounded-2xl border border-amber-200/80 bg-amber-50/80 px-4 py-3 text-xs text-amber-900">
          Assumed / synthetic flow. Scanning does not initiate UPI collect or bank transfer.
        </div>

        <div className="overflow-hidden rounded-2xl border border-mist-300 bg-black/90">
          <div id={SCANNER_ID} className="min-h-[260px] w-full" />
          {!scanning ? (
            <div className="flex min-h-[260px] flex-col items-center justify-center gap-3 px-4 py-10 text-center text-white/80">
              <p className="text-sm">Point at a UPI or TrustMesh demo QR</p>
              <button type="button" className={btnPrimaryClass} onClick={startCamera} disabled={busy}>
                Open camera
              </button>
            </div>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-2">
          {scanning ? (
            <button type="button" className={btnAccentClass} onClick={() => void stopScanner()}>
              Stop camera
            </button>
          ) : null}
          <label className={`${btnAccentClass} cursor-pointer`}>
            Upload QR image
            <input
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={(e) => void onFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <Link href="/app/history" className={btnAccentClass}>
            View history
          </Link>
        </div>

        <div className="rounded-2xl border border-mist-300 bg-mist-100/90 p-5">
          <h2 className="font-display text-xl text-wine-400">Try sample QRs</h2>
          <p className="mt-1 text-xs text-zinc-500">No camera needed — tap to log an assumed merchant signal.</p>
          <ul className="mt-4 grid gap-2 sm:grid-cols-2">
            {SAMPLE_QRS.map((s) => (
              <li key={s.label}>
                <button
                  type="button"
                  disabled={busy}
                  className="w-full rounded-xl border border-mist-300 px-3 py-2.5 text-left text-sm transition hover:border-wine-300 hover:bg-mist-50"
                  onClick={() => void submitRaw(s.raw)}
                >
                  <span className="font-medium text-wine-400">{s.label}</span>
                  <span className="mt-0.5 block truncate text-[11px] text-zinc-400">{s.raw}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl border border-mist-300 bg-mist-100/90 p-5">
          <h2 className="mb-2 font-display text-lg text-wine-400">Paste UPI / QR text</h2>
          <textarea
            className="fh-input min-h-[72px]"
            placeholder="upi://pay?pa=merchant@oksbi&pn=Shop&am=100"
            value={manual}
            onChange={(e) => setManual(e.target.value)}
          />
          <button
            type="button"
            className={`${btnPrimaryClass} mt-3`}
            disabled={busy || !manual.trim()}
            onClick={() => void submitRaw(manual)}
          >
            {busy ? "Logging…" : "Log as assumed signal"}
          </button>
        </div>

        <ErrorText>{error}</ErrorText>

        {last ? (
          <div className="rounded-2xl border border-lagoon-200 bg-lagoon-50/50 p-5">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-wine-500">Last scan</p>
            <h3 className="mt-1 font-display text-2xl text-wine-400">{last.merchant.name}</h3>
            <p className="mt-1 text-sm text-zinc-400">
              ₹{last.transaction.amount.toLocaleString("en-IN")} · {last.merchant.category}
              {last.parsed.upi ? ` · ${last.parsed.upi}` : ""}
            </p>
            <p className="mt-2 text-xs text-zinc-500">{last.message}</p>
          </div>
        ) : null}
      </FadeUp>
    </>
  );
}
