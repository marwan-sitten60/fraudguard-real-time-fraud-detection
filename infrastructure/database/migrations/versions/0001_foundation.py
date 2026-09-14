"""Minimal system-of-record schema; scoring does not write these tables yet."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("transaction_id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("merchant_id", sa.String(64), nullable=False),
        sa.Column("device_id", sa.String(64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("merchant_category", sa.String(4), nullable=False),
        sa.Column("payment_channel", sa.String(16), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("ip_country", sa.String(2), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_transactions_amount"),
    )
    op.create_table(
        "fraud_decisions",
        sa.Column("decision_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column(
            "transaction_id",
            sa.String(64),
            sa.ForeignKey("transactions.transaction_id"),
            nullable=False,
        ),
        sa.Column("risk_score", sa.Float, nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("reason_codes", sa.JSON, nullable=False),
        sa.Column("model_version", sa.String(128), nullable=False),
        sa.Column("latency_ms", sa.Float, nullable=False),
        sa.Column(
            "scored_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("risk_score >= 0 AND risk_score <= 1", name="ck_decisions_score"),
        sa.CheckConstraint("latency_ms >= 0", name="ck_decisions_latency"),
        sa.CheckConstraint(
            "decision IN ('APPROVE','MONITOR','REVIEW','CHALLENGE','BLOCK')",
            name="ck_decisions_decision",
        ),
    )
    op.create_index("ix_decisions_transaction", "fraud_decisions", ["transaction_id"])
    op.create_table(
        "fraud_labels",
        sa.Column("label_id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column(
            "transaction_id",
            sa.String(64),
            sa.ForeignKey("transactions.transaction_id"),
            nullable=False,
        ),
        sa.Column("is_fraud", sa.Boolean, nullable=False),
        sa.Column("label_source", sa.String(64), nullable=False),
        sa.Column(
            "labeled_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_labels_transaction", "fraud_labels", ["transaction_id"])


def downgrade() -> None:
    op.drop_table("fraud_labels")
    op.drop_table("fraud_decisions")
    op.drop_table("transactions")
