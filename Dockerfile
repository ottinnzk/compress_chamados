FROM python:3.11-slim

# Instala o FFmpeg nativo do Linux
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cria as pastas temporárias
RUN mkdir -p temp_uploads temp_compressed

# O Gunicorn passa a escutar dinamicamente na porta definida pelo Fly.io (ou 8080 por defeito)
CMD gunicorn --bind 0.0.0.0:${PORT:-8080} --timeout 300 app:app