"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-01-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("role", sa.String(50), nullable=False, default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("last_login", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create suppliers table
    op.create_table(
        "suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("contact_name", sa.String(255)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("website", sa.String(255)),
        sa.Column("notes", sa.Text()),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create customers table
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("contact_name", sa.String(255)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("address_line1", sa.String(255)),
        sa.Column("address_line2", sa.String(255)),
        sa.Column("city", sa.String(100)),
        sa.Column("postal_code", sa.String(20)),
        sa.Column("country", sa.String(100), default="UK"),
        sa.Column("notes", sa.Text()),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create materials table
    op.create_table(
        "materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("sku", sa.String(100), unique=True, index=True),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(50), nullable=False, index=True),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("current_price", sa.Numeric(10, 4), nullable=False, default=0.0),
        sa.Column(
            "supplier_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suppliers.id"),
        ),
        sa.Column("specifications", postgresql.JSONB()),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("last_price_update", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create material_prices table
    op.create_table(
        "material_prices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("materials.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("price", sa.Numeric(10, 4), nullable=False),
        sa.Column(
            "effective_from", sa.DateTime(timezone=True), nullable=False, index=True
        ),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("source", sa.String(255)),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # Create estimates table
    op.create_table(
        "estimates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "reference_number", sa.String(50), unique=True, nullable=False, index=True
        ),
        sa.Column("job_name", sa.String(255), nullable=False),
        sa.Column(
            "status", sa.String(50), nullable=False, default="draft", index=True
        ),
        sa.Column("complexity_tier", sa.Integer(), default=3),
        sa.Column(
            "customer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("customers.id"),
            index=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("inputs", postgresql.JSONB(), nullable=False),
        sa.Column("outputs", postgresql.JSONB()),
        sa.Column("confidence_low", sa.Numeric(10, 2)),
        sa.Column("confidence_high", sa.Numeric(10, 2)),
        sa.Column("confidence_level", sa.Numeric(5, 4)),
        sa.Column("ml_prediction", sa.Numeric(10, 2)),
        sa.Column("ml_confidence", sa.Numeric(5, 4)),
        sa.Column("ml_model_version", sa.String(50)),
        sa.Column("ml_enhanced", sa.Boolean(), default=False),
        sa.Column("total_cost", sa.Numeric(10, 2)),
        sa.Column("quoted_price", sa.Numeric(10, 2)),
        sa.Column("margin_percent", sa.Numeric(5, 2)),
        sa.Column("calculated_at", sa.DateTime(timezone=True)),
        sa.Column("quoted_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("internal_notes", sa.Text()),
        sa.Column("customer_notes", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create feedback table
    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "estimate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("estimates.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("operation", sa.String(100), nullable=False, index=True),
        sa.Column("machine_id", sa.String(50)),
        sa.Column("operator_id", sa.String(50)),
        sa.Column("operator_skill_level", sa.Integer()),
        sa.Column("estimated_setup_time", sa.Integer()),
        sa.Column("actual_setup_time", sa.Integer()),
        sa.Column("estimated_run_time", sa.Integer()),
        sa.Column("actual_run_time", sa.Integer()),
        sa.Column("estimated_material_usage", sa.Numeric(10, 3)),
        sa.Column("actual_material_usage", sa.Numeric(10, 3)),
        sa.Column("wastage_units", sa.Integer()),
        sa.Column("wastage_reason", sa.String(255)),
        sa.Column("first_pass_yield", sa.Numeric(5, 4)),
        sa.Column("rework_time", sa.Integer()),
        sa.Column("defect_count", sa.Integer()),
        sa.Column("batch_position", sa.Integer()),
        sa.Column("shift", sa.String(20)),
        sa.Column("notes", sa.Text()),
        sa.Column("issues_encountered", postgresql.ARRAY(sa.String())),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "submitted_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
        ),
        sa.Column("is_validated", sa.Boolean(), default=False),
        sa.Column("validated_by", postgresql.UUID(as_uuid=True)),
        sa.Column("validated_at", sa.DateTime(timezone=True)),
    )

    # Create pricing_rules table
    op.create_table(
        "pricing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("category", sa.String(50), nullable=False, index=True),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("dependencies", postgresql.ARRAY(sa.String())),
        sa.Column("default_value", sa.Float()),
        sa.Column("unit", sa.String(50)),
        sa.Column("version", sa.Integer(), default=1),
        sa.Column("is_active", sa.Boolean(), default=True, index=True),
        sa.Column("superseded_by", sa.String(100)),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.String(255)),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create ml_models table
    op.create_table(
        "ml_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, index=True),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("model_type", sa.String(100), nullable=False),
        sa.Column("target_variable", sa.String(100), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("training_samples", sa.Integer(), nullable=False),
        sa.Column("feature_names", postgresql.JSONB(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("hyperparameters", postgresql.JSONB()),
        sa.Column("model_blob", sa.LargeBinary()),
        sa.Column("model_path", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), default=False, index=True),
        sa.Column("is_production", sa.Boolean(), default=False, index=True),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("deactivated_at", sa.DateTime(timezone=True)),
        sa.Column("traffic_percentage", sa.Integer(), default=0),
        sa.Column("trained_by", sa.String(255)),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("ml_models")
    op.drop_table("pricing_rules")
    op.drop_table("feedback")
    op.drop_table("estimates")
    op.drop_table("material_prices")
    op.drop_table("materials")
    op.drop_table("customers")
    op.drop_table("suppliers")
    op.drop_table("users")
