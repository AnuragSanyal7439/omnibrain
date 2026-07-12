# OmniBrain Team Guide

Use this guide when presenting Week 1 to teammates or helping them run experiments and contribute changes.

## Quick Story To Explain

OmniBrain Week 1 is a multimodal PDF ingestion backend. A user uploads a PDF, the API stores metadata in SQLite, extracts page text and embedded images, creates overlapping text chunks, embeds text and images separately, stores vectors in Qdrant, and exposes cited text/image search endpoints.

Important design point: text embeddings and CLIP image embeddings are stored in separate Qdrant collections because they have different dimensions and semantic spaces.

## Run It With Docker

This is the easiest shared-team path.

```bash
cd omnibrain
docker compose up --build
```

Open:

- Swagger API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Readiness check: `http://localhost:8000/ready`
- Qdrant HTTP API: `http://localhost:6333`

Stop services:

```bash
docker compose down
```

## Run It Locally

Use this when developing Python code directly.

```bash
cd omnibrain
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

If Qdrant is running outside Docker Compose, set this in `.env`:

```env
QDRANT_URL=http://localhost:6333
```

Start the API:

```bash
make run
```

## Create A Sample PDF

```bash
python scripts/seed_sample.py
```

This creates:

```text
data/sample_documents/sample_report.pdf
```

## Demo Commands

Upload a PDF:

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload ^
  -F "file=@data/sample_documents/sample_report.pdf;type=application/pdf"
```

Check ingestion status:

```bash
curl http://localhost:8000/api/v1/documents/{document_id}/status
```

View processing events:

```bash
curl http://localhost:8000/api/v1/documents/{document_id}/events
```

Search text chunks:

```bash
curl -X POST http://localhost:8000/api/v1/search/text ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"What were the main revenue drivers?\",\"top_k\":5,\"document_id\":null}"
```

Search extracted images:

```bash
curl -X POST http://localhost:8000/api/v1/search/images ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"bar chart showing quarterly revenue growth\",\"top_k\":5,\"document_id\":null}"
```

Run multimodal search:

```bash
curl -X POST http://localhost:8000/api/v1/search/multimodal ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"quarterly revenue growth\",\"top_k\":5,\"document_id\":null}"
```

Delete a document:

```bash
curl -X DELETE http://localhost:8000/api/v1/documents/{document_id}
```

## What Teammates Should Watch

During upload:

- API returns `202 Accepted`, not `200 OK`, because ingestion runs in the background.
- Duplicate uploads return `409`.
- Invalid non-PDF files are rejected.
- `X-Request-ID` is returned in every response.

During ingestion:

- Status moves through `queued`, `processing`, then `completed`, `partially_completed`, or `failed`.
- `/events` shows the ingestion stages.
- `data/uploads` receives the original PDF with a UUID filename.
- `data/extracted_images` receives deterministic PNG image files.
- SQLite stores document, page, chunk, image, and event metadata.
- Qdrant receives vectors in two collections: `omnibrain_text` and `omnibrain_images`.

During search:

- Text search returns cited chunks with document name, page number, chunk ID, content type, and status.
- Image search returns cited image metadata with document name, page number, image ID, dimensions, path, content type, and status.
- Multimodal search returns separate `text_results` and `image_results`; scores are not merged.

## Experiment Checklist

Try these experiments and record observations:

1. Upload a normal text PDF and verify text chunks appear in search.
2. Upload a PDF with charts or screenshots and verify image search returns extracted images.
3. Upload the same PDF twice and confirm duplicate detection.
4. Upload a `.txt` file and confirm file type validation.
5. Upload a scanned or blank PDF page and confirm it is marked `requires_ocr`.
6. Change `TEXT_CHUNK_SIZE` and `TEXT_CHUNK_OVERLAP`, restart, and compare chunk counts.
7. Change `MIN_IMAGE_WIDTH` and `MIN_IMAGE_HEIGHT`, restart, and compare extracted image counts.
8. Stop Qdrant and observe `/ready` plus search error behavior.
9. Run deletion and verify uploaded files, extracted images, metadata, and vectors are removed.

## Contribution Areas

Good first contributions:

- Add more tests for edge-case PDFs.
- Improve error messages while keeping structured error responses.
- Add API examples to README.
- Add more sample PDFs under `data/sample_documents`.
- Improve Docker startup documentation.

Backend contributions:

- Add pagination to `GET /api/v1/documents`.
- Add richer page/chunk inspection endpoints.
- Add a repository method for querying pages and chunks.
- Add better Qdrant retry/backoff behavior.
- Add a lightweight ingestion progress percentage.

Retrieval contributions:

- Compare chunk sizes and overlaps.
- Evaluate search quality on a fixed PDF set.
- Add metadata filters beyond `document_id`.
- Add reranking experiments, but keep them optional and out of Week 1 core behavior.

Future Week 2 candidates:

- OCR for scanned pages.
- LangGraph orchestration.
- Retrieval evaluation dashboard.
- Streamlit chat UI.
- Observability with Langfuse.

Do not add these to Week 1 core yet unless the team explicitly starts Week 2.

## Contribution Workflow

Before changing code:

```bash
git status
git pull
```

Create a branch:

```bash
git checkout -b codex/your-feature-name
```

Run checks before opening a pull request:

```bash
make test
make lint
make typecheck
```

Keep pull requests small:

- One behavior change per PR.
- Include tests for backend changes.
- Update README or this guide when commands or behavior change.
- Do not commit `.env`, generated databases, uploaded PDFs, extracted runtime images, or cache folders.

Suggested PR description:

```text
Summary:
- What changed

Verification:
- make test
- make lint
- make typecheck

Notes:
- Any known limitations or follow-up ideas
```

## Roles For A Team Demo

Presenter:

- Explains the architecture and why text/image vectors are separate.

Runner:

- Starts Docker or local API and executes upload/search commands.

Observer:

- Watches status endpoints, events, file outputs, and Qdrant collections.

Experimenter:

- Changes chunk/image settings and compares behavior.

Reviewer:

- Checks tests, linting, type checking, and whether contributions stay in Week 1 scope.

## Common Problems

Docker command not found:

- Install Docker Desktop, restart the terminal, then rerun `docker compose up --build`.

Qdrant unavailable:

- Check Docker is running.
- Confirm `QDRANT_URL=http://qdrant:6333` inside Docker Compose.
- Use `QDRANT_URL=http://localhost:6333` when running the API locally.

First ingestion is slow:

- The local text embedding and CLIP models may be downloading/loading for the first time.

Duplicate upload:

- The same PDF hash already exists. Delete the document first or reset storage.

Reset local storage:

```bash
make reset
```
