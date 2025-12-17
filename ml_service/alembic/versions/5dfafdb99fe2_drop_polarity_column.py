# pylint: disable=no-member,wrong-import-position
"""drop polarity column

Revision ID: 5dfafdb99fe2
Revises: 47fe7e10c78d
Create Date: 2025-12-17 18:55:18.598835

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5dfafdb99fe2"
down_revision: Union[str, Sequence[str], None] = "47fe7e10c78d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.drop_column("reviews", "polarity")


def downgrade():
    op.add_column("reviews", sa.Column("polarity", sa.String(length=32), nullable=True))
