"""create parts

Revision ID: 4bb90886ccb
Revises:
Create Date: 2018-08-13 15:27:11.640567

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "4bb90886ccb"
down_revision = "3cc8f76f818"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "parts",
        sa.Column("name", sa.String, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id")),
        sa.Column("properties", sa.PickleType),
    )


def downgrade():
    op.drop_table("parts")
