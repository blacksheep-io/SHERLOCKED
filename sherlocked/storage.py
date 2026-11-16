"""Local SQLite repository. Existing report rows are immutable and never replaced."""
import hashlib
import json
from pathlib import Path
import sqlite3
from contextlib import contextmanager
from .ingestion import validate_records,export_jsonl

from .paths import resource_path


class Store:
    def __init__(self,path=None):
        self.path = Path(path) if path is not None else resource_path('database')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS reports (report_id TEXT PRIMARY KEY, content_sha TEXT NOT NULL, body TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS reports_content ON reports(content_sha)')

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path,timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _hash(record):
        return hashlib.sha256(record['text'].encode('utf-8')).hexdigest()

    def initialize(self,seed_records):
        rows = validate_records(seed_records)
        with self._connect() as db:
            existing = {row[0]:json.loads(row[1]) for row in db.execute('SELECT report_id,body FROM reports')}
            for row in rows:
                if row['report_id'] in existing:
                    if existing[row['report_id']]['text']!=row['text']:
                        raise ValueError(f"Stored report {row['report_id']} differs from seed; existing data was preserved")
                    continue
                db.execute('INSERT INTO reports VALUES (?,?,?)',(row['report_id'],self._hash(row),json.dumps(row,ensure_ascii=False)))
        return len(rows)

    def list_reports(self):
        with self._connect() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT body FROM reports ORDER BY report_id')]

    def add_report(self,record):
        return self.import_reports([record])

    def import_reports(self,records):
        rows = validate_records(records)
        with self._connect() as db:
            existing = [json.loads(row[0]) for row in db.execute('SELECT body FROM reports')]
            ids = {r['report_id'] for r in existing}
            hashes = {self._hash(r):r['report_id'] for r in existing}
            families = {r['family_id']:r['split'] for r in existing if r.get('family_id')}
            for row in rows:
                if row['report_id'] in ids:
                    raise ValueError(f"Report ID {row['report_id']} already exists; no records were overwritten")
                digest = self._hash(row)
                if digest in hashes:
                    raise ValueError(f"Exact duplicate narrative already exists as {hashes[digest]}; no records imported")
                family = row.get('family_id')
                if family and family in families and families[family]!=row['split']:
                    raise ValueError(f'Family {family} would cross splits')
                ids.add(row['report_id']); hashes[digest] = row['report_id']
                if family:
                    families[family] = row['split']
            for row in rows:
                db.execute('INSERT INTO reports VALUES (?,?,?)',(row['report_id'],self._hash(row),json.dumps(row,ensure_ascii=False)))
        return len(rows)

    def export_jsonl(self):
        return export_jsonl(self.list_reports())

    def health(self):
        with self._connect() as db:
            return dict(status=db.execute('PRAGMA integrity_check').fetchone()[0],reports=db.execute('SELECT COUNT(*) FROM reports').fetchone()[0],path=str(self.path))
