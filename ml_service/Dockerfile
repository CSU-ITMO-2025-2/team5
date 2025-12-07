FROM python:3.10-slim AS builder
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV MODEL_NAME=Aniemore/rubert-tiny2-russian-emotion-detection
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
    print('Downloading model and tokenizer...'); \
    AutoTokenizer.from_pretrained('$MODEL_NAME'); \
    AutoModelForSequenceClassification.from_pretrained('$MODEL_NAME'); \
    print('Model cache created.');"

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7070"]
