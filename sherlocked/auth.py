"""Local fictional-demo access gate, separate from investigative report storage."""
from contextlib import contextmanager
import hashlib
import hmac
import logging
import re
import secrets
import sqlite3
import time
from .paths import resource_path

PBKDF2_ITERATIONS=600_000
MAX_FAILURES=5
WINDOW_SECONDS=60
LOCK_SECONDS=60
DEMO_USERNAME='demo'
DEMO_PASSWORD='sherlocked-demo'  # Public fictional-demo credential; never saved as plaintext.
_DUMMY_SALT=secrets.token_bytes(32)
logger=logging.getLogger(__name__)


def access_database_path():
    """Portable access store; never reuse the report/evidence database."""
    path=(resource_path('dataset')/'local_access.sqlite3').resolve()
    if path==resource_path('database').resolve():
        raise ValueError('The local access database must differ from the report database')
    return path


@contextmanager
def _connect():
    path=access_database_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    connection=sqlite3.connect(path,timeout=10)
    try:
        with connection:
            connection.execute('CREATE TABLE IF NOT EXISTS local_accounts (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL)')
            connection.execute('CREATE TABLE IF NOT EXISTS local_login_limits (subject TEXT PRIMARY KEY, failures INTEGER NOT NULL, window_started REAL NOT NULL, blocked_until REAL NOT NULL)')
        yield connection
    finally:
        connection.close()


def _username(value):
    if not isinstance(value,str): return None
    value=value.strip().casefold()
    return value if re.fullmatch(r'[a-z0-9_.-]{1,64}',value) else None


def _password_valid(value):
    return isinstance(value,str) and 1<=len(value)<=1024


def _hash_password(password):
    if not _password_valid(password): raise ValueError('Password length must be 1-1024 characters')
    salt=secrets.token_bytes(32)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),salt,PBKDF2_ITERATIONS)
    return f'pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}'


def _verify_password(password,encoded):
    # Missing/malformed account records still perform a password derivation and compare.
    valid=False;salt=_DUMMY_SALT;expected=bytes(32);iterations=PBKDF2_ITERATIONS
    try:
        algorithm,cost,salt_text,digest_text=encoded.split('$')
        proposed_cost=int(cost);proposed_salt=bytes.fromhex(salt_text);proposed_digest=bytes.fromhex(digest_text)
        if algorithm=='pbkdf2_sha256' and 100_000<=proposed_cost<=2_000_000 and len(proposed_salt)==32 and len(proposed_digest)==32:
            salt,expected,iterations=proposed_salt,proposed_digest,proposed_cost;valid=True
    except (AttributeError,TypeError,ValueError): pass
    candidate=password if _password_valid(password) else ''
    actual=hashlib.pbkdf2_hmac('sha256',candidate.encode('utf-8'),salt,iterations)
    equal=hmac.compare_digest(actual,expected)
    return bool(valid and _password_valid(password) and equal)


def ensure_demo_account():
    """Create the public demo account once. Existing hashes/passwords are preserved."""
    with _connect() as connection:
        if connection.execute('SELECT 1 FROM local_accounts WHERE username=?',(DEMO_USERNAME,)).fetchone():
            return DEMO_USERNAME
        encoded=_hash_password(DEMO_PASSWORD)
        now=time.time()
        with connection:
            connection.execute('INSERT OR IGNORE INTO local_accounts VALUES (?,?,?,?)',(DEMO_USERNAME,encoded,now,now))
    return DEMO_USERNAME


def authenticate(username,password):
    """Return only success/failure, including throttled or unavailable local access.

    Five failed attempts for a normalized username within one minute trigger a
    one-minute lock. The basic local throttle persists across app restarts.
    """
    try:
        ensure_demo_account()
        normalized=_username(username)
        subject=hashlib.sha256((normalized or '<invalid-user>').encode('utf-8')).hexdigest()
        now=time.time()
        with _connect() as connection:
            with connection:
                connection.execute('BEGIN IMMEDIATE')
                limit=connection.execute('SELECT failures,window_started,blocked_until FROM local_login_limits WHERE subject=?',(subject,)).fetchone()
                if limit and limit[2]>now: return False
                failures,started=(limit[0],limit[1]) if limit and now-limit[1]<WINDOW_SECONDS else (0,now)
                row=connection.execute('SELECT password_hash FROM local_accounts WHERE username=?',(normalized,)).fetchone() if normalized else None
                valid=_verify_password(password,row[0] if row else None)
                if row and valid:
                    connection.execute('DELETE FROM local_login_limits WHERE subject=?',(subject,))
                    return True
                failures+=1
                blocked=now+LOCK_SECONDS if failures>=MAX_FAILURES else 0
                connection.execute('INSERT INTO local_login_limits VALUES (?,?,?,?) ON CONFLICT(subject) DO UPDATE SET failures=excluded.failures,window_started=excluded.window_started,blocked_until=excluded.blocked_until',(subject,failures,started,blocked))
                return False
    except (sqlite3.Error,OSError,ValueError) as error:
        logger.error('Local sign-in unavailable (%s); access denied',type(error).__name__)
        return False


def change_password(username,current_password,new_password):
    """Optional local credential update; never resets report data or existing users."""
    if not isinstance(new_password,str) or not 12<=len(new_password)<=1024: return False
    if not authenticate(username,current_password): return False
    normalized=_username(username)
    try:
        with _connect() as connection:
            with connection:
                connection.execute('BEGIN IMMEDIATE')
                row=connection.execute('SELECT password_hash FROM local_accounts WHERE username=?',(normalized,)).fetchone()
                if not row or not _verify_password(current_password,row[0]): return False
                connection.execute('UPDATE local_accounts SET password_hash=?,updated_at=? WHERE username=?',(_hash_password(new_password),time.time(),normalized))
        return True
    except (sqlite3.Error,OSError,ValueError):
        logger.error('Local credential update unavailable; no change saved')
        return False


def account_status():
    """Non-secret local status for setup diagnostics; does not initialize the store."""
    path=access_database_path()
    return dict(initialized=path.is_file(),database_path=str(path),account=DEMO_USERNAME,
                algorithm='PBKDF2-SHA256',iterations=PBKDF2_ITERATIONS,local_demo_only=True)
