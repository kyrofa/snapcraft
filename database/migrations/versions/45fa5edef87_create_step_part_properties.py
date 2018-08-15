"""create part properties

Revision ID: 45fa5edef87
Revises: 4b0f724d8f7
Create Date: 2018-08-14 14:39:55.604086

"""

# revision identifiers, used by Alembic.
revision = "45fa5edef87"
down_revision = "2ff276330d1"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "step_part_properties",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("step_id", sa.Integer, sa.ForeignKey("steps.id")),
        sa.Column("key", sa.String),
        sa.Column("value", sa.String),
    )


def downgrade():
    op.drop_table("step_part_properties")
