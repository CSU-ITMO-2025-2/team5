# pylint: disable=no-member,wrong-import-position
"""add score and reply to reviews

Revision ID: 47fe7e10c78d
Revises:
Create Date: 2025-12-17 18:42:57.470798

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "47fe7e10c78d"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("reviews", sa.Column("score", sa.Float(), nullable=True))
    op.add_column("reviews", sa.Column("reply", sa.Text(), nullable=True))

    op.execute(
        """
        UPDATE reviews
        SET score = CAST(polarity AS double precision)
        WHERE polarity ~ '^[0-9]+(\\.[0-9]+)?$';
        """
    )


def downgrade():
    op.drop_column("reviews", "reply")
    op.drop_column("reviews", "score")
