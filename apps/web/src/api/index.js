/**
 * Finehelper frontend API client.
 * Every control-plane endpoint used by the dashboard lives here.
 */
import { api, clearSession, getToken, setSession, uploadBytes } from "../lib/api";

export { api, clearSession, getToken, setSession, uploadBytes };

export const endpoints = {
  signup: "/v1/auth/signup",
  login: "/v1/auth/login",
  me: "/v1/auth/me",
  apiKeys: "/v1/auth/api-keys",
  org: "/v1/orgs",
  members: "/v1/orgs/members",
  invites: "/v1/invites",
  projects: "/v1/projects",
  project: (id) => `/v1/projects/${id}`,
  datasets: "/v1/datasets",
  dataset: (id) => `/v1/datasets/${id}`,
  datasetUploads: "/v1/datasets/uploads",
  datasetVersions: (datasetId) => `/v1/datasets/${datasetId}/versions`,
  datasetVersion: (datasetId, versionId) => `/v1/datasets/${datasetId}/versions/${versionId}`,
  train: "/v1/jobs/train",
  jobs: "/v1/jobs",
  job: (id) => `/v1/jobs/${id}`,
  jobCancel: (id) => `/v1/jobs/${id}/cancel`,
  jobEvents: (id) => `/v1/jobs/${id}/event-log`,
  evals: "/v1/evals",
  eval: (id) => `/v1/evals/${id}`,
  runs: "/v1/runs",
  run: (id) => `/v1/runs/${id}`,
  compareRuns: (a, b) => `/v1/runs/${a}/compare?other=${b}`,
  deployments: "/v1/deployments",
  credentials: "/v1/credentials",
  chatCompletions: "/v1/chat/completions",
};

export async function signup({ email, password, name, org_name }) {
  return api(endpoints.signup, {
    method: "POST",
    body: JSON.stringify({ email, password, name, org_name }),
  });
}

export async function login({ email, password }) {
  return api(endpoints.login, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function me() {
  return api(endpoints.me);
}

export async function listApiKeys() {
  return api(endpoints.apiKeys);
}

export async function createApiKey(name = "cli") {
  return api(`${endpoints.apiKeys}?name=${encodeURIComponent(name)}`, { method: "POST" });
}

export async function getOrg() {
  return api(endpoints.org);
}

export async function listProjects() {
  return api(endpoints.projects);
}

export async function createProject(body) {
  return api(endpoints.projects, { method: "POST", body: JSON.stringify(body) });
}

export async function getProject(id) {
  return api(endpoints.project(id));
}

export async function listDatasets(projectId) {
  const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return api(`${endpoints.datasets}${q}`);
}

export async function getDataset(id) {
  return api(endpoints.dataset(id));
}

export async function createDataset(body) {
  return api(endpoints.datasets, { method: "POST", body: JSON.stringify(body) });
}

export async function initDatasetUpload(body) {
  return api(endpoints.datasetUploads, { method: "POST", body: JSON.stringify(body) });
}

export async function completeDatasetUpload(datasetId, body) {
  return api(endpoints.datasetVersions(datasetId), { method: "POST", body: JSON.stringify(body) });
}

export async function startTrain(body) {
  return api(endpoints.train, { method: "POST", body: JSON.stringify(body) });
}

export async function listJobs(projectId) {
  const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return api(`${endpoints.jobs}${q}`);
}

export async function getJob(id) {
  return api(endpoints.job(id));
}

export async function getJobEvents(id) {
  return api(endpoints.jobEvents(id));
}

export async function startEval(body) {
  return api(endpoints.evals, { method: "POST", body: JSON.stringify(body) });
}

export async function listRuns(projectId) {
  const q = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
  return api(`${endpoints.runs}${q}`);
}

export async function getRun(id) {
  return api(endpoints.run(id));
}

export async function compareRuns(a, b) {
  return api(endpoints.compareRuns(a, b));
}

export async function listDeployments() {
  return api(endpoints.deployments);
}

export async function createDeployment(body) {
  return api(endpoints.deployments, { method: "POST", body: JSON.stringify(body) });
}

export async function listCredentials() {
  return api(endpoints.credentials);
}

export async function saveCredential(body) {
  return api(endpoints.credentials, { method: "POST", body: JSON.stringify(body) });
}

export async function chatCompletions(body) {
  return api(endpoints.chatCompletions, { method: "POST", body: JSON.stringify(body) });
}

export async function uploadDatasetFile(datasetId, file, { format = "openai-chat", contentType = "application/octet-stream" } = {}) {
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
