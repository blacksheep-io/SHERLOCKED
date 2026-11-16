"""Explicit online setup or offline verification of the approved model assets."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sherlocked.semantic import setup_model,SemanticUnavailable

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--device',choices=['auto','cpu','cuda'],default='auto')
    parser.add_argument('--offline',action='store_true',help='Verify transferred local model assets without any model download')
    args=parser.parse_args()
    try:
        print(json.dumps(setup_model(args.device,offline=args.offline),indent=2))
    except (SemanticUnavailable,ValueError) as exc:
        print(str(exc),file=sys.stderr)
        sys.exit(1)
