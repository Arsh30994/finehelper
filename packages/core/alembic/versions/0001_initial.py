"""initial control-plane schema + optional Postgres RLS

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-26
"""

from alembic import op
from sqlalchemy import text

from finehelper_core.db.models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

TENANT_TABLES = [
    "memberships",
    "api_keys",
    "projects",
    "credentials",
    "datasets",
    "dataset_versions",
    "recipes",
    "jobs",
    "job_events",
    "runs",
    "artifacts",
    "eval_reports",
    "deployments",
    "usage_events",
    "invites",
]


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind)
    if bind.dialect.name != "postgresql":
        return
    for table in TENANT_TABLES:
        op.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        op.execute(
            text(
                f"""
                CREATE POLICY {table}_org_isolation ON {table}
                USING (
                    current_setting('app.current_org_id', true) IS NULL
                    OR current_setting('app.current_org_id', true) = ''
                    OR org_id::text = current_setting('app.current_org_id', true)
                )
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in TENANT_TABLES:
            op.execute(text(f"DROP POLICY IF EXISTS {table}_org_isolation ON {table}"))
            op.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
    Base.metadata.drop_all(bind)
