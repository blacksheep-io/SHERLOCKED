# Local fictional-demo access

The sign-in screen is a local demonstration gate for SHERLOCKED. It is not enterprise authentication, role-based authorization, evidence security or a production internet deployment.

Default public demonstration credentials:

- Username: `demo`
- Password: `sherlocked-demo`

The first initialization creates the account once. Later launches preserve its stored password, including any deliberate password change. The default password is public by design, not a secret or a security guarantee.

## Separate portable storage

Access records live in `local_access.sqlite3` under the configured dataset directory, normally `data/local_access.sqlite3`. This honors `SHERLOCKED_DATASET_DIR` and `configs/paths.json` through the existing portable path resolver. It is separate from `data/sherlocked.sqlite3`; the service refuses to use the configured report database as its access store. Initializing or changing access credentials never changes fictional reports, datasets, splits, embeddings or experiment results.

Only salted password hashes are persisted. Each password uses a fresh 32-byte random salt and PBKDF2-HMAC-SHA256 with 600,000 iterations. Stored hashes contain the algorithm, iteration count, salt and derived hash; no plaintext password is saved in the access database. Verification uses constant-time digest comparison. The documented public demo password necessarily exists in setup code/documentation so a new local copy can initialize itself.

## Failure and rate-limit behavior

`authenticate(username, password)` returns only `True` or `False`. Wrong passwords, unknown users, invalid inputs, blocked attempts and access-store errors do not expose account-specific error messages. Five failures for a normalized username within 60 seconds block further attempts for 60 seconds. The basic throttle is stored in the separate local database and survives application restart. Wait a full minute after the last blocking failure before retrying. Successful authentication clears that account's failure counter.

This is a basic local safeguard, not protection against a determined attacker who controls the host, changes the clock, deletes the access store or distributes guesses across usernames. It uses the desktop clock. Keep the application bound to localhost and use fictional information only.

## Service API

- `ensure_demo_account()` initializes the separate store and returns `demo`; an existing account is never reset.
- `authenticate(username, password)` checks the local account and throttle, returning a boolean.
- `change_password(username, current_password, new_password)` optionally updates the local hash after checking the current password. A new password must contain 12-1024 characters. It returns a boolean and does not reset other application data.
- `account_status()` returns non-secret storage/algorithm diagnostics without initializing the database.
- `access_database_path()` resolves the local access database path.

The Streamlit presentation owns sign-in/session/logout state. The service stores no authentication cookies or browser sessions. A signed-in session is not a human approval of an investigative relationship; results remain UNREVIEWED advisory suggestions.

## Limits and transfer

There is no network identity provider, MFA, recovery email, encrypted report storage, user-role system or tamper-resistant audit trail. Access hashes and throttle data are local SQLite records. Back them up separately if preserving a changed local credential; do not distribute your personal access store in a shared demo package. A new installation without the access store creates the documented public demo account. Copying a changed access store preserves that changed password rather than restoring the demo default.

Tests use isolated temporary access stores. They cover successful/failed login, random salts, constant-time comparison calls, restart-persistent throttling, password changes, plaintext absence and separation from report storage.
