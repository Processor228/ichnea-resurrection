"""add observations table for debugging

Revision ID: fe7fc3fcdf8b
Revises: 3be4004781bc
Create Date: 2026-01-08 18:50:10.253421
"""

import logging

from alembic import op
import sqlalchemy as sa


log = logging.getLogger('alembic.migration')
revision = 'fe7fc3fcdf8b'
down_revision = '3be4004781bc'


def upgrade():
    log.info("Add submitted_report table.")

    stmt = sa.text("""\
CREATE TABLE submitted_report (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    api_key VARCHAR(40),
    lat FLOAT,
    lon FLOAT,
    source VARCHAR(20),
    report TEXT,
    created DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY submitted_report_created_idx (created),
    KEY submitted_report_api_key_idx (api_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
""")
    op.execute(stmt)


def downgrade():
    log.info("Drop observations table.")
    stmt = sa.text("""\
DROP TABLE submitter_report;
""")
    op.execute(stmt)
