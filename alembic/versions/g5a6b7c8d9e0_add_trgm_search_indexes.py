"""Add pg_trgm GIN indexes for ILIKE search on customers, users, mailboxes.

Applies to PostgreSQL only (SQLite in dev skips this migration’s DDL).

Revision ID: g5a6b7c8d9e0
Revises: f4a5b6c7d8e9
Create Date: 2026-04-26 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "g5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    # customer: ilike on name, whatsapp_e164 (api/repositories/customers.py)
    op.create_index(
        "ix_customer_name_trgm",
        "customer",
        ["name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_customer_whatsapp_e164_trgm",
        "customer",
        ["whatsapp_e164"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"whatsapp_e164": "gin_trgm_ops"},
    )

    # user: ilike on name, email (api/repositories/users.py) — "accounts" / team users
    op.create_index(
        "ix_user_name_trgm",
        "user",
        ["name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_user_email_trgm",
        "user",
        ["email"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"email": "gin_trgm_ops"},
    )

    # mailbox: ilike on mailbox_address, provider (api/repositories/mailboxes.py) — email accounts
    op.create_index(
        "ix_mailbox_mailbox_address_trgm",
        "mailbox",
        ["mailbox_address"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"mailbox_address": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_mailbox_provider_trgm",
        "mailbox",
        ["provider"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"provider": "gin_trgm_ops"},
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.drop_index("ix_mailbox_provider_trgm", table_name="mailbox")
    op.drop_index("ix_mailbox_mailbox_address_trgm", table_name="mailbox")
    op.drop_index("ix_user_email_trgm", table_name="user")
    op.drop_index("ix_user_name_trgm", table_name="user")
    op.drop_index("ix_customer_whatsapp_e164_trgm", table_name="customer")
    op.drop_index("ix_customer_name_trgm", table_name="customer")
