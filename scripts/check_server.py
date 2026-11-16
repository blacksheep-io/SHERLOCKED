"""Check actual localhost startup, then stop only the process created here."""
import argparse
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main(timeout=40):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0))
        port=sock.getsockname()[1]
    with tempfile.TemporaryFile(mode='w+b') as log:
        process=subprocess.Popen(
            [sys.executable,'-m','streamlit','run',str(ROOT/'app.py'),'--server.address','127.0.0.1',
             '--server.port',str(port),'--server.headless','true','--browser.gatherUsageStats','false'],
            cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                if process.poll() is not None:
                    log.seek(0)
                    raise RuntimeError('Streamlit exited: '+log.read().decode('utf-8',errors='replace')[-6000:])
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/_stcore/health',timeout=1) as response:
                        if response.status!=200 or response.read()!=b'ok': raise RuntimeError('Unexpected health response')
                        print(f'Streamlit localhost HTTP health: 200 ok; project {ROOT}')
                        return
                except OSError: time.sleep(.2)
            raise RuntimeError('Streamlit health check timed out')
        finally:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout',type=float,default=40)
    main(parser.parse_args().timeout)

