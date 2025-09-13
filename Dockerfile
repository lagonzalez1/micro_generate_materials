FROM python:3.11-slim

# Install dependencies
WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Endpoint
CMD ["python", "main.py"]