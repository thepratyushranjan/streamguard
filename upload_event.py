import os
import shutil
from google.cloud import storage
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
CAPTURES_DIR = "/home/pratyush/Desktop/Roboi/streamguard/captures"
# Create a separate directory for completed events so we don't re-upload
COMPLETED_DIR = "/home/pratyush/Desktop/Roboi/streamguard/captures_uploaded"
BUCKET_NAME = "roboi-event-captures"

# Initialize GCP Client (Ensure GOOGLE_APPLICATION_CREDENTIALS is set in env)
storage_client = storage.Client()
bucket = storage_client.bucket(BUCKET_NAME)

def upload_directory(dir_path, event_name):
    print(f"Processing ready event: {event_name}")
    for filename in os.listdir(dir_path):
        file_path = os.path.join(dir_path, filename)
        if os.path.isfile(file_path):
            blob = bucket.blob(f"events/{event_name}/{filename}")
            blob.upload_from_filename(file_path)
            print(f"Uploaded {filename}")
    
    # Move to completed folder to prevent re-processing
    shutil.move(dir_path, os.path.join(COMPLETED_DIR, event_name))
    print(f"Moved {event_name} to completed directory.")

def check_and_upload():
    # Create completed dir if not exists
    os.makedirs(COMPLETED_DIR, exist_ok=True)

    # Scan all directories in captures
    for event_name in os.listdir(CAPTURES_DIR):
        event_path = os.path.join(CAPTURES_DIR, event_name)
        
        if not os.path.isdir(event_path):
            continue

        # Count files
        files = os.listdir(event_path)
        images = [f for f in files if f.endswith(('.jpg', '.png', '.jpeg'))]
        videos = [f for f in files if f.endswith(('.mp4', '.avi', '.mkv'))]

        # Logic: Strictly 5 images and 1 video
        if len(images) == 5 and len(videos) == 1:
            upload_directory(event_path, event_name)
        else:
            # Optional: Log that it's waiting for more files
            pass
print("All events processed.")
if __name__ == "__main__":
    check_and_upload()