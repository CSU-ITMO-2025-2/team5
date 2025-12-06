"""Initial Alembic migration: create ``users`` table and related indexes.

Revision ID: e6707cf3bf42
Revises:
Create Date: 2025-11-14 21:02:16.307920

This migration creates a lightweight users table intended for authentication
storage. The implementation favors explicit names and small schema hygiene
(imposed column length) while preserving the original migration semantics.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e6707cf3bf42"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "users"
IDX_ID = op.f("ix_users_id")
IDX_USERNAME = op.f("ix_users_username")


def upgrade() -> None:
    """Apply the migration: create the ``users`` table and its indexes.

    The table contains an integer primary key and two string columns:
    ``username`` and ``hashed_password``. Indexes are created for the
    ``id`` column (non-unique) and ``username`` (unique).
    """
    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(IDX_ID, TABLE_NAME, ["id"], unique=False)
    op.create_index(IDX_USERNAME, TABLE_NAME, ["username"], unique=True)


def downgrade() -> None:
    """Revert the migration: drop indexes and the ``users`` table.

    Dropping is performed in the reverse order of creation to avoid
    dependency issues on some database backends.
    """
    op.drop_index(IDX_USERNAME, table_name=TABLE_NAME)
    op.drop_index(IDX_ID, table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
