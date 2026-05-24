# CODEBUDDY.md

This file provides guidance to CodeBuddy Code when working with code in this repository.

## Project Overview

doc2md converts documents (Word, PDF, PowerPoint, Excel) to Markdown format. It provides three interfaces: CLI, REST API, and a React web UI. OCR support via Tesseract (local) and DeepSeek API (cloud).

## Common Commands

### Backend (Python)

```bash
# Install dependencies
pip install -r doc2md/requirements.txt

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_processors.py -v

# Run a specific test
pytest tests/test_processors.py::TestProcessorDetection::test_get_processor_docx -v

# CLI usage
python -m doc2md.cli convert document.docx
python -m doc2md.cli convert file1.docx file2.pdf file3.xlsx  # batch
python -m doc2md.cli list-projects
python -m doc2md.cli serve --port 8000

# Start API server directly
python -m uvicorn doc2md.api:app --host 0.0.0.0 --port 8000
```

### Frontend (React + Vite, in `web/`)

```bash
cd web
npm install
npm run dev       # dev server
npm run build     # production build (tsc + vite)
npm run lint      # eslint
```

The frontend expects the backend at `http://localhost:8000` (configure via `VITE_API_BASE_URL`).

### Docker

```bash
docker build -t doc2md -f doc2md/Dockerfile doc2md/
docker run -p 8000:8000 doc2md
```

## Architecture

### Dual-Component Structure

- **Backend** (`doc2md/`): Python package with FastAPI server, CLI, and document processors
- **Frontend** (`web/`): React 19 + Vite + TypeScript + Tailwind + shadcn/ui components

### Processor Pattern

Document conversion uses a class-based plugin pattern:

1. `BaseProcessor` (abstract, in `processors/base.py`) defines the interface with `SUPPORTED_EXTENSIONS`, `can_process()`, `process()`, and helpers (`save_asset`, `build_front_matter`, `slugify`)
2. Concrete processors (`DocxProcessor`, `PdfProcessor`, `PptxProcessor`, `XlsxProcessor`) each declare their supported extensions and implement `process()`
3. `get_processor(file_path)` in `processors/__init__.py` iterates `PROCESSORS` list, calls `can_process()` on each, and returns the **class** (not an instance)
4. Callers (CLI/API) instantiate: `processor_class(project_id=..., ocr_mode=...)` then call `processor.process(file_path)`

Key detail: `get_processor()` returns a **class**, not an instance. You must instantiate with `project_id` before calling `process()`.

### Output Structure

Each conversion creates a project directory under `projects/` named by timestamp (`YYYY-MM-DD-HHMM`). Markdown output and extracted images (in `assets/`) are saved there.

### OCR Pipeline

`OCRProcessor` (in `ocr.py`) tries Tesseract first, falls back to DeepSeek API if confidence is below `DEEPSEEK_OCR_THRESHOLD`. Configured via `.env` (see `doc2md/.env.example`).

### Data Flow

- `models.py`: `ConversionResult`, `ProjectInfo`, `OCRResult` (dataclasses)
- `config.py`: Singleton `Config` loaded from `.env` via `python-dotenv`
- `api.py`: FastAPI app with `/convert`, `/convert/batch`, `/api/projects` endpoints; includes browser router from `browser.py`
- `browser.py`: APIRouter at `/browser` for file browsing/preview (in-app HTML with marked.js, highlight.js, KaTeX)
- `cli.py`: Typer CLI with `convert`, `batch`, `list-projects`, `serve` commands

### Frontend Key Components

- `App.tsx`: Main layout with upload/preview split view
- `FileUploader.tsx`: Drag-and-drop file upload with OCR mode selection, uses `useDocConverter` hook
- `MarkdownPreview.tsx`: Renders markdown with preview/source tabs

## Key Configuration

Environment variables (set in `.env`):
- `DEEPSEEK_API_KEY`: Required for cloud OCR fallback
- `DEEPSEEK_MODEL`: Model name (default: `gpt-4.1`)
- `DEEPSEEK_API_BASE`: API endpoint (default: `https://api.deepseek.com/v1`)
- `DEEPSEEK_OCR_THRESHOLD`: Confidence threshold to trigger DeepSeek fallback (default: `0.8`)
- `DEFAULT_OCR_MODE`: `full`, `caption`, or `none` (default: `full`)
- `MAX_FILE_SIZE_MB`: Upload size limit (default: `50`)
