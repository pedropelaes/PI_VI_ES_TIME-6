"""cria opportunities e opportunity_applications

Revision ID: f1a2b3c4d5e7
Revises: e5f1a2b3c4d6
Create Date: 2026-11-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql


revision: str = 'f1a2b3c4d5e7'
down_revision: Union[str, None] = 'e5f1a2b3c4d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

opportunity_mode = sa.Enum("PRESENCIAL", "ONLINE", name="opportunitymode")
application_status = sa.Enum("PENDENTE", "APROVADA", "RECUSADA", name="applicationstatus")
_STR = sqlmodel.sql.sqltypes.AutoString


def upgrade() -> None:
    op.create_table(
        "opportunities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organizer_id", sa.Uuid(), nullable=False),
        sa.Column("title", _STR(length=120), nullable=False),
        sa.Column("description", _STR(), nullable=False),
        sa.Column("mode", opportunity_mode, nullable=False),
        sa.Column("state", _STR(length=2), nullable=True),
        sa.Column("city", _STR(), nullable=True),
        sa.Column("address", _STR(), nullable=True),
        sa.Column("meeting_url", _STR(), nullable=True),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registration_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("min_age", sa.Integer(), nullable=True),
        sa.Column("max_age", sa.Integer(), nullable=True),
        sa.Column("positions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("max_applications", sa.Integer(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organizer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_opportunities_organizer_id", "opportunities", ["organizer_id"])
    op.create_index("ix_opportunities_state", "opportunities", ["state"])
    op.create_index("ix_opportunities_event_at", "opportunities", ["event_at"])
    op.create_index(
        "ix_opportunities_registration_deadline", "opportunities", ["registration_deadline"]
    )

    op.create_table(
        "opportunity_applications",
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("athlete_id", sa.Uuid(), nullable=False),
        sa.Column("status", application_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["opportunity_id"], ["opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["athlete_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("opportunity_id", "athlete_id"),
    )
    op.create_index(
        "ix_opportunity_applications_athlete_id", "opportunity_applications", ["athlete_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_opportunity_applications_athlete_id", "opportunity_applications")
    op.drop_table("opportunity_applications")
    op.drop_index("ix_opportunities_registration_deadline", "opportunities")
    op.drop_index("ix_opportunities_event_at", "opportunities")
    op.drop_index("ix_opportunities_state", "opportunities")
    op.drop_index("ix_opportunities_organizer_id", "opportunities")
    op.drop_table("opportunities")
    application_status.drop(op.get_bind(), checkfirst=True)
    opportunity_mode.drop(op.get_bind(), checkfirst=True)
