Repository Readiness & Operation Checklist

Purpose
- Provide quick, actionable steps to prepare this repository for reliable operation.

Quick checklist
1. Ensure Python 3.8+ is installed and using the intended interpreter.
   - python --version
2. Install runtime dependencies using the same Python interpreter used to run the project:
   - pip install -r requirements.txt
3. Configure secrets and credentials:
   - Set CYT_MASTER_PASSWORD environment variable (recommended) or run migrate_credentials interactively.
   - Example: export CYT_MASTER_PASSWORD="<your-password>"
   - Alternatively, copy .env.example to .env and populate values for local testing.
4. Migrate any tokens from config.json into secure storage:
   - python migrate_credentials.py
5. Verify config.json settings (kismet_db_path, log directories, geo bounds):
   - Update kismet_db_path to point to host Kismet database files before running on a Linux/Kismet host.
6. Run a non-destructive readiness check:
   - python tools\check_readiness.py
7. Smoke run (after steps above):
   - python chasing_your_tail.py
   - For offline analysis/demo: python probe_analyzer.py --demo

Notes
- This project expects Kismet and a Linux environment for live captures; analysis tools can run on other OSes if Kismet DBs are available.
- Keep secret values out of git; use secure_credentials and environment variables.
