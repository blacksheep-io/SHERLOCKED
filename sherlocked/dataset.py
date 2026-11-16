"""Deterministic synthetic fixtures. Family labels are evaluation-only."""
import hashlib
import json
import random
from pathlib import Path
from .paths import resource_path

SEED = 20261104
VERSION = 'synthetic-v1'


def generate(seed=SEED):
    rng = random.Random(seed)
    families = list(range(18))
    rng.shuffle(families)
    splits = {f: ('train' if i < 10 else 'dev' if i < 14 else 'test')
              for i, f in enumerate(families)}
    records = []
    for f in range(18):
        location = ['Lotus', 'River', 'Cedar', 'Moon', 'Garden', 'Hill'][f % 6]
        bn_location = ['পদ্ম', 'নদী', 'দেবদারু', 'চাঁদ', 'বাগান', 'পাহাড়'][f % 6]
        item, bn_item = [('bicycle', 'সাইকেল'), ('parcel', 'পার্সেল'),
                         ('lantern', 'লণ্ঠন')][f % 3]
        # Reused locations/items intentionally create misleading overlap.
        mark = ['striped', 'dotted', 'silver'][f // 6]
        bn_mark = ['ডোরাকাটা', 'ফোঁটাযুক্ত', 'রুপালি'][f // 6]
        narratives = [
            ('en', 'original', f'A {mark} {item} disappeared from {location} square. A witness saw a blue cart beside the gate.'),
            ('en', 'paraphrase', f'At the gate of {location} square, a blue trolley was observed. The missing object was a {mark} {item}.'),
            ('bn', 'translation', f'{bn_location} চত্বর থেকে একটি {bn_mark} {bn_item} হারিয়ে যায়। একজন সাক্ষী গেটের পাশে নীল ঠেলাগাড়ি দেখেন।'),
            ('mixed', 'mixed', f'{location} চত্বরে {mark} {item} missing. সাক্ষী blue cart দেখেছেন।'),
            ('mixed', 'transliteration', f'{location.lower()} chottore {mark} {item} hariye geche. Nil thelagari gate er pashe chilo.'),
        ]
        for i, (language, variant, text) in enumerate(narratives):
            if f % 2 == 0 and i == 1:
                text = f'A {mark} {item} was reported missing. Other details are unavailable.'
                variant = 'incomplete'
            records.append(dict(report_id=f'R{f:02d}-{i}', family_id=f'F{f:02d}',
                                split=splits[f], language=language, variant=variant,
                                text=text, fictional=True, source_id=f'synthetic:{VERSION}:R{f:02d}-{i}',
                                incident_type='missing_property', location=location if variant != 'incomplete' else None,
                                occurred_at=f'2025-01-{f+1:02d}T18:00:00+06:00',
                                entities=[], generator_version=VERSION))
    return records


def write_generated_files(files, overwrite=False):
    """Create outputs safely; preserve identical files and reject conflicting edits.

    JSON manifests are compared semantically so existing Windows line endings are
    preserved. Every conflict is checked before any output is created.
    """
    def equivalent(path, payload):
        existing = path.read_bytes()
        if existing == payload:
            return True
        if path.suffix == '.json':
            try:
                return json.loads(existing.decode('utf-8-sig')) == json.loads(payload.decode('utf-8'))
            except (ValueError, UnicodeError):
                return False
        return False
    if not overwrite:
        for path, payload in files.items():
            if path.exists() and not equivalent(path, payload):
                raise FileExistsError(f'{path} contains existing data; preserved. Choose a new directory or explicitly pass --overwrite.')
    for path, payload in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and equivalent(path, payload):
            continue
        if overwrite:
            import os
            import tempfile
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
            try:
                os.replace(temporary, path)
            finally:
                if temporary.exists():
                    temporary.unlink()
        else:
            with path.open('xb') as stream:
                stream.write(payload)


def write_dataset(root=None, overwrite=False):
    root = Path(root) if root is not None else resource_path('dataset')
    root.mkdir(parents=True, exist_ok=True)
    records = generate()
    payload = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in records)
    manifest = dict(seed=SEED, version=VERSION, count=len(records),
                    sha256=hashlib.sha256(payload.encode('utf-8')).hexdigest(),
                    family_splits={r['family_id']: r['split'] for r in records})
    write_generated_files({root / 'reports.jsonl': payload.encode('utf-8'),
                           root / 'manifest.json': json.dumps(manifest, indent=2).encode('utf-8')}, overwrite=overwrite)
    return manifest


def load(path=None):
    path = Path(path) if path is not None else resource_path('dataset') / 'reports.jsonl'
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--overwrite', action='store_true', help='Explicitly replace conflicting generated files; not used during setup')
    args = parser.parse_args()
    print(json.dumps(write_dataset(args.directory, overwrite=args.overwrite), indent=2))
