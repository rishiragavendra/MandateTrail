"""Relational storage. PostgreSQL primary; SQLite supports portable local demos."""
import os
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine, String, Text, Integer, ForeignKey, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import JSON

def uid(): return str(uuid4())
def now(): return datetime.now(timezone.utc).isoformat()

class Base(DeclarativeBase): pass

class Organization(Base):
    __tablename__ = 'organizations'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    org: Mapped[str] = mapped_column(ForeignKey('organizations.id'), index=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    password: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String)

class Record(Base):
    """Typed domain documents, with organization scope and relational associations."""
    __tablename__ = 'records'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    org: Mapped[str] = mapped_column(ForeignKey('organizations.id'), index=True)
    kind: Mapped[str] = mapped_column(String, index=True)
    parent: Mapped[str | None] = mapped_column(ForeignKey('records.id'), nullable=True, index=True)
    created: Mapped[str] = mapped_column(String, default=now)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    # Provenance chain edges the database enforces. The same ids remain in `data` for
    # wire compatibility; core.provenance_verify cross-checks the two, and the
    # organization and kind constraints a foreign key cannot express. NULL means the
    # row predates revision 0003, not that it has no edge.
    source_ref: Mapped[str | None] = mapped_column(ForeignKey('records.id'), nullable=True, index=True)
    prior_ref: Mapped[str | None] = mapped_column(ForeignKey('records.id'), nullable=True, index=True)
    session_ref: Mapped[str | None] = mapped_column(ForeignKey('records.id'), nullable=True, index=True)

class Mandate(Base):
    __tablename__ = 'mandates'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    org: Mapped[str] = mapped_column(ForeignKey('organizations.id'), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    signature: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default='ACTIVE')
    spent: Mapped[int] = mapped_column(Integer, default=0)
    created: Mapped[str] = mapped_column(String, default=now)

class Approval(Base):
    __tablename__ = 'approvals'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    org: Mapped[str] = mapped_column(ForeignKey('organizations.id'), index=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey('records.id'), unique=True)
    digest: Mapped[str] = mapped_column(String)
    nonce: Mapped[str] = mapped_column(String, unique=True)
    expires: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default='PENDING')
    approver: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    approver_role: Mapped[str | None] = mapped_column(String, nullable=True)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)

class Reservation(Base):
    __tablename__ = 'budget_reservations'
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    org: Mapped[str] = mapped_column(ForeignKey('organizations.id'), index=True)
    mandate_id: Mapped[str] = mapped_column(ForeignKey('mandates.id'))
    transaction_id: Mapped[str] = mapped_column(ForeignKey('records.id'), unique=True)
    # Scoped to the organization, like invoice_key beside it. A global constraint would let
    # one tenant claim a guessable key and block another tenant's execution permanently.
    idempotency: Mapped[str] = mapped_column(String)
    invoice_key: Mapped[str] = mapped_column(String)
    amount: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint('org', 'invoice_key'),
                      UniqueConstraint('org', 'idempotency', name='uq_reservation_org_idempotency'))

class Audit(Base):
    __tablename__ = 'audit_events'
    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String, unique=True, default=uid)
    org: Mapped[str] = mapped_column(ForeignKey('organizations.id'), index=True)
    workflow: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    content: Mapped[dict] = mapped_column(JSON)
    previous: Mapped[str] = mapped_column(String)
    digest: Mapped[str] = mapped_column(String)
    signature: Mapped[str] = mapped_column(Text)

DATA_DIR = os.environ.get('DATA_DIR', 'data')
os.makedirs(DATA_DIR, exist_ok=True)
URL = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.abspath(os.path.join(DATA_DIR, 'mandatetrail.db')).replace('\\', '/'))
engine = create_engine(URL, connect_args={'check_same_thread': False, 'timeout': 30} if URL.startswith('sqlite') else {}, pool_pre_ping=True)
if URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def sqlite_settings(conn, _):
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA journal_mode=WAL')
SessionLocal = sessionmaker(engine, expire_on_commit=False)
