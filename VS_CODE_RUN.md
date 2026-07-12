# Running OmniBrain In VS Code

Open VS Code at the `omnibrain` repository root. The root should contain `app/`, `README.md`, `requirements.txt`, and `run_api.py`.

Do not run `python app/main.py` directly. That can cause:

```text
ModuleNotFoundError: No module named 'app'
```

Use `run_api.py` or the VS Code run configuration instead.

## Option 1: Run With VS Code Button

1. Open the Run and Debug panel.
2. Choose `OmniBrain API`.
3. Press the green run button.
4. Open `http://localhost:8000/docs`.

The VS Code launch config uses this working directory:

```text
${workspaceFolder}
```

## Option 2: Git Bash Commands

Use these if your VS Code terminal says `MINGW64`.

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
cp .env.example .env
python run_api.py
```

If dependencies are already installed, use:

```bash
source .venv/Scripts/activate
python run_api.py
```

## Option 3: PowerShell Commands

Use these if your VS Code terminal says `PS`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python run_api.py
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Docker Requirement

For the complete Week 1 flow, Qdrant must run. The easiest way is Docker Desktop:

```bash
docker compose up --build
```

If `docker` is not recognized, install Docker Desktop and restart VS Code.

## Quick Checks

Once running, open:

- `http://localhost:8000/`
- `http://localhost:8000/health`
- `http://localhost:8000/ready`
- `http://localhost:8000/docs`

Create a sample PDF:

```bash
python scripts/seed_sample.py
```

Upload it from Swagger or with:

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@data/sample_documents/sample_report.pdf;type=application/pdf"
```
