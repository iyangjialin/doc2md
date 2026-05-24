from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Optional
import shutil
from doc2md.processors import get_processor
from doc2md.config import config
from doc2md.models import ConversionResult, ProjectInfo

try:
    from doc2md.browser import router as browser_router
    HAS_BROWSER = True
except ImportError:
    HAS_BROWSER = False
    browser_router = None

app = FastAPI(title="doc2md", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if HAS_BROWSER:
    app.include_router(browser_router)

static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

Path(config.PROJECTS_DIR).mkdir(exist_ok=True)
Path(config.ASSETS_DIR).mkdir(exist_ok=True)

def generate_project_id() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d-%H%M")

@app.get("/")
async def root():
    return {"message": "doc2md API", "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/formats")
async def formats():
    return {
        "formats": ["docx", "pdf", "pptx", "ppt", "xlsx", "xls", "csv"]
    }

@app.get("/api/projects")
async def list_projects():
    projects_dir = Path(config.PROJECTS_DIR)
    projects = []
    for d in projects_dir.iterdir():
        if d.is_dir():
            projects.append(d.name)
    return {"projects": sorted(projects, reverse=True)}

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    project_dir = Path(config.PROJECTS_DIR) / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    files = []
    assets = []

    for f in project_dir.glob("*.md"):
        files.append(f.name)

    assets_dir = project_dir / config.ASSETS_DIR
    if assets_dir.exists():
        for f in assets_dir.rglob("*"):
            if f.is_file():
                assets.append(str(f.relative_to(project_dir)))

    return ProjectInfo(
        project_id=project_id,
        created_at="",
        files=files,
        assets=assets
    )

@app.post("/convert")
async def convert(
    file: UploadFile = File(...),
    ocr_mode: str = Form("full"),
    force_ocr: bool = Form(False)
):
    content = await file.read()
    if len(content) > config.MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large. Max size: {config.MAX_FILE_SIZE_MB}MB")

    project_id = generate_project_id()

    temp_path = Path(f"/tmp/{file.filename}")
    temp_path.write_bytes(content)

    try:
        processor_class = get_processor(str(temp_path))
        processor = processor_class(project_id=project_id, ocr_mode=ocr_mode)
        result = processor.process(str(temp_path))

        return {
            "project_id": result.project_id,
            "markdown": result.markdown,
            "assets": result.assets,
            "filename": result.filename
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path.exists():
            temp_path.unlink()

@app.post("/convert/batch")
async def convert_batch(
    files: list[UploadFile] = File(...),
    ocr_mode: str = Form("full"),
    force_ocr: bool = Form(False)
):
    project_id = generate_project_id()
    results = []

    for file in files:
        content = await file.read()
        if len(content) > config.MAX_FILE_SIZE_BYTES:
            results.append({
                "filename": file.filename,
                "error": f"File too large: {file.filename}"
            })
            continue

        temp_path = Path(f"/tmp/{file.filename}")
        temp_path.write_bytes(content)

        try:
            processor_class = get_processor(str(temp_path))
            processor = processor_class(project_id=project_id, ocr_mode=ocr_mode)
            result = processor.process(str(temp_path))
            results.append({
                "filename": result.filename,
                "markdown": result.markdown,
                "assets": result.assets
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "error": str(e)
            })
        finally:
            if temp_path.exists():
                temp_path.unlink()

    return {"project_id": project_id, "results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)