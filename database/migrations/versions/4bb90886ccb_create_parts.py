"""create parts

Revision ID: 4bb90886ccb
Revises:
Create Date: 2018-08-13 15:27:11.640567

"""

# revision identifiers, used by Alembic.
revision = "4bb90886ccb"
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table("parts", sa.Column("name", sa.String, primary_key=True))


def downgrade():
    op.drop_table("parts")
