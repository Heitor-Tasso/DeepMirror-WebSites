#!/usr/bin/env python3
"""
Servidor Local para Site Baixado via DeepMirror-WebSites
Execute este script para visualizar o site offline.

Uso:
    python3 serve.py
    python serve.py

Requisitos: Python 3.7+
"""
import http.server
import socketserver
import webbrowser
import os
import sys
from pathlib import Path

# MIME types para formatos especiais
MIME_TYPES = {
    '.wasm': 'application/wasm',
    '.glb': 'model/gltf-binary',
    '.gltf': 'model/gltf+json',
    '.riv': 'application/octet-stream',
    '.webp': 'image/webp',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.ttf': 'font/ttf',
    '.otf': 'font/otf',
    '.js': 'application/javascript',
    '.mjs': 'application/javascript',
    '.json': 'application/json',
}


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler with CORS and special MIME types"""

    def do_GET(self):
        """
        Serve files with basename-prefix fallback for hash-suffixed filenames.

        When a file is not found at the exact path (e.g. /assets/chunk.js),
        look for a file whose stem starts with 'chunk_' in the same directory
        (e.g. chunk_03efa892a380.js). This transparently resolves ES dynamic
        imports and any other request that uses the original filename while the
        saved file has a hash suffix appended by the downloader.
        """
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            filename = os.path.basename(path)
            directory = os.path.dirname(path)
            if '.' in filename and os.path.isdir(directory):
                stem, _, ext = filename.rpartition('.')
                ext = '.' + ext
                candidates = [
                    f for f in os.listdir(directory)
                    if os.path.isfile(os.path.join(directory, f))
                    and os.path.splitext(f)[1] == ext
                    and os.path.splitext(f)[0].startswith(stem + '_')
                ]
                if len(candidates) == 1:
                    self.path = os.path.join(os.path.dirname(self.path), candidates[0])
        super().do_GET()

    def end_headers(self):
        # CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        # Cache control
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()

    def guess_type(self, path):
        """Override guess_type to handle special MIME types"""
        # Get extension
        ext = Path(path).suffix.lower()

        # Check custom MIME types first
        if ext in MIME_TYPES:
            return MIME_TYPES[ext]

        # Fallback to default
        return super().guess_type(path)

    def log_request(self, code='-', size='-'):
        """Log ALL requests — Zero Suppression policy"""
        super().log_request(code, size)


def find_available_port(start_port=8000, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socketserver.TCPServer(("", port), None) as s:
                return port
        except OSError:
            continue
    raise RuntimeError(f"Não foi possível encontrar porta disponível entre {start_port} e {start_port + max_attempts}")


def main():
    # Change to script directory
    os.chdir(Path(__file__).parent)

    # Find available port
    try:
        PORT = find_available_port(8000)
    except RuntimeError as e:
        print(f"Erro: {e}")
        sys.exit(1)

    # Create server
    Handler = CustomHTTPRequestHandler
    httpd = socketserver.TCPServer(("", PORT), Handler)

    url = f"http://localhost:{PORT}"

    print("=" * 60)
    print("DeepMirror WebSites - Servidor Local")
    print("=" * 60)
    print(f"\nServidor rodando em: {url}")
    print(f"Diretório: {os.getcwd()}")
    print("\nAbrindo navegador...")
    print("\n Para parar o servidor: Ctrl+C")
    print("=" * 60 + "\n")

    # Open browser
    try:
        webbrowser.open(url)
    except:
        print(" Não foi possível abrir o navegador automaticamente.")
        print(f"   Acesse manualmente: {url}")

    # Start server
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServidor encerrado pelo usuário.")
        httpd.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()
