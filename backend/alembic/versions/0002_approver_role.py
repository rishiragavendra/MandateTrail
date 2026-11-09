"""Bind the approver's role into the signed approval object.

Revision 0001 builds tables with `create_all` from the live models, so on a fresh
database this column already exists. On a database stamped at 0001 before this
change it does not. Add it only when it is absent so both paths reach the same schema.
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {c['name'] for c in sa.inspect(bind).get_columns('approvals')}
    if 'approver_role' not in columns:
        op.add_column('approvals', sa.Column('approver_role', sa.String(), nullable=True))


def downgrade():
    raise RuntimeError('Audit-preserving migration: restore a reviewed backup instead of destructive downgrade')
