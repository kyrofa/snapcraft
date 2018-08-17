"""create projects

Revision ID: 3cc8f76f818
Revises: 57ec072f545
Create Date: 2018-08-15 13:22:49.737144

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3cc8f76f818"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("options", sa.PickleType),
    )


def downgrade():
    op.drop_table("projects")
