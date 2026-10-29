import os
import json
import uuid
import subprocess
from pathlib import Path
from flask import Flask, request, render_template_string, send_file, after_this_request

app = Flask(__name__)

# 1. DIRETÓRIO BASE E CAMINHO DO FFMPEG
BASE_DIR = Path(__file__).resolve().parent
FFMPEG_BIN_PATH = r"C:\Users\otto.ettinger\OneDrive - COOPERATIVA VEILING HOLAMBRA\Área de Trabalho\Nova pasta (2)\ffmpeg-9.0.2-essentials_build\bin"

# 2. DECLARAÇÃO GLOBAL DOS EXECUTÁVEIS
def get_exe_path(tool_name):
    if FFMPEG_BIN_PATH and os.path.exists(FFMPEG_BIN_PATH):
        exe = os.path.join(FFMPEG_BIN_PATH, f"{tool_name}.exe")
        if os.path.exists(exe):
            return exe
    local_exe = BASE_DIR / f"{tool_name}.exe"
    if local_exe.exists():
        return str(local_exe)
    return tool_name

FFMPEG_EXE = get_exe_path("ffmpeg")
FFPROBE_EXE = get_exe_path("ffprobe")

# 3. PASTAS TEMPORÁRIAS
UPLOAD_FOLDER = BASE_DIR / "temp_uploads"
OUTPUT_FOLDER = BASE_DIR / "temp_compressed"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

TARGET_SIZE_MB = 18.5
AUDIO_BITRATE_KBPS = 128


def get_video_duration(input_path: str) -> float:
    cmd = [
        FFPROBE_EXE,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        input_path
    ]

    res = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        encoding="utf-8", 
        errors="replace"
    )

    if res.returncode != 0 or not res.stdout.strip():
        err = res.stderr.strip() if res.stderr else "Falha ao ler metadados."
        raise RuntimeError(f"O ffprobe não conseguiu analisar o arquivo.\nDetalhes: {err}")

    data = json.loads(res.stdout)
    return float(data["format"]["duration"])


def compress_video(input_path: str, output_path: str):
    duration = get_video_duration(input_path)

    target_bits = TARGET_SIZE_MB * 8 * 1024 * 1024
    total_kbps = (target_bits / duration) / 1024
    video_kbps = int(total_kbps - AUDIO_BITRATE_KBPS)

    if video_kbps < 150:
        video_kbps = 150

    scale_filter = "scale=-2:720" if video_kbps < 800 else "scale=-2:1080"

    cmd = [
    "ffmpeg", "-y",
    "-i", input_path,
    "-c:v", "libx264",
    "-preset", "superfast",
    "-b:v", f"{video_bitrate}k",
    "-maxrate", f"{video_bitrate}k",
    "-bufsize", f"{video_bitrate * 2}k",
    "-threads", "1",  # <-- Limita o uso de CPU/RAM para o servidor gratuito
    "-c:a", "aac",
    "-b:a", "128k",
    output_path
]

    res = subprocess.run(
        ffmpeg_cmd, 
        capture_output=True, 
        text=True, 
        encoding="utf-8", 
        errors="replace"
    )
    if res.returncode != 0:
        raise RuntimeError(f"Erro na compressão do FFmpeg:\n{res.stderr}")


# HTML da Interface com Rodapé
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Compressor de Vídeos (< 20MB)</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; background: #f4f6f9; margin: 0; padding: 40px 20px; }
        .container { max-width: 480px; margin: 0 auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        h2 { margin-top: 0; color: #1e293b; font-size: 1.3rem; }
        p { color: #64748b; font-size: 0.9rem; line-height: 1.4; }
        .upload-area { border: 2px dashed #cbd5e1; padding: 25px; text-align: center; border-radius: 8px; margin: 20px 0; background: #f8fafc; }
        button { width: 100%; background: #2563eb; color: white; border: none; padding: 12px; font-size: 1rem; font-weight: 600; border-radius: 6px; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #1d4ed8; }
        .status { margin-top: 15px; font-size: 0.9rem; color: #059669; font-weight: 600; text-align: center; display: none; }
        
        /* Estilo do Rodapé */
        .footer { 
            margin-top: 25px; 
            padding-top: 15px; 
            border-top: 1px solid #e2e8f0; 
            text-align: center; 
            font-size: 0.8rem; 
            color: #94a3b8; 
        }
        .footer strong { color: #64748b; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Compressor de Vídeo para Chamados</h2>
        <p>Ajuste automático para garantir que o vídeo fique dentro do limite de 20MB.</p>
        
        <form action="/compress" method="post" enctype="multipart/form-data" onsubmit="showLoading()">
            <div class="upload-area">
                <input type="file" name="file" accept="video/*" required>
            </div>
            <button type="submit" id="btnSubmit">Comprimir e Baixar</button>
        </form>
        <div id="statusMsg" class="status">Processando vídeo... por favor aguarde.</div>

        <!-- Rodapé do Card -->
        <div class="footer">
            🛠️ <strong>Ferramenta Interna</strong> • Otimização de anexos para o sistema de chamados
        </div>
    </div>

    <script>
        function showLoading() {
            document.getElementById('btnSubmit').disabled = true;
            document.getElementById('btnSubmit').innerText = 'Comprimindo...';
            document.getElementById('statusMsg').style.display = 'block';
        }
    </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/compress", methods=["POST"])
def compress():
    if "file" not in request.files:
        return "Nenhum arquivo enviado", 400

    file = request.files["file"]
    if file.filename == "":
        return "Nenhum arquivo selecionado", 400

    file_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename).suffix or ".mp4"

    input_path = str(UPLOAD_FOLDER / f"{file_id}_in{ext}")
    output_path = str(OUTPUT_FOLDER / f"{file_id}_25MB.mp4")

    try:
        file.save(input_path)
        compress_video(input_path, output_path)

        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(input_path): os.remove(input_path)
                if os.path.exists(output_path): os.remove(output_path)
            except Exception as e:
                app.logger.error(f"Erro ao deletar arquivos: {e}")
            return response

        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"comprimido_{file.filename.rsplit('.', 1)[0]}.mp4"
        )

    except Exception as e:
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)
        return f"Erro ao processar vídeo: {str(e)}", 500


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print(f" FFmpeg: {FFMPEG_EXE}")
    print(f" FFprobe: {FFPROBE_EXE}")
    print(" SERVIDOR INICIADO!")
    print(" Acesse no seu PC: http://localhost:5000")
    print("=" * 50 + "\n")

    app.run(host="0.0.0.0", port=5000, debug=False)