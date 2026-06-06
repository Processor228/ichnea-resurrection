"""add observations table

Revision ID: ad7914c2dd33
Revises: fe7fc3fcdf8b
Create Date: 2026-03-17 21:00:35.933708
"""

import logging

from alembic import op
import sqlalchemy as sa


log = logging.getLogger('alembic.migration')
revision = 'ad7914c2dd33'
down_revision = 'fe7fc3fcdf8b'


def upgrade():
    log.info("Add wifi_observations table.")

    stmt = sa.text("""\
CREATE TABLE wifi_observations (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `mac` binary(6),
    lat FLOAT,
    lon FLOAT,
    rssi INTEGER,
    source VARCHAR(20),
    speed FLOAT,
    age INTEGER,
    accuracy FLOAT,
    created DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
""")
    op.execute(stmt)


def downgrade():
    log.info("Drop wifi_observations table.")
    stmt = sa.text("""\
DROP TABLE wifi_observations;
""")
    op.execute(stmt)
