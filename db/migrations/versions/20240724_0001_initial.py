"""Initial tables for facial analysis pipeline."""
from __future__ import annotations

from alembic import op  # type: ignore
import sqlalchemy as sa

revision = "20240724_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "images",
        sa.Column("image_id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("source", sa.Text(), server_default="telegram"),
        sa.Column("bucket_path", sa.Text(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("taken_at", sa.DateTime(timezone=True)),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "face_landmarks",
        sa.Column("image_id", sa.UUID(), sa.ForeignKey("images.image_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("model", sa.Text(), server_default="mediapipe_face_mesh"),
        sa.Column("landmarks", sa.JSON(), nullable=False),
        sa.Column("regions", sa.JSON()),
        sa.Column("contour_heatmap_path", sa.Text()),
    )
    op.create_table(
        "lesions",
        sa.Column("lesion_id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("image_id", sa.UUID(), sa.ForeignKey("images.image_id", ondelete="CASCADE")),
        sa.Column("detector", sa.Text()),
        sa.Column("bbox", sa.JSON()),
        sa.Column("mask_path", sa.Text()),
        sa.Column("confidence", sa.Numeric()),
        sa.Column("type", sa.Text(), server_default="pimple"),
        sa.Column("region", sa.Text()),
        sa.Column("area_px", sa.Integer()),
        sa.Column("redness_score", sa.Numeric()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_table(
        "sessions",
        sa.Column("session_id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("session_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("notes", sa.Text()),
    )
    op.create_table(
        "session_images",
        sa.Column("session_id", sa.UUID(), sa.ForeignKey("sessions.session_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("image_id", sa.UUID(), sa.ForeignKey("images.image_id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("session_images")
    op.drop_table("sessions")
    op.drop_table("lesions")
    op.drop_table("face_landmarks")
    op.drop_table("images")
