"""Initial relational schema and append-only audit triggers.

Written as explicit DDL rather than `Base.metadata.create_all`. Creating tables from
the live models means a fresh database always gets TODAY's schema, so the next
additive migration finds its column already present and fails, while an existing
database does not have it. Spelling the original schema out here keeps both paths
converging on the same result: 0001 builds the original tables, later revisions alter them.

This revision deliberately omits approvals.approver_role; revision 0002 adds it.
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('org', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password', sa.Text(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['org'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_org', 'users', ['org'])
    op.create_table(
        'records',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('org', sa.String(), nullable=False),
        sa.Column('kind', sa.String(), nullable=False),
        sa.Column('parent', sa.String(), nullable=True),
        sa.Column('created', sa.String(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['org'], ['organizations.id']),
        sa.ForeignKeyConstraint(['parent'], ['records.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_records_org', 'records', ['org'])
    op.create_index('ix_records_kind', 'records', ['kind'])
    op.create_index('ix_records_parent', 'records', ['parent'])
    op.create_table(
        'mandates',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('org', sa.String(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('signature', sa.Text(), nullable=False),
        sa.Column('digest', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('spent', sa.Integer(), nullable=False),
        sa.Column('created', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['org'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mandates_org', 'mandates', ['org'])
    op.create_table(
        'approvals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('org', sa.String(), nullable=False),
        sa.Column('transaction_id', sa.String(), nullable=False),
        sa.Column('digest', sa.String(), nullable=False),
        sa.Column('nonce', sa.String(), nullable=False),
        sa.Column('expires', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('approver', sa.String(), nullable=True),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['approver'], ['users.id']),
        sa.ForeignKeyConstraint(['org'], ['organizations.id']),
        sa.ForeignKeyConstraint(['transaction_id'], ['records.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nonce'),
        sa.UniqueConstraint('transaction_id'),
    )
    op.create_index('ix_approvals_org', 'approvals', ['org'])
    op.create_table(
        'budget_reservations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('org', sa.String(), nullable=False),
        sa.Column('mandate_id', sa.String(), nullable=False),
        sa.Column('transaction_id', sa.String(), nullable=False),
        sa.Column('idempotency', sa.String(), nullable=False),
        sa.Column('invoice_key', sa.String(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['mandate_id'], ['mandates.id']),
        sa.ForeignKeyConstraint(['org'], ['organizations.id']),
        sa.ForeignKeyConstraint(['transaction_id'], ['records.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency'),
        sa.UniqueConstraint('transaction_id'),
        sa.UniqueConstraint('org', 'invoice_key'),
    )
    op.create_index('ix_budget_reservations_org', 'budget_reservations', ['org'])
    op.create_table(
        'audit_events',
        sa.Column('seq', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('org', sa.String(), nullable=False),
        sa.Column('workflow', sa.String(), nullable=True),
        sa.Column('content', sa.JSON(), nullable=False),
        sa.Column('previous', sa.String(), nullable=False),
        sa.Column('digest', sa.String(), nullable=False),
        sa.Column('signature', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['org'], ['organizations.id']),
        sa.PrimaryKeyConstraint('seq'),
        sa.UniqueConstraint('id'),
    )
    op.create_index('ix_audit_events_org', 'audit_events', ['org'])
    op.create_index('ix_audit_events_workflow', 'audit_events', ['workflow'])

    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        op.execute("CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit append only'); END")
        op.execute("CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit append only'); END")
    elif bind.dialect.name == 'postgresql':
        op.execute("CREATE FUNCTION audit_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'audit append only'; END; $$")
        op.execute("CREATE TRIGGER audit_immutable BEFORE UPDATE OR DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION audit_immutable()")


def downgrade():
    raise RuntimeError('Audit-preserving migration: restore a reviewed backup instead of destructive downgrade')
