"""add country and US fields

Revision ID: a2b3c4d5e6f7
Revises: 47d91705494a
Create Date: 2026-02-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "47d91705494a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # User table: add country and filing_status
    op.add_column("users", sa.Column("country", sa.String(5), nullable=False, server_default="IN"))
    op.add_column("users", sa.Column("filing_status", sa.String(30), nullable=True))

    # Loan table: add US tax deduction fields
    op.add_column("loans", sa.Column("eligible_mortgage_deduction", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("loans", sa.Column("eligible_student_loan_deduction", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("loans", "eligible_student_loan_deduction")
    op.drop_column("loans", "eligible_mortgage_deduction")
    op.drop_column("users", "filing_status")
    op.drop_column("users", "country")
