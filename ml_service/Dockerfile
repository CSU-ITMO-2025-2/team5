FROM python:3.10-slim

WORKDIR /

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7070

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7070"]
