"""Add persisted knowledge chunks for retrieval."""

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa

revision = "20260927_03"
down_revision = "20260922_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(length=512), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source", "chunk_index", name="uq_knowledge_source_chunk"),
    )
    op.create_index("ix_knowledge_chunks_source", "knowledge_chunks", ["source"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_source", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
