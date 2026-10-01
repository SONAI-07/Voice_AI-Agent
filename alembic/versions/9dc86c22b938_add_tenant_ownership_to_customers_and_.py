"""add tenant ownership to customers and calls

Revision ID: <KEEP GENERATED REVISION>
Revises: 5fc89a38bb1b
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9dc86c22b938"
down_revision: Union[str, Sequence[str], None] = "5fc89a38bb1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------
    # 1. Add nullable columns first.
    # ---------------------------------------------------------

    op.add_column(
        "customers",
        sa.Column(
            "tenant_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.add_column(
        "calls",
        sa.Column(
            "tenant_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    # ---------------------------------------------------------
    # 2. Add foreign keys.
    # ---------------------------------------------------------

    op.create_foreign_key(
        "fk_customers_tenant_id_tenants",
        "customers",
        "tenants",
        ["tenant_id"],
        ["id"],
    )

    op.create_foreign_key(
        "fk_calls_tenant_id_tenants",
        "calls",
        "tenants",
        ["tenant_id"],
        ["id"],
    )

    # ---------------------------------------------------------
    # 3. Index tenant ownership.
    # ---------------------------------------------------------

    op.create_index(
        "ix_customers_tenant_id",
        "customers",
        ["tenant_id"],
        unique=False,
    )

    op.create_index(
        "ix_calls_tenant_id",
        "calls",
        ["tenant_id"],
        unique=False,
    )

    # ---------------------------------------------------------
    # 4. Backfill existing customers.
    #
    # There is exactly one Tenant in the current development
    # database. If this migration is ever run against a database
    # with multiple tenants, fail rather than guessing ownership.
    # ---------------------------------------------------------

    bind = op.get_bind()

    tenant_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM tenants")
    ).scalar_one()

    if tenant_count != 1:
        raise RuntimeError(
            "Cannot safely backfill customers. "
            f"Expected exactly 1 tenant, found {tenant_count}."
        )

    tenant_id = bind.execute(
        sa.text("SELECT id FROM tenants ORDER BY id LIMIT 1")
    ).scalar_one()

    bind.execute(
        sa.text(
            """
            UPDATE customers
            SET tenant_id = :tenant_id
            WHERE tenant_id IS NULL
            """
        ),
        {"tenant_id": tenant_id},
    )

    # ---------------------------------------------------------
    # 5. Backfill calls from their authoritative customer.
    # ---------------------------------------------------------

    bind.execute(
        sa.text(
            """
            UPDATE calls AS calls_table
            SET tenant_id = customers_table.tenant_id
                FROM customers AS customers_table
            WHERE calls_table.customer_id = customers_table.id
              AND calls_table.tenant_id IS NULL
            """
        )
    )

    # ---------------------------------------------------------
    # 6. Verify no tenant-owned rows remain NULL.
    # ---------------------------------------------------------

    null_customers = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM customers
            WHERE tenant_id IS NULL
            """
        )
    ).scalar_one()

    if null_customers != 0:
        raise RuntimeError(
            f"Customer tenant backfill incomplete: "
            f"{null_customers} rows still have NULL tenant_id."
        )

    null_calls = bind.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM calls
            WHERE tenant_id IS NULL
            """
        )
    ).scalar_one()

    if null_calls != 0:
        raise RuntimeError(
            f"Call tenant backfill incomplete: "
            f"{null_calls} rows still have NULL tenant_id."
        )

    # ---------------------------------------------------------
    # 7. tenant_id is now mandatory.
    # ---------------------------------------------------------

    op.alter_column(
        "customers",
        "tenant_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.alter_column(
        "calls",
        "tenant_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # ---------------------------------------------------------
    # 8. Replace global customer phone uniqueness with
    #    tenant-scoped uniqueness.
    # ---------------------------------------------------------

    op.drop_index(
        "ix_customers_phone_number",
        table_name="customers",
    )

    op.create_index(
        "ix_customers_tenant_phone",
        "customers",
        ["tenant_id", "phone_number"],
        unique=True,
    )


def downgrade() -> None:
    # Restore global phone uniqueness.
    op.drop_index(
        "ix_customers_tenant_phone",
        table_name="customers",
    )

    op.create_index(
        "ix_customers_phone_number",
        "customers",
        ["phone_number"],
        unique=True,
    )

    op.drop_index(
        "ix_calls_tenant_id",
        table_name="calls",
    )

    op.drop_index(
        "ix_customers_tenant_id",
        table_name="customers",
    )

    op.drop_constraint(
        "fk_calls_tenant_id_tenants",
        "calls",
        type_="foreignkey",
    )

    op.drop_constraint(
        "fk_customers_tenant_id_tenants",
        "customers",
        type_="foreignkey",
    )

    op.drop_column("calls", "tenant_id")
    op.drop_column("customers", "tenant_id")