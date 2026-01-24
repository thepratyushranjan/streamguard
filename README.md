# StreamGuard (Camera Event Processor)

StreamGuard is a FastAPI-based service designed to process, enrich, and validate camera events. It acts as a middleware between event sources (like Vector) and a ClickHouse database, while also integrating with external validation services and AI analysis.

## Features

- **Event Processing**: Receives camera events via a Vector pipeline.
- **Data Enrichment**: Enriches event data with metadata and timestamp handling.
- **Validation**:
  - **Standard Validation**: Validates event frames against an external API.
  - **AI Validation**: specific validation for "ai-info" event types.
- **System Health**: Monitors device performance and camera status.
- **Storage**: High-performance storage of event data in ClickHouse.
- **Health Monitoring**: Endpoints for service health and usage metrics.

## Prerequisites

- **Docker** and **Docker Compose**
- **Python 3.9+** (for local development)
- **ClickHouse** (provided via Docker)

## Configuration

The application is configured using environment variables. Create a `.env` file in the root directory with the following variables:

```env
# ClickHouse Database Configuration
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your_password
CLICKHOUSE_DATABASE=default

# External Services
VALIDATION_BASE_URL=https://api.example.com
VECTOR_URL=http://vector:8080

# Cloud & Storage
BUCKET_NAME=your-gcp-bucket-name
EVENT_PREFIX=events/
GOOGLE_APPLICATION_CREDENTIALS=vertex-ai-user.json

# Local Settings
CAMERA_LOGS_PATH=camera_logs.json
CAPTURES_DIR=captures
```

> **Note**: A `vertex-ai-user.json` file is expected for Google Cloud authentication if `GOOGLE_APPLICATION_CREDENTIALS` is set.

## Installation & Running

### Using Docker Compose (Recommended)

To run the entire system (FastAPI app + ClickHouse) using Docker Compose:

1.  **Clone the repository:**
    ```bash
    git clone <https://github.com/thepratyushranjan/streamguard.git>
    cd streamguard
    ```

2.  **Configure environment:**
    Ensure your `.env` file is set up as described above.

3.  **Start services:**
    ```bash
    docker-compose up --build
    ```

    The API will be available at `http://localhost:8000`.

### Local Development

To run the FastAPI service locally without Docker (requires a running ClickHouse instance):

1.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    sudo apt install ffmpeg
    ```

3.  **Run the application:**
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```

## 📋 Table Management Commands

### **List all available tables:**

```bash
docker compose exec fastapi python db/manage_tables.py list
```

### **Create a single table:**

```bash
docker compose exec fastapi python db/manage_tables.py create sop_compliance_audits
docker compose exec fastapi python db/manage_tables.py create video_analytics_logs
docker compose exec fastapi python db/manage_tables.py create system_health
```

### **Delete a single table:**

```bash
docker compose exec fastapi python db/manage_tables.py delete sop_compliance_audits
docker compose exec fastapi python db/manage_tables.py delete video_analytics_logs
docker compose exec fastapi python db/manage_tables.py delete system_health
```

### **Create all tables:**

```bash
docker compose exec fastapi python db/manage_tables.py create --all
```

### **Delete all tables:**

```bash
docker compose exec fastapi python db/manage_tables.py delete --all
```

---

**Benefits of this approach:**

- ✅ Single unified CLI for all table operations
- ✅ Auto-discovers tables from schema files
- ✅ Clear error messages if table name is wrong
- ✅ `list` command shows all available tables
- ✅ Works with Docker Compose seamlessly

## API Endpoints

### Core
- `POST /vector`: Main endpoint for receiving events from Vector pipelines. Accepts single or list of event dictionaries.

### Monitoring
- `GET /`: Service status and info.
- `GET /health`: Health check for API and Database connection.
- `GET /last-events`: Retrieve recently processed events (debugging).

### System Health
- `POST /system-health`: Receive and store system health metrics (CPU, RAM, Camera Status).

## Project Structure

- `main.py`: Application entry point and route definitions.
- `config.py`: Configuration loading using Pydantic Settings.
- `services/`: Business logic.
  - `events_services.py`: ClickHouse interaction for events.
  - `validation_service.py`: External API validation logic.
  - `ai_validation_services.py`: AI-specific validation logic.
  - `vector_services.py`: Data transformation and enrichment.
  - `system_health_services.py`: System health data processing.
- `db/`: Database connection and schema definitions.
- `middleware.py`: Custom middleware (logging, exception handling).
- `docker-compose.yml`: Container orchestration.


