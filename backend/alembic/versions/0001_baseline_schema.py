"""Baseline schema: adopt the full current model tree under Alembic.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-12

Existing deployments were built with ``Base.metadata.create_all`` plus ad-hoc
``ALTER TABLE`` statements in ``tradeo.db.init_db``. This baseline makes that
state the root of the migration tree:

- Fresh databases: creates every table known to ``Base.metadata`` (including
  the new ``agent_messages`` table) with ``checkfirst=True``.
- Existing databases: tables already exist, ``checkfirst`` makes this a no-op;
  ``init_db`` keeps backfilling legacy column drift, and this revision is the
  stamp point. Run ``alembic stamp 0001_baseline`` (or ``upgrade head``) once.

Future schema changes must be new revisions on top of this one — do not edit
this file.
"""

from __future__ import annotations

from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from tradeo.db import models  # noqa: F401  (register all models)
    from tradeo.db.session import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    raise NotImplementedError(
        "Baseline revision is not reversible: downgrading would drop the whole schema."
    )
