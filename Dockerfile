# Dockerfile cho deploy len GPU cloud (Runpod / Vast.ai / may co NVIDIA + nvidia-docker)
# Build:  docker build -t voice-studio .
# Run:    docker run --gpus all -p 8000:8000 -v %cd%/models:/app/models voice-studio
FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# torch da co san trong image -> chi cai phan con lai
RUN pip install --no-cache-dir \
    "coqui-tts>=0.24.1" "transformers>=4.45,<5.0" "huggingface_hub>=0.23" \
    "numpy<2.0" "soundfile>=0.12" "fastapi>=0.110" "uvicorn[standard]>=0.29" \
    "python-multipart>=0.0.9"

COPY engine.py apikeys.py server.py manage_keys.py ./
COPY web ./web

EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
