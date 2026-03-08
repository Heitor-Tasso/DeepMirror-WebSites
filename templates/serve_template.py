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
        print(f"❌ Erro: {e}")
        sys.exit(1)

    # Create server
    Handler = CustomHTTPRequestHandler
    httpd = socketserver.TCPServer(("", PORT), Handler)

    url = f"http://localhost:{PORT}"

    print("=" * 60)
    print("🪞 DeepMirror WebSites - Servidor Local")
    print("=" * 60)
    print(f"\n🌐 Servidor rodando em: {url}")
    print(f"📁 Diretório: {os.getcwd()}")
    print("\n✨ Abrindo navegador...")
    print("\n⚠️  Para parar o servidor: Ctrl+C")
    print("=" * 60 + "\n")

    # Open browser
    try:
        webbrowser.open(url)
    except:
        print("⚠️  Não foi possível abrir o navegador automaticamente.")
        print(f"   Acesse manualmente: {url}")

    # Start server
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor encerrado pelo usuário.")
        httpd.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()
