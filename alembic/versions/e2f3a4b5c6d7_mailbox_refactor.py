"""Mailbox refactor: drop streaming_account and mailbox_credential, add mailbox tables.

Schema-only: does not insert seed rows; load catalog and other data yourself.

Revision ID: e2f3a4b5c6d7
Revises: c303e69e3f4e
Create Date: 2026-04-25 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "c303e69e3f4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        fk_type = sa.Integer()
    else:
        fk_type = sa.BigInteger()

    op.drop_index(
        op.f("ix_mailbox_credential_streaming_account_id"), table_name="mailbox_credential"
    )
    op.drop_table("mailbox_credential")
    op.drop_index(op.f("ix_streaming_account_streaming_service_id"), table_name="streaming_account")
    op.drop_index(op.f("ix_streaming_account_entity_id"), table_name="streaming_account")
    op.drop_table("streaming_account")

    op.create_table(
        "mailbox",
        sa.Column("entity_id", fk_type, nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="gmail"),
        sa.Column("mailbox_address", sa.String(length=320), nullable=False),
        sa.Column("credential_payload", sa.JSON(), nullable=True),
        sa.Column("secret_ref", sa.String(length=512), nullable=True),
        sa.Column("token_scopes", sa.String(length=2048), nullable=True),
        sa.Column("token_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_customer_links", sa.Integer(), nullable=True),
        sa.Column("id", fk_type, autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["entity_id"], ["entity.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_id", "mailbox_address", name="uq_mailbox_entity_address"),
    )
    op.create_index(op.f("ix_mailbox_entity_id"), "mailbox", ["entity_id"], unique=False)

    op.create_table(
        "customer_mailbox",
        sa.Column("customer_id", fk_type, nullable=False),
        sa.Column("mailbox_id", fk_type, nullable=False),
        sa.Column("id", fk_type, autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customer.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mailbox_id"], ["mailbox.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", "mailbox_id", name="uq_customer_mailbox_pair"),
    )
    op.create_index(
        op.f("ix_customer_mailbox_customer_id"), "customer_mailbox", ["customer_id"], unique=False
    )
    op.create_index(
        op.f("ix_customer_mailbox_mailbox_id"), "customer_mailbox", ["mailbox_id"], unique=False
    )

    with op.batch_alter_table("customer_streaming_entitlement") as batch_op:
        batch_op.add_column(sa.Column("mailbox_id", fk_type, nullable=True))
        batch_op.create_foreign_key(
            "fk_cse_mailbox",
            "mailbox",
            ["mailbox_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index("ix_cse_mailbox_id", ["mailbox_id"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade to streaming_account is not supported")
