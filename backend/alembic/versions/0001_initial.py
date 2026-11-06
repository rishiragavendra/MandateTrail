"""Initial relational schema and append-only audit triggers."""
from alembic import op
from app.db import Base
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None
def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind)
    if bind.dialect.name == 'sqlite':
        op.execute("CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit append only'); END")
        op.execute("CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit append only'); END")
    elif bind.dialect.name == 'postgresql':
        op.execute("CREATE FUNCTION audit_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'audit append only'; END; $$")
        op.execute("CREATE TRIGGER audit_immutable BEFORE UPDATE OR DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION audit_immutable()")
def downgrade():
    raise RuntimeError('Audit-preserving migration: restore a reviewed backup instead of destructive downgrade')
