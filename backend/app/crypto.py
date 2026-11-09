"""Canonical schema v1: NFC strings, sorted keys, UTF-8, integers only, explicit nulls.

Signing keys are separated by purpose. One key for mandates, approvals and the audit
chain meant that anyone who could read that single file could forge all three at once,
and the chain could then be rewritten undetectably. Separate keys limit what a single
compromised key can rewrite.

A key that was previously used for everything is still loaded, read-only, as a legacy
verifier: records signed before the split must keep verifying, which is exactly how key
rotation works in practice. Nothing new is ever signed with it.
"""
import base64
import hashlib
import json
import os
import secrets
import unicodedata
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

PURPOSES = ('mandate', 'approval', 'audit')

def normalize(value):
    if isinstance(value, float): raise ValueError('Floating point is forbidden in signed objects')
    if isinstance(value, str): return unicodedata.normalize('NFC', value)
    if isinstance(value, dict):
        result = {normalize(k): normalize(v) for k, v in value.items()}
        if len(result) != len(value): raise ValueError('Duplicate normalized keys')
        return result
    if isinstance(value, list): return [normalize(v) for v in value]
    return value

def canonical(value): return json.dumps(normalize(value), sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
def digest(value): return hashlib.sha256(canonical(value)).hexdigest()

def data_dir(): return os.environ.get('DATA_DIR', 'data')
def key_dir(): return Path(os.environ.get('KEY_DIR', os.path.join(data_dir(), 'keys')))

def _read_or_create(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        key = Ed25519PrivateKey.generate()
        try:
            with path.open('xb') as f:
                f.write(key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()))
            try: path.chmod(0o600)
            except OSError: pass
        except FileExistsError: pass
    return Ed25519PrivateKey.from_private_bytes(path.read_bytes())

def _read_only(path):
    """A pre-split key, if one exists. Never created, never used to sign."""
    return Ed25519PrivateKey.from_private_bytes(path.read_bytes()) if path.exists() else None

def _public_hex(key): return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
def _key_id(key): return hashlib.sha256(bytes.fromhex(_public_hex(key))).hexdigest()[:16]

KEYS = {purpose: _read_or_create(key_dir() / (purpose + '.key')) for purpose in PURPOSES}
LEGACY_KEY = _read_only(Path(os.environ.get('SIGNING_KEY_PATH', os.path.join(data_dir(), 'signing.key'))))

PUBLIC_KEYS = {purpose: _public_hex(key) for purpose, key in KEYS.items()}
KEY_IDS = {purpose: _key_id(key) for purpose, key in KEYS.items()}
LEGACY_KEY_ID = _key_id(LEGACY_KEY) if LEGACY_KEY else None

# Historical aliases, kept so existing call sites and the settings screen keep working.
PUBLIC = PUBLIC_KEYS['mandate']
KEY_ID = KEY_IDS['mandate']

def sign(value, purpose='mandate'):
    if purpose not in KEYS: raise ValueError('Unknown signing purpose: ' + str(purpose))
    return base64.b64encode(KEYS[purpose].sign(canonical(value))).decode()

def _verify_with(key, value, signature):
    try:
        key.public_key().verify(base64.b64decode(signature, validate=True), canonical(value))
        return True
    except Exception:
        return False

def verify(value, signature, purpose='mandate'):
    """Accept this purpose's key, or the pre-split key for records that predate it."""
    if _verify_with(KEYS[purpose], value, signature): return True
    return bool(LEGACY_KEY) and _verify_with(LEGACY_KEY, value, signature)

def sign_checkpoint(chain_hash):
    """Audit signatures cover the key id, so verification must try each id with its own key."""
    return sign({'hash': chain_hash, 'key_id': KEY_IDS['audit']}, 'audit')

def verify_checkpoint(chain_hash, signature):
    candidates = [(KEY_IDS['audit'], KEYS['audit'])]
    if LEGACY_KEY: candidates.append((LEGACY_KEY_ID, LEGACY_KEY))
    return any(_verify_with(key, {'hash': chain_hash, 'key_id': key_id}, signature)
               for key_id, key in candidates)

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + '$' + hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
def password_ok(password, stored):
    try: return secrets.compare_digest(password_hash(password, stored.split('$')[0]), stored)
    except Exception: return False
