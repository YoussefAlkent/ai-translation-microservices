FROM python:3.9-slim

WORKDIR /app

# Add pip configuration and install dependencies
RUN pip install --upgrade pip

# Copy shared module first
COPY shared/ /app/shared/

# Copy and install requirements
COPY gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY gateway/ .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
