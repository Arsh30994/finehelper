"""Legacy FastAPI router package — re-exports thin route modules."""

from finehelper_api.routes.auth import router as auth
from finehelper_api.routes.chat import router as chat
from finehelper_api.routes.datasets import router as datasets
from finehelper_api.routes.jobs import router as jobs
from finehelper_api.routes.ops import router as ops
from finehelper_api.routes.orgs import router as orgs
from finehelper_api.routes.projects import router as projects

__all__ = ["auth", "chat", "datasets", "jobs", "ops", "orgs", "projects"]
