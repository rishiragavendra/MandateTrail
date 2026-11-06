"""Canonical schema v1: NFC strings, sorted keys, UTF-8, integers only, explicit nulls."""
import base64
import hashlib
import json
import os
import secrets
import unicodedata
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

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

def load_key():
    path = Path(os.environ.get('SIGNING_KEY_PATH', os.path.join(os.environ.get('DATA_DIR', 'data'), 'signing.key')))
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

KEY = load_key()
PUBLIC = KEY.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
KEY_ID = hashlib.sha256(bytes.fromhex(PUBLIC)).hexdigest()[:16]
def sign(value): return base64.b64encode(KEY.sign(canonical(value))).decode()
def verify(value, signature):
    try:
        KEY.public_key().verify(base64.b64decode(signature, validate=True), canonical(value))
        return True
    except Exception: return False

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + '$' + hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
def password_ok(password, stored):
    try: return secrets.compare_digest(password_hash(password, stored.split('$')[0]), stored)
    except Exception: return False
