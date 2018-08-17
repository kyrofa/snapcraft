"""create metadata

Revision ID: 4e10dffce48
Revises: 57ec072f545
Create Date: 2018-08-15 15:13:08.886236

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "4e10dffce48"
down_revision = "39ce6a142c7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "metadata",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("step_id", sa.Integer, sa.ForeignKey("steps.id")),
        sa.Column("source", sa.Enum("EXTRACTED", "SCRIPTLET")),
        sa.Column("common_id", sa.String),
        sa.Column("summary", sa.String),
        sa.Column("description", sa.String),
        sa.Column("version", sa.String),
        sa.Column("grade", sa.String),
        sa.Column("icon", sa.String),
        sa.Column("desktop_file_paths", sa.PickleType),
        sa.Column("files", sa.PickleType),
    )


def downgrade():
    op.drop_table("metadata")
