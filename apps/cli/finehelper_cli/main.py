from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import typer
import yaml
from rich import print as rprint
from rich.table import Table

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Finehelper CLI")
auth_app = typer.Typer(help="Authentication")
dataset_app = typer.Typer(help="Datasets")
project_app = typer.Typer(help="Projects")
app.add_typer(auth_app, name="auth")
app.add_typer(dataset_app, name="dataset")
app.add_typer(project_app, name="project")

CONFIG_DIR = Path.home() / ".finehelper"
CONFIG_PATH = CONFIG_DIR / "config.json"


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {"api_url": "http://localhost:8000", "token": None, "project_id": None}


def save_config(cfg: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def client() -> httpx.Client:
    cfg = load_config()
    if not cfg.get("token"):
        raise typer.BadParameter("not logged in — run `fh auth login`")
    return httpx.Client(
        base_url=cfg["api_url"].rstrip("/"),
        headers={"Authorization": f"Bearer {cfg['token']}"},
        timeout=120.0,
    )


@auth_app.command("login")
def auth_login(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True),
    api_url: str = typer.Option("http://localhost:8000"),
):
    resp = httpx.post(f"{api_url.rstrip('/')}/v1/auth/login", json={"email": email, "password": password}, timeout=30)
    if resp.status_code >= 400:
        rprint(f"[red]login failed[/red] {resp.text}")
        raise typer.Exit(1)
    data = resp.json()
    cfg = load_config()
    cfg.update({"api_url": api_url, "token": data["token"], "org": data.get("org")})
    save_config(cfg)
    rprint(f"[green]logged in[/green] as {data['user']['email']} / {data['org']['slug']}")


@auth_app.command("signup")
def auth_signup(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True),
    name: str = typer.Option(..., prompt=True),
    org_name: str = typer.Option(..., prompt=True),
    api_url: str = typer.Option("http://localhost:8000"),
):
    resp = httpx.post(
        f"{api_url.rstrip('/')}/v1/auth/signup",
        json={"email": email, "password": password, "name": name, "org_name": org_name},
        timeout=30,
    )
    if resp.status_code >= 400:
        rprint(f"[red]signup failed[/red] {resp.text}")
        raise typer.Exit(1)
    data = resp.json()
    cfg = load_config()
    cfg.update({"api_url": api_url, "token": data["token"], "org": data.get("org")})
    save_config(cfg)
    rprint(f"[green]signed up[/green] {data['user']['email']}")


@auth_app.command("key")
def auth_key(name: str = "cli"):
    with client() as c:
        resp = c.post("/v1/auth/api-keys", params={"name": name})
        resp.raise_for_status()
        data = resp.json()
        cfg = load_config()
        cfg["token"] = data["key"]
        save_config(cfg)
        rprint("API key (shown once):")
        rprint(data["key"])


@project_app.command("list")
def project_list():
    with client() as c:
        projects = c.get("/v1/projects").json()
        table = Table("id", "slug", "backend", "base_model")
        for p in projects:
            table.add_row(p["id"], p["slug"], p["default_backend"], p["default_base_model"])
        rprint(table)


@project_app.command("create")
def project_create(name: str, slug: str | None = None):
    with client() as c:
        resp = c.post("/v1/projects", json={"name": name, "slug": slug})
        resp.raise_for_status()
        project = resp.json()
        cfg = load_config()
        cfg["project_id"] = project["id"]
        save_config(cfg)
        rprint(f"created and using [bold]{project['slug']}[/bold] {project['id']}")


@project_app.command("use")
def project_use(ref: str):
    """Select a project by slug, org/slug, or id. Example: fh project use acme/support-bot"""
    slug = ref.split("/")[-1]
    with client() as c:
        projects = c.get("/v1/projects").json()
        project = next((p for p in projects if p["slug"] == slug or p["id"] == ref or p["slug"] == ref), None)
        if not project:
            rprint("[red]project not found[/red]")
            raise typer.Exit(1)
        cfg = load_config()
        cfg["project_id"] = project["id"]
        save_config(cfg)
        rprint(f"using project [bold]{project['slug']}[/bold] {project['id']}")


@dataset_app.command("upload")
def dataset_upload(
    path: Path,
    name: str = typer.Option(...),
    fmt: str = typer.Option("openai-chat", "--format"),
):
    cfg = load_config()
    if not cfg.get("project_id"):
        raise typer.BadParameter("run `fh project use <slug>` first")
    raw = path.read_bytes()
    with client() as c:
        ds = c.post("/v1/datasets", json={"name": name, "project_id": cfg["project_id"]}).json()
        init = c.post(
            "/v1/datasets/uploads",
            json={
                "dataset_id": ds["id"],
                "filename": path.name,
                "content_type": "application/octet-stream",
                "format": fmt,
            },
        ).json()
        put = c.put(init["upload_url"], content=raw, headers={"Content-Type": "application/octet-stream"})
        put.raise_for_status()
        job = c.post(
            f"/v1/datasets/{ds['id']}/versions",
            json={"dataset_id": ds["id"], "key": init["key"], "filename": path.name, "format": fmt},
        ).json()
        rprint(f"ingest job [bold]{job['job_id']}[/bold] dataset={ds['id']}")


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text()) or {}


@app.command("prepare")
def prepare(config: Path = typer.Option(..., "-f", "--file")):
    rprint("Prepare runs automatically after `fh dataset upload`. Use the web run page or `fh logs`.")
    _ = _load_yaml(config)


@app.command("train")
def train(
    config: Path = typer.Option(..., "-f", "--file"),
    dataset_version_id: str = typer.Option(...),
    backend: str | None = typer.Option(None),
):
    cfg = load_config()
    recipe = _load_yaml(config)
    if backend:
        recipe.setdefault("train", {})["backend"] = backend
    with client() as c:
        if not cfg.get("project_id"):
            projects = c.get("/v1/projects").json()
            project = next((p for p in projects if p["slug"] == recipe.get("project")), None)
            if not project:
                raise typer.BadParameter("project not set")
            project_id = project["id"]
        else:
            project_id = cfg["project_id"]
        resp = c.post(
            "/v1/jobs/train",
            json={
                "project_id": project_id,
                "dataset_version_id": dataset_version_id,
                "recipe": recipe,
                "backend": backend,
            },
        )
        if resp.status_code >= 400:
            rprint(resp.text)
            raise typer.Exit(1)
        job = resp.json()
        rprint(f"train job [bold]{job['job_id']}[/bold]")
        _tail(c, job["job_id"])


@app.command("eval")
def eval_cmd(
    run_id: str = typer.Option(...),
    suite: Path = typer.Option(..., "--suite"),
    metric: list[str] = typer.Option(["exact_match"]),
    min_score: float = typer.Option(0.8, "--min"),
):
    items = []
    text = suite.read_text()
    if text.strip().startswith("["):
        items = json.loads(text)
    else:
        items = [json.loads(line) for line in text.splitlines() if line.strip()]
    with client() as c:
        resp = c.post(
            "/v1/evals",
            json={
                "run_id": run_id,
                "suite_inline": items,
                "metrics": metric,
                "gate": {"metric": metric[0], "min": min_score},
            },
        )
        resp.raise_for_status()
        job = resp.json()
        rprint(f"eval job [bold]{job['job_id']}[/bold]")
        _tail(c, job["job_id"])


@app.command("deploy")
def deploy(run_id: str = typer.Option(...), name: str = "prod", override: bool = False):
    with client() as c:
        resp = c.post("/v1/deployments", json={"run_id": run_id, "name": name, "override_gate": override})
        if resp.status_code >= 400:
            rprint(resp.text)
            raise typer.Exit(1)
        job = resp.json()
        rprint(f"deploy job [bold]{job['job_id']}[/bold]")
        _tail(c, job["job_id"])


@app.command("logs")
def logs(job_id: str):
    with client() as c:
        _tail(c, job_id)


@app.command("chat")
def chat(
    deployment_id: str | None = typer.Option(None, "--deployment"),
    run_id: str | None = typer.Option(None, "--run"),
    message: str = typer.Option(..., "-m", "--message"),
):
    with client() as c:
        resp = c.post(
            "/v1/chat/completions",
            json={
                "deployment_id": deployment_id,
                "run_id": run_id,
                "messages": [{"role": "user", "content": message}],
            },
        )
        if resp.status_code >= 400:
            rprint(resp.text)
            raise typer.Exit(1)
        data = resp.json()
        rprint(data["choices"][0]["message"]["content"])


@app.command("pull")
def pull(run_id: str = typer.Option(...), out: Path = typer.Option(Path("./artifacts"))):
    with client() as c:
        run = c.get(f"/v1/runs/{run_id}").json()
        out.mkdir(parents=True, exist_ok=True)
        (out / "run.json").write_text(json.dumps(run, indent=2))
        rprint(f"wrote {out / 'run.json'}")


def _tail(c: httpx.Client, job_id: str) -> None:
    with c.stream("GET", f"/v1/jobs/{job_id}/events") as resp:
        if resp.status_code >= 400:
            rprint(resp.read().decode())
            raise typer.Exit(1)
        for line in resp.iter_lines():
            if not line or line.startswith(":"):
                continue
            rprint(line)
            if "\"event\": \"done\"" in line or line.startswith("event: done"):
                break


if __name__ == "__main__":
    app()
