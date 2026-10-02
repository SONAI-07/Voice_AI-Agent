"""add tenant agents campaigns and call ownership

Revision ID: 2193f0521efe
Revises: 5f6aa0e9b5b8
Create Date: 2026-10-02 13:53:15.049124

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2193f0521efe'
down_revision: Union[str, Sequence[str], None] = '5f6aa0e9b5b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("language_code", sa.String(length=20), nullable=False),
        sa.Column("voice_id", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_agents_tenant_id"),
        "agents",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_campaigns_agent_id"),
        "campaigns",
        ["agent_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_campaigns_tenant_id"),
        "campaigns",
        ["tenant_id"],
        unique=False,
    )

    op.add_column(
        "calls",
        sa.Column("agent_id", sa.Integer(), nullable=True),
    )

    op.add_column(
        "calls",
        sa.Column("campaign_id", sa.Integer(), nullable=True),
    )

    op.create_index(
        op.f("ix_calls_agent_id"),
        "calls",
        ["agent_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_calls_campaign_id"),
        "calls",
        ["campaign_id"],
        unique=False,
    )

    op.create_foreign_key(
        "fk_calls_campaign_id_campaigns",
        "calls",
        "campaigns",
        ["campaign_id"],
        ["id"],
    )

    op.create_foreign_key(
        "fk_calls_agent_id_agents",
        "calls",
        "agents",
        ["agent_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(
        "fk_calls_agent_id_agents",
        "calls",
        type_="foreignkey",
    )

    op.drop_constraint(
        "fk_calls_campaign_id_campaigns",
        "calls",
        type_="foreignkey",
    )

    op.drop_index(
        op.f("ix_calls_campaign_id"),
        table_name="calls",
    )

    op.drop_index(
        op.f("ix_calls_agent_id"),
        table_name="calls",
    )

    op.drop_column(
        "calls",
        "campaign_id",
    )

    op.drop_column(
        "calls",
        "agent_id",
    )

    op.drop_index(
        op.f("ix_campaigns_tenant_id"),
        table_name="campaigns",
    )

    op.drop_index(
        op.f("ix_campaigns_agent_id"),
        table_name="campaigns",
    )

    op.drop_table("campaigns")

    op.drop_index(
        op.f("ix_agents_tenant_id"),
        table_name="agents",
    )

    op.drop_table("agents")