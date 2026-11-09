"""Scope idempotency-key uniqueness to the organization.

`budget_reservations.idempotency` was globally UNIQUE while `invoice_key` beside it was
already UNIQUE(org, invoice_key). The key is client-supplied and free-form, so one tenant
could claim a guessable natural key such as 'INV-2026-001' and permanently prevent any
other tenant from executing a payment under that key. A system whose premise is tenant
isolation should not let one tenant reach another's execution path at all.

Rebuilding this table is safe: nothing references budget_reservations, so the DROP that
batch mode performs does not run into a foreign key. (Revision 0003 could not use batch
mode for exactly the opposite reason.)
"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


NEW_TABLE = """
CREATE TABLE budget_reservations_new (
	id VARCHAR NOT NULL,
	org VARCHAR NOT NULL,
	mandate_id VARCHAR NOT NULL,
	transaction_id VARCHAR NOT NULL,
	idempotency VARCHAR NOT NULL,
	invoice_key VARCHAR NOT NULL,
	amount INTEGER NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (transaction_id),
	UNIQUE (org, invoice_key),
	CONSTRAINT uq_reservation_org_idempotency UNIQUE (org, idempotency),
	FOREIGN KEY(org) REFERENCES organizations (id),
	FOREIGN KEY(mandate_id) REFERENCES mandates (id),
	FOREIGN KEY(transaction_id) REFERENCES records (id)
)
"""

COLUMNS = 'id, org, mandate_id, transaction_id, idempotency, invoice_key, amount'


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    names = {uc.get('name') for uc in inspector.get_unique_constraints('budget_reservations')}
    if 'uq_reservation_org_idempotency' in names:
        return

    # The old global constraint guaranteed uniqueness across every tenant, so a per-tenant
    # duplicate cannot exist. Checked rather than assumed, because the rebuild is one-way.
    dupes = bind.execute(sa.text(
        'SELECT org, idempotency, COUNT(*) c FROM budget_reservations '
        'GROUP BY org, idempotency HAVING c > 1')).fetchall()
    if dupes:
        raise RuntimeError('budget_reservations has duplicate (org, idempotency) rows: %r' % (dupes[:5],))

    if bind.dialect.name == 'sqlite':
        # Not batch_alter_table: it reflects the existing table and faithfully reproduces the
        # very UNIQUE(idempotency) this revision exists to remove. The table is rebuilt
        # explicitly so the resulting DDL is exactly what the model declares. Safe to drop
        # because no table references budget_reservations.
        op.execute(NEW_TABLE)
        op.execute('INSERT INTO budget_reservations_new (%s) SELECT %s FROM budget_reservations' % (COLUMNS, COLUMNS))
        op.execute('DROP TABLE budget_reservations')
        op.execute('ALTER TABLE budget_reservations_new RENAME TO budget_reservations')
        op.create_index('ix_budget_reservations_org', 'budget_reservations', ['org'])
    else:
        for uc in inspector.get_unique_constraints('budget_reservations'):
            if uc['column_names'] == ['idempotency'] and uc.get('name'):
                op.drop_constraint(uc['name'], 'budget_reservations', type_='unique')
        op.create_unique_constraint('uq_reservation_org_idempotency', 'budget_reservations',
                                    ['org', 'idempotency'])


def downgrade():
    raise RuntimeError('Audit-preserving migration: restore a reviewed backup instead of destructive downgrade')
