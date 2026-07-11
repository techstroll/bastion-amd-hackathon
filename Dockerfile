# Bastion Router — containerized submission (hackathon requirement)
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY router/ router/
COPY dashboard/ dashboard/
COPY demo/ demo/

EXPOSE 9000
ENV VLLM_BASE_URL=http://host.docker.internal:8000/v1

# honors the platform-assigned $PORT (Render/HF/etc.); defaults to 9000 locally
CMD ["sh", "-c", "uvicorn router.main:app --host 0.0.0.0 --port ${PORT:-9000}"]
