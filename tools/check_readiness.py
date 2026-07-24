"""
Simple non-destructive readiness check for Chasing Your Tail (CYT).
Run: python tools\check_readiness.py
Exits with code 0 if all critical checks pass, 1 otherwise.
"""

import sys
import os
import importlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQ_FILE = os.path.join(ROOT, 'requirements.txt')
CONFIG_FILE = os.path.join(ROOT, 'config.json')

checks_failed = 0

def info(msg):
    print('[INFO]', msg)

def warn(msg):
    print('[WARN]', msg)

# Python version
info(f'Python: {sys.version.splitlines()[0]}')

# Files
if os.path.isfile(REQ_FILE):
    info('requirements.txt: found')
else:
    warn('requirements.txt: missing')
    checks_failed += 1

if os.path.isfile(CONFIG_FILE):
    info('config.json: found')
else:
    warn('config.json: missing')
    checks_failed += 1

# Check key modules
for mod in ('requests', 'cryptography'):
    try:
        importlib.import_module(mod)
        info(f"module '{mod}': import OK")
    except Exception as e:
        warn(f"module '{mod}': import failed ({e})")
        checks_failed += 1

# Environment secrets
master_pw = os.getenv('CYT_MASTER_PASSWORD')
cyt_test = os.getenv('CYT_TEST_MODE')
if master_pw:
    info('CYT_MASTER_PASSWORD: set in environment')
elif cyt_test and cyt_test.lower() in ('1','true','yes'):
    warn('CYT_TEST_MODE enabled; secure operations may be limited')
else:
    warn('CYT_MASTER_PASSWORD not set; migrate_credentials.py may prompt interactively')

# Git status (if available)
try:
    from subprocess import check_output, CalledProcessError
    out = check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    if out.strip():
        warn('git: working tree has uncommitted changes')
    else:
        info('git: working tree clean')
except Exception:
    warn('git: git not available or not a git repo')

# Kismet path hint
try:
    import json
    cfg = json.load(open(CONFIG_FILE))
    kpath = cfg.get('paths', {}).get('kismet_logs') or cfg.get('kismet_db_path')
    if kpath:
        info(f'kismet path hint: {kpath}')
except Exception:
    pass

if checks_failed:
    warn(f'{checks_failed} checks failed — see messages above')
    sys.exit(1)
else:
    info('Readiness checks passed (non-exhaustive)')
    sys.exit(0)
