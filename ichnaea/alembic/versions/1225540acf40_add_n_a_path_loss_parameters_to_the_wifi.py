"""Add n,A path loss parameters to the wifi

Revision ID: 1225540acf40
Revises: ad7914c2dd33
Create Date: 2026-05-05 14:04:39.895503
"""

import logging

from alembic import op
import sqlalchemy as sa


log = logging.getLogger('alembic.migration')
revision = '1225540acf40'
down_revision = 'ad7914c2dd33'

SHARDS = [f"wifi_shard_{x}" for x in "0123456789abcdef"]

def upgrade():
    for table in SHARDS:
        op.add_column(
            table,
            sa.Column("A", sa.Float(), nullable=True)
        )
        op.add_column(
            table,
            sa.Column("n", sa.Float(), nullable=True)
        )


def downgrade():
    for table in SHARDS:
        op.drop_column(table, "n")
        op.drop_column(table, "A")