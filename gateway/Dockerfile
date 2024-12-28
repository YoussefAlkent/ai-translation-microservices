FROM python:3.9-slim

WORKDIR /app

RUN pip install --upgrade pip

COPY shared/ /app/shared/

COPY gateway/requirements.txt .
RUN pip install -r requirements.txt

COPY gateway/ /app/

ENV PYTHONPATH=/app
ENV PYTHONBUFFERED=1

CMD ["python", "app.py"]