# pylint: disable=no-member,wrong-import-position
"""add score and reply columns

Revision ID: 5ad021f08bdd
Revises: 5dfafdb99fe2
Create Date: 2025-12-17 18:59:12.181216

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5ad021f08bdd"
down_revision: Union[str, Sequence[str], None] = "5dfafdb99fe2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("reviews", sa.Column("score", sa.Float(), nullable=True))
    op.add_column("reviews", sa.Column("reply", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("reviews", "reply")
    op.drop_column("reviews", "score")
