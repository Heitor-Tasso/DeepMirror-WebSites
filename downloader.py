"""
DeepMirror-WebSites - Fachada que mantém interface pública
"""
import os
import re
import shutil
import time
from urllib.parse import urlparse
from website_downloader.browser import BrowserController
from website_downloader.network import NetworkRecorder
from website_downloader.post_process import PostProcessor
from website_downloader.clean import clean_site
from pathlib import Path


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

        # 6.6. Trigger dynamic imports (Next.js/React code splitting)
        self.browser.trigger_dynamic_imports()

        # 6.7. CRITICAL: Extract CSS from framework manifests (Next.js __BUILD_MANIFEST)
        framework_css_urls = self.browser.extract_framework_manifests()

        # 7. Coletar todas as URLs de assets presentes no DOM antes de fechar o browser
        self.log("Coletando assets presentes no DOM para fallback...")
        dynamic_asset_urls = self.browser.collect_dynamic_asset_urls()

        # 7.5. Merge framework CSS with dynamic assets
        if framework_css_urls:
            dynamic_asset_urls.extend(framework_css_urls)

        # 8. Get final HTML
        if is_iframe and iframe_content:
            html_content = iframe_content
            self.log("Usando conteúdo extraído do iframe")
        else:
            html_content = self.browser.get_content()

        # 8. Log network capture stats
        self.network.log_stats()

        # 9. Close browser
        self.browser.close()

        # 9.5. FASE 3: Save all captured resources to disk before processing
        self.log("Salvando recursos capturados...")
        self.network.save_all_captured_resources()

        # 9.6. Fallback-download de qualquer asset do DOM que não foi capturado
        self.log("Verificando assets do DOM para fallback...")
        self.network.ensure_resources_downloaded(dynamic_asset_urls)

        # 9.7. Fallback-download de qualquer URL vista pelo browser que não foi salva nem ignorada
        self.log("Verificando todos os assets vistos pelo browser para fallback...")
        # Pega todos os URLs vistos pelo handler de resposta
        all_seen_urls = list(dict.fromkeys(url for url, status in self.network.all_seen_urls))
        # Remove duplicados e já baixados/ignorados
        ignored_urls = {url for url, _reason in self.network.ignored_resources}
        failed_urls = {url for url, _reason in self.network.failed_resources}
        already = set(self.network.resource_cache.keys()) | ignored_urls | failed_urls
        fallback_urls = [u for u in all_seen_urls if u not in already]
        if fallback_urls:
            self.log(f"   {len(fallback_urls)} URLs vistas não salvas, tentando fallback...")
            self.network.ensure_resources_downloaded(fallback_urls)

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

        # 13. Organize final artifact into raw/clean variants
        self.log("Organizando artefato final...")
        clean_site(self.output_dir, self.log_callback)

        # 14. FASE 3: Include serve.py selector script in download root
        self._create_serve_script()

        # 15. FASE 6: Generate final report
        elapsed = time.time() - start_time
        self.log(f"\nTempo total: {elapsed:.1f}s")

        self.network.generate_final_report()

        return True

    def _create_serve_script(self):
        """FASE 3: Create root serve.py selector script in output directory"""
        serve_template = Path(__file__).parent / 'templates' / 'serve_outside.py'
        serve_script_path = os.path.join(self.output_dir, 'serve.py')
        shutil.copy(serve_template, os.path.join(self.output_dir, 'serve.py'))

        # Make executable on Unix-like systems
        try:
            os.chmod(serve_script_path, 0o755)
        except:
            pass  # Windows doesn't support this

        self.log("   Seletor de servidor (serve.py) incluído no download")


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
