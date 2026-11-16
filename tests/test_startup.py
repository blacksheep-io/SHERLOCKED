"""Windows startup contracts and resource initialization without touching user reports."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from scripts.health import dependency_state,inspect
ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(sys.platform=='win32','Windows launcher contracts')
class WindowsStartupTests(unittest.TestCase):
    def run_ps(self,script,cwd):
        return subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script)],
                              cwd=cwd,capture_output=True,text=True,timeout=30,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))

    def test_missing_environment_actionable_and_no_creation(self):
        with tempfile.TemporaryDirectory(prefix='SHERLOCKED missing env ') as directory:
            root=Path(directory)
            (root/'scripts').mkdir()
            shutil.copy2(ROOT/'scripts/windows_common.ps1',root/'scripts/windows_common.ps1')
            shutil.copy2(ROOT/'start.ps1',root/'start.ps1')
            result=self.run_ps(root/'start.ps1',Path(directory).parent)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('SETUP_SHERLOCKED.bat',result.stdout)
            self.assertFalse((root/'.venv').exists())

    def test_moved_environment_preserved_inside_project(self):
        with tempfile.TemporaryDirectory(prefix='SHERLOCKED move test ') as directory:
            root=Path(directory)
            (root/'.venv').mkdir()
            (root/'.venv/valuable.txt').write_text('preserve me',encoding='utf-8')
            (root/'.venv/sherlocked-environment.json').write_text(json.dumps({'project_root':str(root/'old')}),encoding='utf-8')
            quote=lambda value: str(value).replace("'","''")
            script=root/'check.ps1'
            script.write_text(
                ". '"+quote(ROOT/'scripts/windows_common.ps1')+"'\n"+
                "function Get-PythonInfo([string]$Executable) { return [pscustomobject]@{version=@(3,12);base='fixture'} }\n"+
                "$state=Get-VenvState '"+quote(root)+"'\n"+
                "Write-Output $state.Status\n"+
                "if ($state.Status -eq 'moved') { Backup-Venv '"+quote(root)+"' }\n",
                encoding='utf-8-sig')
            result=self.run_ps(script,root)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertIn('moved',result.stdout)
            copies=list((root/'backups/environments').glob('*/valuable.txt'))
            self.assertEqual(len(copies),1)
            self.assertEqual(copies[0].read_text(encoding='utf-8'),'preserve me')
            self.assertFalse((root/'.venv').exists())


class HealthTests(unittest.TestCase):
    def test_missing_dependency_actionable(self):
        from importlib.metadata import PackageNotFoundError
        def version(name):
            if name=='torch': raise PackageNotFoundError('torch')
            return {'streamlit':'1.51.0','scikit-learn':'1.7.2','plotly':'6.4.0',
                    'sentence-transformers':'3.4.1','transformers':'4.48.3','sentencepiece':'0.2.0'}[name]
        with patch('scripts.health.importlib.metadata.version',side_effect=version):
            versions,errors=dependency_state()
        self.assertIsNone(versions['torch'])
        self.assertTrue(any('SETUP_SHERLOCKED' in error for error in errors))

    def test_custom_resources_initialize_preserve_source(self):
        before=(ROOT/'data/reports.jsonl').read_bytes()
        with tempfile.TemporaryDirectory(prefix='SHERLOCKED resources ') as directory:
            env={'SHERLOCKED_DATASET_DIR':str(Path(directory)/'dataset'),
                 'SHERLOCKED_DATABASE_PATH':str(Path(directory)/'db/reports.sqlite3'),
                 'SHERLOCKED_RESULTS_DIR':str(Path(directory)/'results'),
                 'SHERLOCKED_LOG_DIR':str(Path(directory)/'logs'),
                 'SHERLOCKED_EXPORT_DIR':str(Path(directory)/'exports'),
                 'SHERLOCKED_TEMP_DIR':str(Path(directory)/'temp')}
            with patch.dict(os.environ,env):
                result=inspect(initialize=True,lightweight=True)
            self.assertEqual(result['errors'],[],result)
            self.assertTrue(Path(env['SHERLOCKED_DATABASE_PATH']).exists())
            self.assertEqual((Path(env['SHERLOCKED_DATASET_DIR'])/'reports.jsonl').read_bytes(),before)
        self.assertEqual((ROOT/'data/reports.jsonl').read_bytes(),before)



@unittest.skipUnless(sys.platform=='win32','Windows profile argument check')
class TorchProfileTests(unittest.TestCase):
    def test_exact_profiles_cannot_satisfy_the_opposite_variant(self):
        from packaging.specifiers import SpecifierSet
        # Demonstrate why the former public-version pin was insufficient.
        self.assertTrue(SpecifierSet('==2.6.0').contains('2.6.0+cu124'))
        self.assertFalse(SpecifierSet('==2.6.0+cpu').contains('2.6.0+cu124'))
        self.assertFalse(SpecifierSet('==2.6.0+cu124').contains('2.6.0+cpu'))
        setup=str(ROOT/'setup.ps1').replace("'","''")
        command=(
            "$tokens=$null; $parseErrors=$null; "
            f"$ast=[Management.Automation.Language.Parser]::ParseFile('{setup}',[ref]$tokens,[ref]$parseErrors); "
            "if ($parseErrors.Count) { throw 'Setup script has parse errors' }; "
            "$definition=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Get-TorchInstallArguments'},$true); "
            "Invoke-Expression $definition.Extent.Text; "
            "@{cpu=@(Get-TorchInstallArguments '2.6.0+cpu' 'https://download.pytorch.org/whl/cpu' ''); "
            "cuda=@(Get-TorchInstallArguments '2.6.0+cu124' 'https://download.pytorch.org/whl/cu124' ''); "
            "offline=@(Get-TorchInstallArguments '2.6.0+cpu' '' 'E:\\trusted wheels')} | ConvertTo-Json -Compress"
        )
        result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-Command',command],
                              capture_output=True,text=True,timeout=20,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertEqual(result.returncode,0,result.stderr)
        arguments=json.loads(result.stdout)
        self.assertIn('torch==2.6.0+cpu',arguments['cpu'])
        self.assertIn('torch==2.6.0+cu124',arguments['cuda'])
        self.assertIn('--index-url',arguments['cpu'])
        self.assertIn('--no-index',arguments['offline'])
        self.assertNotIn('--index-url',arguments['offline'])
        self.assertNotIn('torch==2.6.0',arguments['cpu'])


if __name__=='__main__': unittest.main()

