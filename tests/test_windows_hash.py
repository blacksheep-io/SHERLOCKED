"""Windows setup hashing must work without optional PowerShell module autoload."""
import hashlib
import os
from pathlib import Path
import subprocess
import unittest

@unittest.skipUnless(os.name=='nt','Windows launcher check')
class WindowsHashTests(unittest.TestCase):
    def test_hash_without_utility_module_autoload(self):
        root=Path(__file__).resolve().parents[1]
        common=str(root/'scripts/windows_common.ps1').replace("'","''")
        requirements=str(root/'requirements.txt').replace("'","''")
        code=f". '{common}'; $PSModuleAutoLoadingPreference='None'; Get-PortableFileHash '{requirements}'"
        result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-Command',code],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip().lower(),hashlib.sha256((root/'requirements.txt').read_bytes()).hexdigest())
