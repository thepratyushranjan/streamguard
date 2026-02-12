from typing import Optional
from fastapi import APIRouter
from core.config import get_settings
import os
import shutil
from fastapi import UploadFile, File, Form, BackgroundTasks, HTTPException

from services.file_conversion import process_and_upload_workflow

from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Root"])
settings = get_settings()


@router.get("/")
def root():
    return {
        "status": "running", 
        "service": "camera-event-processor",
        "database": settings.clickhouse_database
    }

@router.post("/upload-folder/")
async def upload_folder(
    background_tasks: BackgroundTasks,
    file_name:str = Form(...),
    file: UploadFile = File(...),
    json_data: Optional[str] = Form(None)
):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a .zip")

    # Get the project root directory (2 levels up from api/routes/)
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Create uploads directory in project root if not exists
    UPLOADS_DIR = os.path.join(PROJECT_ROOT, "uploads")
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    # Save the zip file with its original name in uploads directory
    zip_path = os.path.join(UPLOADS_DIR, file.filename)

    with open(zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create extraction directory inside uploads with the zip's base name
    zip_base_name = os.path.splitext(file.filename)[0]
    extract_dir = os.path.join(UPLOADS_DIR, zip_base_name)
    os.makedirs(extract_dir, exist_ok=True)

    background_tasks.add_task(process_and_upload_workflow, zip_path, extract_dir, file_name,json_data)
    # process_and_upload_workflow(zip_path, extract_dir, file_name,json_data)

    return {
        "status": "success",
        "message": "File received. Processing, converting, and uploading in background.",
        "target_bucket_folder": f"events"
    }
