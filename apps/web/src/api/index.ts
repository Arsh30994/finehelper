/**
 * TrustMesh API client — auth + trust scoring only.
 */
import { api, clearSession, getToken, setSession } from "@/lib/api";
import type {
  AuthToken,
  Me,
  Org,
  TrustAttestVerify,
  TrustDashboard,
  TrustExplainResult,
  TrustIngestResult,
  TrustProfile,
  TrustScore,
} from "@/types";

export { api, clearSession, getToken, setSession };
export type * from "@/types";

export const endpoints = {
  signup: "/v1/auth/signup",
  login: "/v1/auth/login",
  me: "/v1/auth/me",
  org: "/v1/orgs",
  security: "/v1/auth/security",
  verifyEmailSend: "/v1/auth/verify/email/send",
  verifyEmail: "/v1/auth/verify/email",
  setPhone: "/v1/auth/verify/phone",
  verifyPhoneSend: "/v1/auth/verify/phone/send",
  verifyPhoneConfirm: "/v1/auth/verify/phone/confirm",
  biometricChallenge: "/v1/auth/biometric/challenge",
  biometricRegister: "/v1/auth/biometric/register",
  biometricUnlock: "/v1/auth/biometric/unlock",
  trustConsent: "/v1/trust/consent",
  trustOnboard: "/v1/trust/onboard",
  trustProfile: "/v1/trust/profile",
  trustIngest: "/v1/trust/ingest/synthetic",
  trustScore: "/v1/trust/score",
  trustScoreMe: "/v1/trust/score/me",
  trustExplain: "/v1/trust/explain",
  trustDashboard: "/v1/trust/dashboard",
  trustScan: "/v1/trust/scan",
  trustBootstrap: "/v1/trust/bootstrap",
  trustAttest: "/v1/trust/attest",
  trustAttestVerify: "/v1/trust/attest/verify",
  trustAttestStatus: "/v1/trust/attest/status",
  agentChat: "/v1/agent/chat",
  agentHealth: "/v1/agent/health",
  agentVoiceStt: "/v1/agent/voice/stt",
  agentVoiceTts: "/v1/agent/voice/tts",
} as const;

export async function signup(body: {
  email: string;
  password: string;
  name: string;
  org_name: string;
}): Promise<AuthToken> {
  return api(endpoints.signup, { method: "POST", body: JSON.stringify(body) });
}

export async function login(body: { email: string; password: string }): Promise<AuthToken> {
  return api(endpoints.login, { method: "POST", body: JSON.stringify(body) });
}

export async function me(): Promise<Me> {
  return api(endpoints.me);
}

export async function getSecurityStatus(): Promise<{
  email: string;
  phone: string | null;
  email_verified: boolean;
  phone_verified: boolean;
  biometric_enabled: boolean;
  last_biometric_at: string | null;
  demo: boolean;
}> {
  return api(endpoints.security);
}

export async function sendEmailOtp(): Promise<{ ok: boolean; demo_otp?: string; message: string }> {
  return api(endpoints.verifyEmailSend, { method: "POST", body: "{}" });
}

export async function verifyEmailOtp(code: string): Promise<{ ok: boolean; email_verified: boolean }> {
  return api(endpoints.verifyEmail, { method: "POST", body: JSON.stringify({ code }) });
}

export async function setPhone(phone: string): Promise<{ ok: boolean; phone: string }> {
  return api(endpoints.setPhone, { method: "POST", body: JSON.stringify({ phone }) });
}

export async function sendPhoneOtp(): Promise<{ ok: boolean; demo_otp?: string; message: string }> {
  return api(endpoints.verifyPhoneSend, { method: "POST", body: "{}" });
}

export async function verifyPhoneOtp(code: string): Promise<{ ok: boolean; phone_verified: boolean }> {
  return api(endpoints.verifyPhoneConfirm, { method: "POST", body: JSON.stringify({ code }) });
}

export async function biometricChallenge(): Promise<{
  challenge: string;
  biometric_enabled: boolean;
  has_credential: boolean;
}> {
  return api(endpoints.biometricChallenge);
}

export async function biometricRegister(body: {
  credential_id: string;
  public_key: string;
  demo?: boolean;
}): Promise<{ ok: boolean; biometric_enabled: boolean; mode: string }> {
  return api(endpoints.biometricRegister, { method: "POST", body: JSON.stringify(body) });
}

export async function biometricUnlock(body?: {
  credential_id?: string;
  demo?: boolean;
}): Promise<{ ok: boolean; unlocked: boolean; mode: string }> {
  return api(endpoints.biometricUnlock, { method: "POST", body: JSON.stringify(body || { demo: true }) });
}

export async function getOrg(): Promise<Org & { role: string; member_count: number }> {
  return api(endpoints.org);
}

export async function trustConsent(scopes?: string[]): Promise<TrustProfile> {
  return api(endpoints.trustConsent, {
    method: "POST",
    body: JSON.stringify({ scopes: scopes ?? ["upi_6m", "bills", "recharges", "peers"] }),
  });
}

export async function trustOnboard(body: {
  upi_id: string;
  bank_name?: string;
  bank_account_last4?: string;
  occupation?: string;
}): Promise<TrustProfile> {
  return api(endpoints.trustOnboard, { method: "POST", body: JSON.stringify(body) });
}

export async function trustProfile(): Promise<TrustProfile> {
  return api(endpoints.trustProfile);
}

export async function trustIngestSynthetic(body?: {
  months?: number;
  seed?: number;
  occupation?: string;
  quality?: string;
}): Promise<TrustIngestResult> {
  return api(endpoints.trustIngest, { method: "POST", body: JSON.stringify(body || {}) });
}

export async function trustScore(): Promise<TrustScore> {
  return api(endpoints.trustScore, { method: "POST", body: "{}" });
}

export async function trustScoreMe(): Promise<
  TrustScore & { profile?: TrustProfile | null; signals_summary?: TrustDashboard["signals_summary"] }
> {
  return api(endpoints.trustScoreMe);
}

export async function trustExplain(lang: "en" | "hi" = "en"): Promise<TrustExplainResult> {
  return api(endpoints.trustExplain, { method: "POST", body: JSON.stringify({ lang }) });
}

export async function trustDashboard(): Promise<TrustDashboard> {
  return api(endpoints.trustDashboard);
}

export async function trustBootstrap(body?: {
  months?: number;
  seed?: number;
  occupation?: string;
  quality?: string;
  force?: boolean;
  lang?: string;
}): Promise<TrustDashboard & { bootstrapped?: boolean; message?: string }> {
  return api(endpoints.trustBootstrap, {
    method: "POST",
    body: JSON.stringify(body || { occupation: "kirana", quality: "good" }),
  });
}

export async function trustAttest(): Promise<{
  ok: boolean;
  score: TrustScore;
  attestation: {
    network?: string | null;
    tx_hash?: string | null;
    block_number?: number | null;
    explorer_url?: string | null;
    score_hash?: string | null;
    signals_root?: string | null;
    mode?: string | null;
  };
  demo?: boolean;
}> {
  return api(endpoints.trustAttest, { method: "POST", body: "{}" });
}

export async function trustAttestVerify(): Promise<TrustAttestVerify> {
  return api(endpoints.trustAttestVerify);
}

export type TrustScanResult = {
  ok: boolean;
  demo: boolean;
  settlement: boolean;
  message: string;
  parsed: {
    kind: string;
    upi?: string | null;
    name?: string;
    amount?: number | null;
    category?: string;
  };
  transaction: {
    at: string;
    amount: number;
    direction: string;
    counterparty: string;
    upi: string;
  };
  merchant: { name: string; category: string; upi?: string | null };
};

export async function trustScan(raw: string, amount_override?: number): Promise<TrustScanResult> {
  return api(endpoints.trustScan, {
    method: "POST",
    body: JSON.stringify({ raw, amount_override }),
  });
}

export type AgentChatResult = {
  reply: string;
  intent: string;
  tools_used: string[];
  lang: string;
  score?: number | null;
  suggestions?: string[];
  demo?: boolean;
};

export async function agentChat(body: {
  message: string;
  lang?: "en" | "hi" | "auto";
  force_refresh?: boolean;
}): Promise<AgentChatResult> {
  return api(endpoints.agentChat, {
    method: "POST",
    body: JSON.stringify({
      message: body.message,
      lang: body.lang || "auto",
      force_refresh: body.force_refresh || false,
    }),
  });
}

export type AgentSttResult = {
  transcript: string;
  language_code?: string | null;
  language_probability?: number | null;
  provider?: string;
  mode?: string;
};

export type AgentTtsResult = {
  audio_base64: string;
  mime_type: string;
  language_code: string;
  speaker?: string;
  provider?: string;
};

export async function agentVoiceStt(blob: Blob, filename = "voice.webm"): Promise<AgentSttResult> {
  const fd = new FormData();
  fd.append("file", blob, filename);
  return api(endpoints.agentVoiceStt, { method: "POST", body: fd });
}

export async function agentVoiceTts(body: {
  text: string;
  language_code?: string | null;
  speaker?: string | null;
}): Promise<AgentTtsResult> {
  return api(endpoints.agentVoiceTts, {
    method: "POST",
    body: JSON.stringify({
      text: body.text,
      language_code: body.language_code || null,
      speaker: body.speaker || null,
    }),
  });
}

/** Stage demo: consent → onboard → ingest → score → explain */
export async function runTrustDemoFlow(opts?: {
  upi_id?: string;
  occupation?: string;
  quality?: string;
  lang?: "en" | "hi";
}): Promise<{ score: TrustScore; explanation: string; dashboard: TrustDashboard }> {
  await trustConsent();
  await trustOnboard({
    upi_id: opts?.upi_id || "demo.kirana@oksbi",
    bank_name: "Demo Bank",
    bank_account_last4: "4242",
    occupation: opts?.occupation || "kirana",
  });
  await trustIngestSynthetic({
    months: 6,
    seed: 30994,
    occupation: opts?.occupation || "kirana",
    quality: opts?.quality || "good",
  });
  const score = await trustScore();
  const explained = await trustExplain(opts?.lang || "en");
  const dashboard = await trustDashboard();
  return { score, explanation: explained.explanation, dashboard };
}
