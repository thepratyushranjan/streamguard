FROM python:3.12.3

WORKDIR /app

# Disable Python output buffering
ENV PYTHONUNBUFFERED=1

# Install FFmpeg 6.x - Using latest release for better reliability
RUN apt-get update && \
    apt-get install -y --no-install-recommends wget xz-utils && \
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar xf ffmpeg-release-amd64-static.tar.xz && \
    cd ffmpeg-*-amd64-static && \
    mv ffmpeg /usr/local/bin/ && \
    mv ffprobe /usr/local/bin/ && \
    cd .. && \
    rm -rf ffmpeg-* && \
    apt-get remove -y wget xz-utils && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
