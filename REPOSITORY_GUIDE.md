REPOSITORY GUIDE — How to prepare this repo for your thesis

This guide shows practical steps to make the repository clean, reproducible, and ready for submission with your Bab 3.

1. Repository structure (recommended)

- `src/` : source code (API, chatbot, nlp, utils)
- `data/` : datasets and CSV evaluation results
- `models/` : trained models (if any; for thesis you may omit to keep deterministic rule-based repo)
- `docs/`  : diagrams, Bab3 mapping, questionnaires
- `tests/` : unit/integration tests used during development
- `scripts/` : helper scripts for running the system locally and collecting logs

2. Essential files to include for thesis submission
- `README.md` : short project summary and run instructions
- `REPOSITORY_GUIDE.md` : this file (what to include and how to produce evidence)
- `docs/BAB3_mapping.md` : mapping between Bab 3 sections and code (generated)
- Example logs: `logs/intent_debug.log`, `logs/uvicorn_out.log` (export `journalctl` output)
- Evaluation outputs: `datasheet/hasil_evaluasi_chatbot_v2.csv` and confusion matrix images

3. Reproducibility checklist
- Add `requirements.txt` (already present). Freeze exact versions used during experiments, e.g. `pip freeze > requirements.txt` on the experiment environment.
- Provide a one-command run script (example below) and a Dockerfile if you want full reproducibility.

Example helper script (save as `scripts/run_local.sh`):
```bash
# start api (development)
export INTENT_DEBUG=1
export APPLY_TIME_GREETING=all
export TIMEZONE=Asia/Jakarta
PYTHONPATH=./src uvicorn src.api_fastapi:app --host 0.0.0.0 --port 8121 > logs/uvicorn_out.log 2>&1 &

# start telegram bot (if token configured in env)
nohup python3 src/telegram_bot.py > logs/telegram_bot.log 2>&1 &

echo "Services started. Tail logs with: tail -f logs/uvicorn_out.log logs/telegram_bot.log"
```

4. Logging and evidence collection
- For intent matching traces, run API with `INTENT_DEBUG=1` and collect the stdout/stderr (`logs/intent_debug.log`).
- For each experiment run, create a small manifest text `experiments/run-YYYYMMDD.txt` describing env vars, server spec, and test cases used.

5. Git & release
- Initialize git repo (if not already): `git init` → add a clear `.gitignore` (Python artifacts, venv, __pycache__).
- Tag releases that correspond to thesis snapshots, e.g. `git tag -a v1.0-thesis -m "Thesis snapshot"`.

6. Optional: Dockerfile (simple example)
- A Dockerfile lets examiners run your system exactly. If you want, I can create a minimal Dockerfile and `docker-compose.yml`.

7. What I can do for you now
- Create/format `README.md` with run instructions.
- Add `scripts/run_local.sh` and a sample `.gitignore`.
- Create Dockerfile + docker-compose for one-command run.

If you want, I will (A) add `README.md` and small helper scripts now, or (B) create Docker artifacts. Which do you prefer?

