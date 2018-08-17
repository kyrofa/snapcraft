"""create steps

Revision ID: d21f298277
Revises: 4bb90886ccb
Create Date: 2018-08-14 14:23:07.194183

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d21f298277"
down_revision = "4bb90886ccb"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "steps",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("part_name", sa.String, sa.ForeignKey("parts.name")),
        sa.Column("name", sa.Enum("pull", "build", "stage", "prime")),
        sa.Column("manifest", sa.PickleType),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
    )


def downgrade():
    op.drop_table("steps")
