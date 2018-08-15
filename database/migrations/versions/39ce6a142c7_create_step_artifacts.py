"""create part artifacts

Revision ID: 39ce6a142c7
Revises: 2ff276330d1
Create Date: 2018-08-14 14:40:32.329101

"""

# revision identifiers, used by Alembic.
revision = "39ce6a142c7"
down_revision = "d21f298277"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "step_artifacts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("step_id", sa.Integer, sa.ForeignKey("steps.id")),
        sa.Column("path", sa.String),
        sa.Column("type", sa.Enum("file", "directory")),
    )


def downgrade():
    op.drop_table("step_artifacts")
