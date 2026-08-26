/** TrustMesh frontend types (mirrors API). */

export type Org = {
  id: string;
  slug: string;
  name: string;
};

export type User = {
  id: string;
  email: string;
  name: string;
  phone?: string | null;
  email_verified?: boolean;
  phone_verified?: boolean;
  biometric_enabled?: boolean;
  security?: {
    email_verified: boolean;
    phone_verified: boolean;
    biometric_enabled: boolean;
    phone?: string | null;
  };
};

export type AuthToken = {
  token: string;
  token_type?: string;
  user: User;
  org: Org;
};

export type Me = {
  user: User;
  org: Org;
  role: string;
  via: string;
};

export type TrustProfile = {
  id?: string;
  user_id?: string;
  upi_id?: string | null;
  bank_name?: string | null;
  bank_account_last4?: string | null;
  consent_at?: string | null;
  consent_scopes?: string[];
  occupation?: string | null;
};

export type TrustScore = {
  id: string;
  score: number;
  factors: Record<string, number>;
  eligibility_min: number;
  eligibility_max: number;
  explanation?: string | null;
  explanation_lang?: string;
  model_version?: string;
  created_at?: string;
  score_hash?: string | null;
  signals_root?: string | null;
  chain_network?: string | null;
  chain_tx_hash?: string | null;
  chain_block?: number | null;
  chain_explorer_url?: string | null;
  chain_mode?: string | null;
};

export type TrustAttestVerify = {
  ok: boolean;
  hash_match: boolean;
  score_hash?: string;
  chain_tx_hash?: string | null;
  network?: string;
  explorer_url?: string | null;
  found_in_ledger?: boolean;
  note?: string;
  demo?: boolean;
};

export type TrustSignalsSummary = {
  txn_count: number;
  bill_count: number;
  recharge_count: number;
  peers: { name: string; upi: string; direction?: string; months_known?: number; txn_count?: number }[];
  merchants: { name: string; count?: number; txn_count?: number; spend_total?: number; category?: string }[];
  recent_txns: { at: string; amount: number; direction: string; counterparty?: string; note?: string }[];
  bills: { name?: string; provider?: string; kind?: string; amount: number; on_time: boolean; at?: string }[];
  recharges: { amount: number; at: string; operator?: string }[];
};

export type TrustDashboard = {
  profile: TrustProfile | null;
  score: TrustScore | null;
  signals_summary: TrustSignalsSummary | null;
  demo?: boolean;
};

export type TrustIngestResult = {
  id: string;
  months: number;
  txn_count: number;
  bill_count: number;
  recharge_count: number;
  peer_count: number;
  merchants: { name: string }[];
  synthetic: boolean;
};

export type TrustExplainResult = {
  explanation: string;
  lang: string;
  score_id?: string;
};
