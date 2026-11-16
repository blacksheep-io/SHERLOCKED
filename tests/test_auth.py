"""Local authentication behavior against isolated temporary access stores."""
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sherlocked import auth


class LocalAuthTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.root=Path(self.directory.name)
        self.paths=patch('sherlocked.auth.resource_path',side_effect=lambda key:self.root/'reports.sqlite3' if key=='database' else self.root)
        self.paths.start()
    def tearDown(self):
        self.paths.stop();self.directory.cleanup()
    def hash_from_store(self):
        with closing(sqlite3.connect(auth.access_database_path())) as connection:
            return connection.execute('SELECT password_hash FROM local_accounts WHERE username=?',('demo',)).fetchone()[0]

    def test_demo_login_and_idempotent_storage_without_plaintext_or_report_db(self):
        auth.ensure_demo_account();first=self.hash_from_store()
        auth.ensure_demo_account()
        self.assertEqual(first,self.hash_from_store())
        self.assertTrue(auth.authenticate('  DEMO  ','sherlocked-demo'))
        self.assertFalse(auth.authenticate('demo','wrong'))
        self.assertNotIn(b'sherlocked-demo',auth.access_database_path().read_bytes())
        self.assertFalse((self.root/'reports.sqlite3').exists())
        self.assertEqual(auth.access_database_path().name,'local_access.sqlite3')

    def test_salted_hashes_and_constant_time_verification(self):
        first=auth._hash_password('Example fictional password')
        second=auth._hash_password('Example fictional password')
        self.assertNotEqual(first,second)
        with patch('sherlocked.auth.hmac.compare_digest',wraps=auth.hmac.compare_digest) as compare:
            self.assertTrue(auth._verify_password('Example fictional password',first))
            self.assertFalse(auth._verify_password('different',first))
            self.assertFalse(auth._verify_password('different','malformed hash'))
            self.assertEqual(compare.call_count,3)

    def test_generic_failure_and_persistent_rate_limit_then_recovery(self):
        with patch('sherlocked.auth.time.time',return_value=1000):
            for _ in range(auth.MAX_FAILURES): self.assertIs(auth.authenticate('demo','wrong'),False)
            self.assertIs(auth.authenticate('demo','sherlocked-demo'),False)
            self.assertIs(auth.authenticate('unknown','wrong'),False)
            self.assertIs(auth.authenticate(None,None),False)
        # Separate call/connection, persisted throttle; correct credentials remain blocked.
        with patch('sherlocked.auth.time.time',return_value=1030):
            self.assertFalse(auth.authenticate('demo','sherlocked-demo'))
        with patch('sherlocked.auth.time.time',return_value=1061):
            self.assertTrue(auth.authenticate('demo','sherlocked-demo'))

    def test_credential_change_requires_current_password_and_survives_initialization(self):
        auth.ensure_demo_account()
        self.assertFalse(auth.change_password('demo','incorrect','another-long-password'))
        self.assertFalse(auth.change_password('demo','sherlocked-demo','short'))
        self.assertTrue(auth.change_password('demo','sherlocked-demo','another-long-password'))
        changed=self.hash_from_store()
        auth.ensure_demo_account()
        self.assertEqual(changed,self.hash_from_store())
        self.assertFalse(auth.authenticate('demo','sherlocked-demo'))
        self.assertTrue(auth.authenticate('demo','another-long-password'))

    def test_access_store_cannot_be_configured_as_report_store(self):
        with patch('sherlocked.auth.resource_path',side_effect=lambda key:self.root/'local_access.sqlite3' if key=='database' else self.root):
            with self.assertRaises(ValueError): auth.ensure_demo_account()
            self.assertFalse(auth.authenticate('demo','sherlocked-demo'))
        self.assertFalse(auth.access_database_path().exists())


if __name__=='__main__': unittest.main()
