/** Shared Finehelper dashboard types (mirrors API documents). */

export type Org = {
  id: string;
  slug: string;
  name: string;
};

export type User = {
  id: string;
  email: string;
  name: string;
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

export type Project = {
  id: string;
  name: string;
  slug: string;
  task_type: string;
  default_backend: string;
  default_base_model: string;
  quality_gate?: Record<string, unknown> | null;
  created_at?: string;
};

export type Dataset = {
  id: string;
  name: string;
  description?: string | null;
  project_id: string;
};

export type DatasetVersion = {
  id: string;
  status: string;
  row_count: number;
  content_digest: string;
  stats?: { approx_tokens_p50?: number } | null;
  split_map?: Record<string, unknown> | null;
};

export type DatasetDetail = Dataset & {
  versions: DatasetVersion[];
};

export type Job = {
  id: string;
  type: string;
  status: string;
  project_id?: string | null;
  created_at?: string;
  error?: string | null;
  result?: unknown;
};

export type JobEvent = {
  id: string;
  kind: string;
  message: string;
  created_at: string;
  data?: Record<string, unknown> | null;
};

export type EvalRow = {
  id: string;
  passed: boolean;
  metrics: Record<string, number>;
};

export type Run = {
  id: string;
  backend: string;
  base_model: string;
  provider_model_id?: string | null;
  adapter_uri?: string | null;
  metrics?: Record<string, number> | null;
  hyperparams?: Record<string, unknown> | null;
  dataset_version_id?: string;
  job_id?: string;
  project_id?: string;
  created_at?: string;
  evals?: EvalRow[];
};

export type Deployment = {
  id: string;
  name: string;
  backend: string;
  run_id: string;
  project_id?: string;
  target?: Record<string, unknown>;
};

export type Credential = {
  id: string;
  provider: string;
  last4: string;
};

export type ApiKey = {
  id: string;
  name: string;
  prefix: string;
};

export type JobAccepted = {
  job_id: string;
  status: string;
};

export type UploadInit = {
  key: string;
  upload_url: string;
  method: string;
};

export type ChatCompletion = {
  id: string;
  object: string;
  model?: string;
  choices: { index: number; message: { role: string; content: string }; finish_reason: string }[];
};
