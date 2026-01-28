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
    file: UploadFile = File(...)
):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a .zip")

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    zip_base_name = os.path.splitext(file.filename)[0]  
    extract_dir = os.path.join(BASE_DIR, zip_base_name)

    os.makedirs(extract_dir, exist_ok=True)

    zip_path = os.path.join(extract_dir, file.filename)

    with open(zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    background_tasks.add_task(process_and_upload_workflow, zip_path,extract_dir,file_name)
    # process_and_upload_workflow(zip_path,extract_dir,file_name)

    return {
        "status": "success",
        "message": "File received. Processing, converting, and uploading in background.",
        "target_bucket_folder": f"events"
    }
