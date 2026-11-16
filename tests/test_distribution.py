import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/build_distribution.py'
spec=importlib.util.spec_from_file_location('distribution_builder',SCRIPT)
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class DistributionTests(unittest.TestCase):
    def make_source(self,root):
        files=['app.py','START_SHERLOCKED.bat','SETUP_SHERLOCKED.bat','README.md','requirements.txt',
               'configs/model.json','configs/paths.example.json','sherlocked/__init__.py']
        files += [f'data/{name}' for name in builder.DATA_FILES]
        for name in files:
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'unit-test source fixture')

    def test_source_allowlist_and_sha256_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.make_source(root)
            for name in ['.env','configs/app.json','configs/paths.json','data/sherlocked.sqlite3','logs/error.log',
                         '.venv/Scripts/python.exe','sherlocked/__pycache__/code.pyc','models/private.bin',
                         'cache/embedding.npy','backups/original.zip','results/private.json','.streamlit/secrets.toml']:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'private excluded data')
            for name in ['assets/interface/sherlocked.css','assets/branding/README.md','assets/illustrative/ashford_manor.json','assets/illustrative/ashford_manor_plan.svg']:
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'local product presentation asset')
            result=builder.build_distribution(root/'source.zip',root=root)
            with zipfile.ZipFile(result['path']) as archive:
                names=set(archive.namelist())
                self.assertIn('SHERLOCKED/app.py',names)
                self.assertIn('SHERLOCKED/assets/interface/sherlocked.css',names)
                self.assertIn('SHERLOCKED/assets/branding/README.md',names)
                self.assertIn('SHERLOCKED/assets/illustrative/ashford_manor.json',names)
                self.assertIn('SHERLOCKED/assets/illustrative/ashford_manor_plan.svg',names)
                self.assertIn('SHERLOCKED/data/reports.jsonl',names)
                self.assertEqual(len([name for name in names if '/data/' in name]),6)
                self.assertFalse(any('private' in name or '/.venv/' in name or '.sqlite3' in name or 'secrets.toml' in name for name in names))
                self.assertNotIn('SHERLOCKED/configs/app.json',names)
                self.assertNotIn('SHERLOCKED/configs/paths.json',names)
                manifest=json.loads(archive.read('SHERLOCKED/DISTRIBUTION_MANIFEST.json'))
                self.assertTrue(manifest['requires_internet_for_first_dependency_setup'])
                self.assertFalse(manifest['dependencies_included'])
                for file in manifest['files']:
                    self.assertEqual(hashlib.sha256(archive.read(file['path'])).hexdigest(),file['sha256'])
                    self.assertEqual(len(archive.read(file['path'])),file['bytes'])

    def test_deterministic_output_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.make_source(root)
            first=builder.build_distribution(root/'one.zip',root=root)
            second=builder.build_distribution(root/'two.zip',root=root)
            self.assertEqual(first['sha256'],second['sha256'])
            with self.assertRaises(FileExistsError):builder.build_distribution(root/'one.zip',root=root)
            self.assertEqual(hashlib.sha256((root/'one.zip').read_bytes()).hexdigest(),first['sha256'])

    def test_results_are_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);self.make_source(root)
            (root/'results/experiments').mkdir(parents=True)
            (root/'results/experiments/previous.json').write_text('{}')
            (root/'configs/frozen_research.json').write_text('{}')
            result=builder.build_distribution(root/'with-results.zip',root=root,include_results=True)
            with zipfile.ZipFile(result['path']) as archive:
                self.assertIn('SHERLOCKED/results/experiments/previous.json',archive.namelist())
                self.assertIn('SHERLOCKED/configs/frozen_research.json',archive.namelist())

    def test_model_assets_pin_and_cache_exclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            config=dict(model_id='intfloat/multilingual-e5-small',revision='a'*40,license='MIT',dimensions=384,local_directory='models/unit-model')
            (root/'configs').mkdir();(root/'configs/model.json').write_text(json.dumps(config))
            model=root/'models/unit-model'
            for name in builder.MODEL_FILES:
                path=model/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'isolated unit-test model fixture; not inference weights')
            (model/'sherlocked_model.json').write_text(json.dumps(config))
            (model/'.cache/huggingface').mkdir(parents=True);(model/'.cache/huggingface/private.token').write_text('secret')
            result=builder.build_distribution(root/'model.zip',root=root,model_assets=True)
            with zipfile.ZipFile(result['path']) as archive:
                self.assertIn('SHERLOCKED/models/unit-model/model.safetensors',archive.namelist())
                self.assertIn('SHERLOCKED/models/unit-model/LICENSE-MIT.txt',archive.namelist())
                self.assertIn('SHERLOCKED/MODEL_DISTRIBUTION_MANIFEST.json',archive.namelist())
                self.assertNotIn('SHERLOCKED/DISTRIBUTION_MANIFEST.json',archive.namelist())
                self.assertFalse(any('.cache' in name for name in archive.namelist()))
            (model/'sherlocked_model.json').write_text(json.dumps(dict(config,revision='b'*40)))
            with self.assertRaises(ValueError):builder.build_distribution(root/'wrong.zip',root=root,model_assets=True)

    def test_public_brand_assets_ship_without_generated_or_private_material(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.make_source(root)
            public=['assets/branding/sherlocked-noir.svg','assets/branding/sherlocked-noir.png',
                    'docs/PUBLIC_GUIDE.md','docs/screenshots/research-paper.png']
            excluded=['docs/proposal_work/render/page-1.png','docs/Proposal_Work/references.md',
                      'assets/.cache/render.png','assets/node_modules/vendor.png',
                      'assets/secrets/tokens.json','assets/Private/portrait.png',
                      'assets/branding/credentials.json','assets/branding/secrets.toml']
            for name in public+excluded:
                path=root/name; path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b'isolated distribution fixture')
            result=builder.build_distribution(root/'source.zip',root=root)
            with zipfile.ZipFile(result['path']) as archive:
                names=set(archive.namelist())
                for name in public: self.assertIn('SHERLOCKED/'+name,names)
                for name in excluded: self.assertNotIn('SHERLOCKED/'+name,names)

    def test_source_and_model_merge_without_collisions_and_preserve_both_manifests(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.make_source(root)
            config=dict(model_id='intfloat/multilingual-e5-small',revision='a'*40,license='MIT',
                        dimensions=384,local_directory='models/unit-model')
            (root/'configs/model.json').write_text(json.dumps(config),encoding='utf-8')
            model=root/'models/unit-model'
            for name in builder.MODEL_FILES:
                path=model/name; path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(('isolated test asset: '+name).encode('utf-8'))
            (model/'sherlocked_model.json').write_text(json.dumps(config),encoding='utf-8')
            for name in ['.env','configs/app.json','configs/paths.json','data/sherlocked.sqlite3',
                         '.venv/Scripts/python.exe','models/unit-model/.cache/huggingface/token.json',
                         'cache/embedding.npy','logs/session.log']:
                path=root/name; path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b'private material that must never appear in either package')
            source=builder.build_distribution(root/'source.zip',root=root)
            assets=builder.build_distribution(root/'model.zip',root=root,model_assets=True)
            merged=root/'merged'; merged.mkdir()
            manifests=[]
            with zipfile.ZipFile(source['path']) as source_zip,zipfile.ZipFile(assets['path']) as model_zip:
                source_names=set(source_zip.namelist()); model_names=set(model_zip.namelist())
                self.assertTrue(source_names.isdisjoint(model_names),source_names&model_names)
                self.assertIn('SHERLOCKED/DISTRIBUTION_MANIFEST.json',source_names)
                self.assertIn('SHERLOCKED/MODEL_DISTRIBUTION_MANIFEST.json',model_names)
                for archive,manifest_name,kind in [
                    (source_zip,'DISTRIBUTION_MANIFEST.json','source'),
                    (model_zip,'MODEL_DISTRIBUTION_MANIFEST.json','model-assets')
                ]:
                    manifest=json.loads(archive.read('SHERLOCKED/'+manifest_name))
                    self.assertEqual(manifest['kind'],kind)
                    self.assertFalse(manifest['dependencies_included'])
                    manifests.append((manifest_name,manifest))
                    # Exclusive writes model an actual merge: collisions fail rather
                    # than silently replacing a source file or its manifest.
                    for info in archive.infolist():
                        destination=merged/info.filename
                        destination.parent.mkdir(parents=True,exist_ok=True)
                        with archive.open(info) as original,destination.open('xb') as target:
                            target.write(original.read())
            for manifest_name,expected in manifests:
                written=json.loads((merged/'SHERLOCKED'/manifest_name).read_text(encoding='utf-8'))
                self.assertEqual(written,expected)
                for item in written['files']:
                    payload=(merged/item['path']).read_bytes()
                    self.assertEqual(len(payload),item['bytes'])
                    self.assertEqual(hashlib.sha256(payload).hexdigest(),item['sha256'])
            self.assertTrue((merged/'SHERLOCKED/models/unit-model/LICENSE-MIT.txt').is_file())
            for name in ['.env','configs/app.json','configs/paths.json','data/sherlocked.sqlite3',
                         '.venv/Scripts/python.exe','models/unit-model/.cache/huggingface/token.json',
                         'cache/embedding.npy','logs/session.log']:
                self.assertFalse((merged/'SHERLOCKED'/name).exists(),name)


if __name__=='__main__':unittest.main()
