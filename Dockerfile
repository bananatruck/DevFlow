# DevFlow Agent API container
# - Builds the FastAPI service
# - Does NOT execute arbitrary user code directly (sandbox does that)
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
EXPOSE 8000

# Entrypoint for the API service
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
