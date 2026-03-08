"""
Website Downloader - Fachada que mantém interface pública
"""
import os
import re
import shutil
import time
from urllib.parse import urlparse
from website_downloader.browser import BrowserController
from website_downloader.network import NetworkRecorder
from website_downloader.post_process import PostProcessor


class WebsiteDownloader:
    """
    Main downloader class - maintains public interface for app.py
    """
    def __init__(self, url, output_dir, log_callback=None):
        self.url = url
        self.output_dir = output_dir
        self.assets_dir = os.path.join(output_dir, 'assets')
        self.log_callback = log_callback or (lambda msg: print(msg))

        # Clean and create output directories
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(self.assets_dir)

        # Initialize components
        self.browser = BrowserController(self.log_callback)
        self.network = NetworkRecorder(url, self.assets_dir, self.log_callback)
        self.post_processor = None  # Will be initialized after browser sets base_url

    def log(self, message):
        """Send log message to callback"""
        self.log_callback(message)

    def process(self):
        """
        Main processing method - orchestrates the download flow
        """
        # FASE 6: Track total time
        start_time = time.time()

        # 1. Launch browser and setup network recording
        page = self.browser.launch()
        page.on("response", self.network.get_response_handler())

        # 2. Navigate to URL
        self.browser.goto(self.url)

        # 3. Setup requests session with cookies
        cookies = self.browser.get_cookies()
        self.network.setup_session(cookies)

        # Update network recorder's base_url after navigation (handles redirects)
        self.network.base_url = self.browser.base_url

        # 4. Check for iframe content
        iframe_content, is_iframe = self.browser.extract_iframe_content()

        # 5. Stimulate page if not iframe
        if not is_iframe:
            self.browser.scroll_page()
            self.browser.simulate_interactions()
            # WebGL canvas interactions for texture loading
            self.browser.interact_with_webgl_canvases()

        # 6. Wait for network to settle (XHRs, delayed resources, WebGL textures)
        self.browser.wait_for_network_idle()

        # 6.5. Wait for CSS-in-JS to inject (styled-components, emotion, etc.)
        self.browser.wait_for_css_injection()

        # 7. Get final HTML
        if is_iframe and iframe_content:
            html_content = iframe_content
            self.log("✨ Usando conteúdo extraído do iframe")
        else:
            html_content = self.browser.get_content()

        # 8. Log network capture stats
        self.network.log_stats()

        # 9. Close browser
        self.browser.close()

        # 9.5. FASE 3: Save all captured resources to disk before processing
        self.log("💾 Salvando recursos capturados...")
        self.network.save_all_captured_resources()

        # 10. Initialize post-processor with final base_url
        self.post_processor = PostProcessor(
            self.browser.base_url,
            self.output_dir,
            self.log_callback,
            self.network
        )

        # 11. Process HTML
        html_output = self.post_processor.process_html(html_content)

        # 12. Save HTML
        self.post_processor.save_html(html_output)

        # 13. FASE 3: Include serve.py script in download
        self._create_serve_script()

        # 14. FASE 6: Generate final report
        elapsed = time.time() - start_time
        self.log(f"\n⏱️ Tempo total: {elapsed:.1f}s")

        self.network.generate_final_report()

        return True

    def _create_serve_script(self):
        """FASE 3: Create root serve.py selector script in output directory"""
        serve_selector_content = '''#!/usr/bin/env python3
"""
Servidor Local para Site Baixado via DeepMirror-WebSites
Escolha entre versão RAW ou CLEAN do site.

Uso:
    python3 serve.py
    python serve.py

Requisitos: Python 3.7+
"""
import os
import sys
import subprocess
from pathlib import Path


def main():
    print("=" * 60)
    print("🪞 DeepMirror WebSites - Seletor de Versão")
    print("=" * 60)
    print("\\nQual versão do site você deseja visualizar?\\n")
    print("1. RAW   - Versão completa com todos os recursos")
    print("2. CLEAN - Versão otimizada para IA (sem canvas/scripts)")
    print("\\n" + "=" * 60)

    while True:
        choice = input("\\nEscolha (1/2): ").strip()

        if choice == "1":
            folder = "raw"
            break
        elif choice == "2":
            folder = "clean"
            break
        else:
            print("❌ Opção inválida. Digite 1 ou 2.")

    # Get path to serve.py in selected folder
    serve_path = Path(__file__).parent / folder / "serve.py"

    if not serve_path.exists():
        print(f"\\n❌ Erro: Arquivo {serve_path} não encontrado!")
        sys.exit(1)

    print(f"\\n✨ Iniciando versão {folder.upper()}...\\n")

    # Execute the serve.py in the selected folder
    try:
        subprocess.run([sys.executable, str(serve_path)])
    except KeyboardInterrupt:
        print("\\n\\n🛑 Servidor encerrado pelo usuário.")
        sys.exit(0)


if __name__ == "__main__":
    main()
'''

        serve_script_path = os.path.join(self.output_dir, 'serve.py')
        with open(serve_script_path, 'w', encoding='utf-8') as f:
            f.write(serve_selector_content)

        # Make executable on Unix-like systems
        try:
            os.chmod(serve_script_path, 0o755)
        except:
            pass  # Windows doesn't support this

        self.log("   ✅ Seletor de servidor (serve.py) incluído no download")


def get_site_name(url):
    """Extract a clean site name from URL for the zip filename"""
    parsed = urlparse(url)
    # Get domain without www
    domain = parsed.netloc.replace('www.', '')
    # Clean special characters
    clean_name = re.sub(r'[^a-zA-Z0-9.-]', '_', domain)
    # Add path info if present (cleaned)
    if parsed.path and parsed.path != '/':
        path_part = re.sub(r'[^a-zA-Z0-9]', '_', parsed.path.strip('/'))[:30]
        clean_name = f"{clean_name}_{path_part}"
    return clean_name


def zip_directory(folder_path, output_path):
    """Create a zip file from a directory"""
    base_name = output_path.replace('.zip', '')
    shutil.make_archive(base_name, 'zip', folder_path)
    return base_name + '.zip'
