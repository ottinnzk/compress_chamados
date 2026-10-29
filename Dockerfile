FROM python:3.11-slim

# Instala o FFmpeg nativo do Linux no container
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala as dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cria as pastas temporárias
RUN mkdir -p temp_uploads temp_compressed

# Executa o servidor de produção Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "--timeout", "300", "app:app"]