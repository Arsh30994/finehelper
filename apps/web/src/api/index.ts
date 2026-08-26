/**
 * Finehelper frontend API client.
 * Typed wrappers around control-plane endpoints.
 */
import { api, clearSession, getToken, setSession, uploadBytes } from "@/lib/api";
import type {
  ApiKey,
  AuthToken,
  ChatCompletion,
  Credential,
  Dataset,
  DatasetDetail,
  Deployment,
  Job,
  JobAccepted,
  JobEvent,
  Me,
  Org,
  Project,
  Run,
  UploadInit,
} from "@/types";

export { api, clearSession, getToken, setSession, uploadBytes };
export type * from "@/types";

export const endpoints = {
  signup: "/v1/auth/signup",
  login: "/v1/auth/login",
  me: "/v1/auth/me",
  apiKeys: "/v1/auth/api-keys",
  org: "/v1/orgs",
  members: "/v1/orgs/members",
  invites: "/v1/invites",
  projects: "/v1/projects",
  project: (id: string) => `/v1/projects/${id}`,
  datasets: "/v1/datasets",
  dataset: (id: string) => `/v1/datasets/${id}`,
  datasetUploads: "/v1/datasets/uploads",
  datasetVersions: (datasetId: string) => `/v1/datasets/${datasetId}/versions`,
  datasetVersion: (datasetId: string, versionId: string) => `/v1/datasets/${datasetId}/versions/${versionId}`,
  train: "/v1/jobs/train",
  jobs: "/v1/jobs",
  job: (id: string) => `/v1/jobs/${id}`,
  jobCancel: (id: string) => `/v1/jobs/${id}/cancel`,
  jobEvents: (id: string) => `/v1/jobs/${id}/event-log`,
  evals: "/v1/evals",
  eval: (id: string) => `/v1/evals/${id}`,
  runs: "/v1/runs",
  run: (id: string) => `/v1/runs/${id}`,
  compareRuns: (a: string, b: string) => `/v1/runs/${a}/compare?other=${b}`,
  deployments: "/v1/deployments",
  credentials: "/v1/credentials",
  chatCompletions: "/v1/chat/completions",
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

export async function listApiKeys(): Promise<ApiKey[]> {
  return api(endpoints.apiKeys);
}

export async function createApiKey(name = "cli"): Promise<{ id: string; key: string; prefix: string; name: string }> {
  return api(`${endpoints.apiKeys}?name=${encodeURIComponent(name)}`, { method: "POST" });
}

export async function getOrg(): Promise<Org & { role: string; member_count: number }> {
  return api(endpoints.org);
}

export async function listProjects(): Promise<Project[]> {
  return api(endpoints.projects);
}

export async function createProject(body: {
  name: string | FormDataEntryValue | null;
  slug?: string;
  default_backend?: string | FormDataEntryValue | null;
  default_base_model?: string | FormDataEntryValue | null;
  task_type?: string;
}): Promise<Project> {
  return api(endpoints.projects, { method: "POST", body: JSON.stringify(body) });
}

export async function getProject(id: string): Promise<Project> {
  return api(endpoints.project(id));
}

export async function listDatasets(projectId?: string): Promise<Dataset[]> {
  const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return api(`${endpoints.datasets}${q}`);
}

export async function getDataset(id: string): Promise<DatasetDetail> {
  return api(endpoints.dataset(id));
}

export async function createDataset(body: {
  project_id: string;
  name: string | FormDataEntryValue | null;
  description?: string;
}): Promise<Dataset> {
  return api(endpoints.datasets, { method: "POST", body: JSON.stringify(body) });
}

export async function initDatasetUpload(body: {
  dataset_id: string;
  filename: string;
  content_type?: string;
  format?: string;
}): Promise<UploadInit> {
  return api(endpoints.datasetUploads, { method: "POST", body: JSON.stringify(body) });
}

export async function completeDatasetUpload(
  datasetId: string,
  body: { dataset_id: string; key: string; filename: string; format?: string },
): Promise<JobAccepted> {
  return api(endpoints.datasetVersions(datasetId), { method: "POST", body: JSON.stringify(body) });
}

export async function startTrain(body: {
  project_id: string;
  dataset_version_id: string;
  backend?: string;
  recipe?: Record<string, unknown>;
  yaml_source?: string;
  git_sha?: string;
}): Promise<JobAccepted> {
  return api(endpoints.train, { method: "POST", body: JSON.stringify(body) });
}

export async function listJobs(projectId?: string): Promise<Job[]> {
  const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return api(`${endpoints.jobs}${q}`);
}

export async function getJob(id: string): Promise<Job> {
  return api(endpoints.job(id));
}

export async function getJobEvents(id: string): Promise<JobEvent[]> {
  return api(endpoints.jobEvents(id));
}

export async function cancelJob(id: string): Promise<Job> {
  return api(endpoints.jobCancel(id), { method: "POST" });
}

export async function startEval(body: {
  run_id: string;
  suite_inline?: unknown[];
  suite_key?: string;
  metrics?: string[];
  gate?: Record<string, unknown>;
  judge_model?: string;
}): Promise<JobAccepted> {
  return api(endpoints.evals, { method: "POST", body: JSON.stringify(body) });
}

export async function listRuns(projectId?: string): Promise<Run[]> {
  const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return api(`${endpoints.runs}${q}`);
}

export async function getRun(id: string): Promise<Run> {
  return api(endpoints.run(id));
}

export async function compareRuns(a: string, b: string): Promise<{ a: Run; b: Run }> {
  return api(endpoints.compareRuns(a, b));
}

export async function listDeployments(projectId?: string): Promise<Deployment[]> {
  const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return api(`${endpoints.deployments}${q}`);
}

export async function createDeployment(body: {
  run_id: string;
  name?: string;
  override_gate?: boolean;
  eval_report_id?: string;
}): Promise<JobAccepted> {
  return api(endpoints.deployments, { method: "POST", body: JSON.stringify(body) });
}

export async function listCredentials(): Promise<Credential[]> {
  return api(endpoints.credentials);
}

export async function saveCredential(body: {
  provider: string | FormDataEntryValue | null;
  secret: string | FormDataEntryValue | null;
}): Promise<Credential> {
  return api(endpoints.credentials, { method: "POST", body: JSON.stringify(body) });
}

export async function chatCompletions(body: {
  deployment_id?: string | FormDataEntryValue | null;
  run_id?: string | FormDataEntryValue | null;
  model?: string;
  messages: { role: string; content: string | FormDataEntryValue | null }[];
  temperature?: number;
}): Promise<ChatCompletion> {
  return api(endpoints.chatCompletions, { method: "POST", body: JSON.stringify(body) });
}

export async function uploadDatasetFile(
  datasetId: string,
  file: File,
  { format = "openai-chat", contentType = "application/octet-stream" }: { format?: string; contentType?: string } = {},
): Promise<JobAccepted> {
  const token = getToken();
  if (!token) throw new Error("not signed in");
  const init = await initDatasetUpload({
    dataset_id: datasetId,
    filename: file.name,
    content_type: contentType,
    format,
  });
  await uploadBytes(init.upload_url, file, token);
  return completeDatasetUpload(datasetId, {
    dataset_id: datasetId,
    key: init.key,
    filename: file.name,
    format,
  });
}
