"""create steps

Revision ID: d21f298277
Revises: 4bb90886ccb
Create Date: 2018-08-14 14:23:07.194183

"""

# revision identifiers, used by Alembic.
revision = "d21f298277"
down_revision = "4bb90886ccb"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "steps",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("part_name", sa.String, sa.ForeignKey("parts.name")),
        sa.Column("name", sa.String),
    )


def downgrade():
    op.drop_table("steps")
