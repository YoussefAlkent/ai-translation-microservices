FROM python:3.9-slim

WORKDIR /app

# Add pip configuration for faster installs
RUN pip config set global.index-url https://pypi.org/simple/ \
    && pip config set global.trusted-host pypi.org \
    && pip install --upgrade pip

# Copy shared module first
COPY shared/ /app/shared/

# Copy only requirements first for better caching
COPY English2Arabic_Translator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --compile

COPY English2Arabic_Translator/ .
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
