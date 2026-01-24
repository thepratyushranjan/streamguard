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


# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp_uploads")
CONFIG_PATH = os.path.join(BASE_DIR, "configs", "app_config.yaml")

os.makedirs(TEMP_DIR, exist_ok=True)

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

    temp_zip_path = os.path.join(TEMP_DIR, f"{file.filename}")
    
    with open(temp_zip_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    background_tasks.add_task(process_and_upload_workflow, temp_zip_path,TEMP_DIR,file_name)
    # process_and_upload_workflow(temp_zip_path,TEMP_DIR,file_name)

    return {
        "status": "success",
        "message": "File received. Processing, converting, and uploading in background.",
        "target_bucket_folder": f"events"
    }
