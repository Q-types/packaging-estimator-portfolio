"""Add bespoke fit and exclusion fields for PackagePro

Revision ID: 003
Revises: 002
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add bespoke fit score column
    op.add_column(
        "prospects",
        sa.Column("bespoke_fit_score", sa.Float, nullable=True)
    )

    # Add bespoke fit reason column
    op.add_column(
        "prospects",
        sa.Column("bespoke_fit_reason", sa.String(500), nullable=True)
    )

    # Add exclusion flag
    op.add_column(
        "prospects",
        sa.Column("is_excluded", sa.Boolean, default=False, nullable=True)
    )

    # Add exclusion reason
    op.add_column(
        "prospects",
        sa.Column("exclusion_reason", sa.String(255), nullable=True)
    )

    # Create index on is_excluded for filtering
    op.create_index(
        "ix_prospects_is_excluded",
        "prospects",
        ["is_excluded"]
    )

    # Create index on bespoke_fit_score for sorting
    op.create_index(
        "ix_prospects_bespoke_fit_score",
        "prospects",
        ["bespoke_fit_score"]
    )

    # Update existing rows to have is_excluded = False
    op.execute("UPDATE prospects SET is_excluded = FALSE WHERE is_excluded IS NULL")


def downgrade() -> None:
    op.drop_index("ix_prospects_bespoke_fit_score")
    op.drop_index("ix_prospects_is_excluded")
    op.drop_column("prospects", "exclusion_reason")
    op.drop_column("prospects", "is_excluded")
    op.drop_column("prospects", "bespoke_fit_reason")
    op.drop_column("prospects", "bespoke_fit_score")
