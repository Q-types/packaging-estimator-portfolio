"""Add prospects tables for Companies House search

Revision ID: 002_add_prospects
Revises: 001_initial_schema
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("""
        CREATE TYPE prospectstatus AS ENUM (
            'new', 'scored', 'qualified', 'contacted', 'interested',
            'proposal', 'negotiation', 'won', 'lost', 'disqualified'
        )
    """)
    op.execute("""
        CREATE TYPE prospecttier AS ENUM ('hot', 'warm', 'cool', 'cold')
    """)
    op.execute("""
        CREATE TYPE packagingneed AS ENUM ('high', 'medium', 'low', 'unknown')
    """)

    # Create prospects table
    op.create_table(
        "prospects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Companies House identifiers
        sa.Column("company_number", sa.String(8), unique=True, index=True, nullable=False),
        sa.Column("company_name", sa.String(500), nullable=False, index=True),

        # Company details
        sa.Column("company_status", sa.String(50)),
        sa.Column("company_type", sa.String(100)),
        sa.Column("date_of_creation", sa.DateTime),
        sa.Column("date_of_cessation", sa.DateTime),
        sa.Column("jurisdiction", sa.String(50)),

        # Address
        sa.Column("address_line_1", sa.String(255)),
        sa.Column("address_line_2", sa.String(255)),
        sa.Column("locality", sa.String(100)),
        sa.Column("region", sa.String(100), index=True),
        sa.Column("postal_code", sa.String(20), index=True),
        sa.Column("country", sa.String(100), default="United Kingdom"),

        # Industry classification
        sa.Column("sic_codes", postgresql.ARRAY(sa.String(10))),
        sa.Column("primary_sic_code", sa.String(10), index=True),
        sa.Column("industry_sector", sa.String(100), index=True),
        sa.Column("packaging_need", postgresql.ENUM("high", "medium", "low", "unknown", name="packagingneed", create_type=False), default="unknown"),
        sa.Column("packaging_need_reason", sa.String(255)),

        # Company size indicators
        sa.Column("officer_count", sa.Integer, default=0),
        sa.Column("active_officer_count", sa.Integer, default=0),
        sa.Column("filing_count", sa.Integer, default=0),
        sa.Column("has_charges", sa.Boolean, default=False),
        sa.Column("has_insolvency_history", sa.Boolean, default=False),

        # Web presence
        sa.Column("website", sa.String(500)),
        sa.Column("has_website", sa.Boolean, default=False),
        sa.Column("has_https", sa.Boolean, default=False),

        # Derived features
        sa.Column("company_age_years", sa.Float),

        # ML Scoring
        sa.Column("prospect_score", sa.Float, index=True),
        sa.Column("tier", postgresql.ENUM("hot", "warm", "cool", "cold", name="prospecttier", create_type=False), index=True),

        # Score components
        sa.Column("industry_score", sa.Float),
        sa.Column("age_score", sa.Float),
        sa.Column("size_score", sa.Float),
        sa.Column("geography_score", sa.Float),
        sa.Column("web_presence_score", sa.Float),
        sa.Column("ml_model_score", sa.Float),

        # Clustering
        sa.Column("cluster_id", sa.Integer, index=True),
        sa.Column("cluster_name", sa.String(100)),
        sa.Column("cluster_confidence", sa.Float),

        # Sales pipeline
        sa.Column("status", postgresql.ENUM("new", "scored", "qualified", "contacted", "interested", "proposal", "negotiation", "won", "lost", "disqualified", name="prospectstatus", create_type=False), default="new", index=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), index=True),

        # Tracking
        sa.Column("last_enriched_at", sa.DateTime),
        sa.Column("last_scored_at", sa.DateTime),
        sa.Column("last_contacted_at", sa.DateTime),

        # Notes and raw data
        sa.Column("notes", sa.Text),
        sa.Column("raw_data", postgresql.JSON),
    )

    # Create prospect_scores table
    op.create_table(
        "prospect_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.Column("prospect_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prospects.id"), index=True, nullable=False),

        # Scores
        sa.Column("total_score", sa.Float, nullable=False),
        sa.Column("tier", postgresql.ENUM("hot", "warm", "cool", "cold", name="prospecttier", create_type=False), nullable=False),

        # Component scores
        sa.Column("industry_score", sa.Float),
        sa.Column("age_score", sa.Float),
        sa.Column("size_score", sa.Float),
        sa.Column("geography_score", sa.Float),
        sa.Column("web_presence_score", sa.Float),

        # ML model
        sa.Column("ml_model_score", sa.Float),
        sa.Column("ml_model_version", sa.String(50)),

        # Metadata
        sa.Column("icp_profile_version", sa.String(50)),
        sa.Column("scoring_config", postgresql.JSON),
    )

    # Create prospect_activities table
    op.create_table(
        "prospect_activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.Column("prospect_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prospects.id"), index=True, nullable=False),

        sa.Column("activity_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("extra_data", postgresql.JSON),
    )

    # Create prospect_searches table
    op.create_table(
        "prospect_searches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Search parameters
        sa.Column("query", sa.String(500)),
        sa.Column("sic_codes", postgresql.ARRAY(sa.String(10))),
        sa.Column("location", sa.String(100)),
        sa.Column("company_status", sa.String(50)),
        sa.Column("incorporated_from", sa.DateTime),
        sa.Column("incorporated_to", sa.DateTime),

        # Results
        sa.Column("total_results", sa.Integer, default=0),
        sa.Column("results_fetched", sa.Integer, default=0),
        sa.Column("prospects_created", sa.Integer, default=0),
        sa.Column("prospects_updated", sa.Integer, default=0),

        # Performance
        sa.Column("duration_seconds", sa.Float),
        sa.Column("api_calls_made", sa.Integer, default=0),

        # Who ran the search
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),

        # Status
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("error_message", sa.Text),
    )

    # Create indexes
    op.create_index("ix_prospects_score_tier", "prospects", ["prospect_score", "tier"])
    op.create_index("ix_prospects_industry", "prospects", ["industry_sector", "packaging_need"])


def downgrade() -> None:
    # Drop tables
    op.drop_table("prospect_searches")
    op.drop_table("prospect_activities")
    op.drop_table("prospect_scores")
    op.drop_table("prospects")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS prospectstatus")
    op.execute("DROP TYPE IF EXISTS prospecttier")
    op.execute("DROP TYPE IF EXISTS packagingneed")
