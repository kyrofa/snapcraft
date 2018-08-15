"""create project options

Revision ID: 2ff276330d1
Revises: 45fa5edef87
Create Date: 2018-08-14 14:40:05.637089

"""

# revision identifiers, used by Alembic.
revision = "2ff276330d1"
down_revision = "176f258e6d"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "step_project_options",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("step_id", sa.Integer, sa.ForeignKey("steps.id")),
        sa.Column("key", sa.String),
        sa.Column("value", sa.String),
    )


def downgrade():
    op.drop_table("step_project_options")
