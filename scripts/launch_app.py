"""Start the local server without onboarding prompts; optionally open its browser."""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
ROOT=Path(__file__).resolve().parents[1]


def run(port=8501,no_browser=False):
    # Refuse an occupied port rather than claim another application's health response.
    with socket.socket() as probe:
        try: probe.bind(('127.0.0.1',port))
        except OSError as error: raise RuntimeError(f'Port {port} is occupied; use START_SHERLOCKED.bat -Port 8502') from error
    process=subprocess.Popen([sys.executable,'-m','streamlit','run',str(ROOT/'app.py'),
                              '--server.address','127.0.0.1','--server.port',str(port),
                              '--server.headless','true','--browser.gatherUsageStats','false'],cwd=ROOT)
    try:
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            if process.poll() is not None: return process.returncode or 1
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/_stcore/health',timeout=1) as response:
                    if response.status==200 and response.read()==b'ok': break
            except OSError: time.sleep(.2)
        else: raise RuntimeError('Startup timed out; inspect the server output above')
        print(f'SHERLOCKED is ready: http://127.0.0.1:{port}',flush=True)
        if not no_browser:
            try: webbrowser.open(f'http://127.0.0.1:{port}')
            except Exception as error: print(f'Open the address manually: {error}',flush=True)
        return process.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8501)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    if not 1<=args.port<=65535: parser.error('port must be 1-65535')
    try: raise SystemExit(run(args.port,args.no_browser))
    except RuntimeError as error: print(str(error),file=sys.stderr); raise SystemExit(1)
