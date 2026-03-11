FROM python:3.10-slim

WORKDIR /app

# System deps for OpenCV + MediaPipe
RUN apt-get update && apt-get install -y \
    curl \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# Step 1: Install CPU-only PyTorch FIRST — prevents ultralytics from
# triggering the CUDA wheel (which is 2GB+).
RUN pip install --no-cache-dir \
    torch==2.3.1+cpu \
    torchvision==0.18.1+cpu \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Step 2: Install everything else (ultralytics will see torch already installed)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# PostgreSQL client lib
RUN pip install --no-cache-dir psycopg2-binary

# Step 3: Copy application code
COPY . .

# Disable MediaPipe GPU (no GPU in container)
ENV MEDIAPIPE_DISABLE_GPU=1
ENV OMP_NUM_THREADS=2

# --workers 2: one worker keeps /stream alive, second serves /status /events without queuing
# --timeout-keep-alive 120: MJPEG connections must not be killed by idle timeout
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--timeout-keep-alive", "120", "--log-level", "warning"]