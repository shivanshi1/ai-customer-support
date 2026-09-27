"""Add human assignment to review tickets."""

from alembic import op
import sqlalchemy as sa

revision = "20260927_04"
down_revision = "20260927_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("support_tickets", sa.Column("assignee", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("support_tickets", "assignee")
