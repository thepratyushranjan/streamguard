import json
import os
import shutil
import zipfile
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.cloud import storage
from google.cloud.exceptions import NotFound
from PIL import Image
from utils.common import safe_json_load
from utils.logger import get_logger
import requests


logger = get_logger(__name__)

def get_storage_client():
    """Initializes GCS Client based on your existing code."""
    try:
        key_path = "vertex-ai-user.json"
        if os.path.exists(key_path):
            return storage.Client.from_service_account_json(key_path)
        else:
            return storage.Client() # Fallback to default auth
    except Exception as e:
        logger.error(f"Failed to init GCS client: {e}")
        return None


def get_or_create_bucket(storage_client, bucket_name):
    """
    Checks if a bucket exists. If not, creates it.
    Returns the Bucket object.
    """
    try:
        bucket = storage_client.bucket(bucket_name)
        
        bucket.reload()
        logging.info(f"Bucket '{bucket_name}' already exists.")
        return bucket

    except NotFound:
        logging.info(f"Bucket '{bucket_name}' not found")
        # try:
        #     bucket = storage_client.create_bucket(bucket_name)
        #     logging.info(f"Bucket '{bucket_name}' created successfully.")
        #     return bucket
        # except Exception as create_error:
        #     logging.error(f"Failed to create bucket '{bucket_name}': {create_error}")
        #     raise

    except Exception as e:
        logging.error(f"Error checking bucket '{bucket_name}': {e}")
        raise

def check_folder(bucket, folder_name: str) -> bool:
    blobs = bucket.list_blobs(prefix=folder_name, max_results=1)

    for _ in blobs:
        logger.info("Folder already exists")
        return True

    return False
def convert_image_to_webp(file_path: str) -> str:
    """Converts .jpeg, .jpg, .avf to .webp and returns new path."""
    try:
        output_path = os.path.splitext(file_path)[0] + ".webp"
        with Image.open(file_path) as img:
            if img.mode not in ["RGB", "RGBA"]:
                img = img.convert("RGB")
            img.save(output_path, "WEBP", quality=80)
        
        if os.path.exists(output_path):
            os.remove(file_path)
            return output_path
    except Exception as e:
        logger.error(f"Image conversion failed for {file_path}: {e}")
    return file_path

def convert_video_to_webm(file_path: str) -> str:
    """
    Converts .mp4 and .avi to .webm using ffmpeg.
    """
    try:
        if not file_path.lower().endswith(('.mp4', '.avi')):
            return file_path

        webm_path = os.path.splitext(file_path)[0] + ".webm"
        
        logging.info(f"Converting file: {file_path} -> {webm_path}")

        command = [
            "ffmpeg", "-y",
            "-i", file_path,                 
            "-c:v", "libvpx-vp9",            
            "-b:v", "0", "-crf", "30",       
            "-pix_fmt", "yuv420p",          
            "-an",                           
            "-f", "webm",                    
            webm_path
        ]
        
        result = subprocess.run(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        if result.returncode != 0:
            logging.error(f"FFmpeg Failed for {file_path}\nError: {result.stderr}")
            return file_path

        if os.path.exists(webm_path):
            os.remove(file_path) 
            logging.info(f"Conversion Success: {webm_path}")
            return webm_path
        else:
            logging.error(f"WebM file was not created for {file_path}")

    except Exception as e:
        logging.error(f"Video conversion exception for {file_path}: {e}")
        
    return file_path
def upload_single_file(bucket, blob_name, file_path):
    """Helper for thread pool upload."""
    try:
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(file_path)
        logger.info(f"Uploaded: {blob_name}")
        return True
    except Exception as e:
        logger.error(f"Upload failed {blob_name}: {e}")
        return False


def process_and_upload_workflow(zip_file_path: str,TEMP_DIR:str,bucket_name:str,json_data=None,tmp_filename = None):
    """
    1. Unzip
    2. Convert (Images -> WebP, Video -> WebM)
    3. Upload to GCS
    4. Cleanup (Delete local folder)
    """
    logger.info(f"Starting processing for folder: {TEMP_DIR}")
    
    extract_path = TEMP_DIR
    # os.makedirs(extract_path, exist_ok=True)

    client = get_storage_client() 

    bucket = get_or_create_bucket(client, bucket_name)
    
    if not bucket or not client:
        logger.error("GCS Configuration missing. Aborting.")
        return


    try:
        exist = check_folder(bucket, tmp_filename)
        if exist:
            logger.info("Folder exists. Skipping.")
            return
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        os.remove(zip_file_path)

        files_to_upload = []

        for root, dirs, files in os.walk(extract_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()

                if ext in ['.mp4', '.avi']:
                    file_path = convert_video_to_webm(file_path)
                elif ext in ['.jpeg', '.jpg']:
                    file_path = convert_image_to_webp(file_path)
                
                rel_path = os.path.relpath(file_path, extract_path)
                folder_name = os.path.basename(extract_path)
                blob_name = f"events/{folder_name}/{rel_path}".replace("\\", "/")
                
                files_to_upload.append((blob_name, file_path))
        logger.info(f"Prepared {len(files_to_upload)} files for upload.")

        logger.info(f"Uploading {len(files_to_upload)} files...")
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_file = {
                executor.submit(upload_single_file, bucket, bn, fp): fp 
                for bn, fp in files_to_upload
            }
            for future in as_completed(future_to_file):
                future.result()

        logger.info("Upload sequence completed.")
        try:
            if json_data:        
                headers = {
                    "Content-Type": "application/json"
                }
                url = "https://roboiingest.invincibleocean.com/vector"
                if bucket_name == '697cbadab584b2e17eb86d24':
                    url = "https://roboiingest.invincibleocean.com/vector-office"
                
                logger.info(f"Calling for AI info endpoint: {url}")

                try:
                    payload = safe_json_load(json_data)
                    logger.info("Successfully parsed JSON payload")
                    logger.info(f"Payload: {payload}")
                except json.JSONDecodeError as json_err:
                    logger.error(f"JSON parsing failed: {json_err}")
                    logger.error(f"Full json_data: {json_data}")
                    raise
                
                logger.info("Sending POST request to vector endpoint")
                response = requests.post(url, json=payload, headers=headers)
                logger.info(f"API response status: {response.status_code}")
                logger.info(f"API response: {response.text}")
        except Exception as e:
            logger.error(f"Exception during API hit: {str(e)}")
            logger.error(f"json_data content: {json_data}")
    except Exception as e:
        logger.error(f"Critical Error in workflow: {e}")

    finally:
        if os.path.exists(extract_path):
            logger.info(f"Deleting local folder: {extract_path}")
            shutil.rmtree(extract_path)
        
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)

