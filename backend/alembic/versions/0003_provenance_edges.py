"""Promote provenance chain pointers from JSON into enforced foreign keys.

A provenance record's chain was held entirely in its JSON `data`: `source_id`,
`parent_provenance` and `session_id`. The database could not see those edges, so
nothing stopped a dangling or cross-table pointer from being written; it only
surfaced later, at read time, as a failed lookup in the middle of a policy decision.

These columns carry the same edges where the database can enforce them. The JSON keys
stay for wire compatibility, and the verifier in core.provenance_verify cross-checks
the two against each other, plus the organization and kind constraints a foreign key
cannot express. Columns are nullable: rows written before this revision keep NULL and
are reported as legacy by the verifier rather than silently treated as intact.
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

NEW_COLUMNS = ('source_ref', 'prior_ref', 'session_ref')


def _fk_columns(bind):
    """Columns of `records` that already carry a foreign key to records.id."""
    return {fk['constrained_columns'][0]
            for fk in sa.inspect(bind).get_foreign_keys('records')
            if fk['referred_table'] == 'records' and len(fk['constrained_columns']) == 1}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {c['name'] for c in inspector.get_columns('records')}
    constrained = _fk_columns(bind)
    indexes = {i['name'] for i in inspector.get_indexes('records')}

    # A column present without its foreign key is the residue of a half-applied attempt.
    # It would silently behave like the unenforced JSON pointer this revision exists to
    # replace, so stop rather than leave an edge that only looks enforced.
    unenforced = [n for n in NEW_COLUMNS if n in existing and n not in constrained]
    if unenforced:
        raise RuntimeError(
            'records.%s exists without a foreign key to records.id, which means a previous '
            'run of this revision was interrupted. SQLite cannot attach the constraint to an '
            'existing column without rebuilding the table. Restore the pre-0003 backup and '
            're-run this revision.' % ', records.'.join(unenforced))

    for name in NEW_COLUMNS:
        if name in existing:
            continue
        if bind.dialect.name == 'sqlite':
            # One statement, so the column and its constraint arrive together. SQLite
            # allows REFERENCES on ADD COLUMN precisely because the default is NULL.
            # Batch mode is wrong here: it rebuilds `records`, and the DROP TABLE that
            # requires fails while approvals and budget_reservations reference it.
            op.execute('ALTER TABLE records ADD COLUMN %s VARCHAR REFERENCES records(id)' % name)
        else:
            op.add_column('records', sa.Column(name, sa.String(), nullable=True))
            op.create_foreign_key('fk_records_' + name, 'records', 'records', [name], ['id'])
        if ('ix_records_' + name) not in indexes:
            op.create_index('ix_records_' + name, 'records', [name])


def downgrade():
    raise RuntimeError('Audit-preserving migration: restore a reviewed backup instead of destructive downgrade')
