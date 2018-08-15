"""create part dependencies

Revision ID: 11e5aa24673
Revises: 176f258e6d
Create Date: 2018-08-14 14:41:00.697667

"""

# revision identifiers, used by Alembic.
revision = "11e5aa24673"
down_revision = "57ec072f545"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "step_dependencies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("step_id", sa.Integer, sa.ForeignKey("steps.id")),
        sa.Column("path", sa.String),
    )


def downgrade():
    op.drop_table("step_dependencies")
