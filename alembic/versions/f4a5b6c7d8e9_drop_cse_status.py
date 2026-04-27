"""Drop customer_streaming_entitlement.status (use row presence + deleted_at only).

Revision ID: f4a5b6c7d8e9
Revises: e2f3a4b5c6d7
Create Date: 2026-04-26 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("customer_streaming_entitlement") as batch_op:
            batch_op.drop_column("status")
    else:
        op.drop_column("customer_streaming_entitlement", "status")


def downgrade() -> None:
    bind = op.get_bind()
    col = sa.Column("status", sa.String(length=32), nullable=False, server_default="active")
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("customer_streaming_entitlement") as batch_op:
            batch_op.add_column(col)
    else:
        op.add_column("customer_streaming_entitlement", col)
