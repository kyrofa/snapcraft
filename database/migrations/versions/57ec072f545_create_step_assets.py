"""create step assets

Revision ID: 57ec072f545
Revises: 11e5aa24673
Create Date: 2018-08-14 14:42:35.863367

"""

# revision identifiers, used by Alembic.
revision = "57ec072f545"
down_revision = "45fa5edef87"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        "step_assets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("step_id", sa.Integer, sa.ForeignKey("steps.id")),
        sa.Column("key", sa.String),
        sa.Column("value", sa.String),
    )


def downgrade():
    op.drop_table("step_assets")
