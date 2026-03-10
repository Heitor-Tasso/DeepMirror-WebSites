"""
Browser Controller - Playwright operations
"""
import html
from playwright.sync_api import sync_playwright
from . import (
    BROWSER_TIMEOUT, BROWSER_ARGS, USER_AGENT,
    MAX_SCROLL_ITERATIONS, INTERACTION_WAIT
)

class BrowserController:
    def play_all_videos(self, wait_time=8000):
        """
        Simula play em todos os <video> do DOM para forçar carregamento de HLS/chunks.
        """
        try:
            video_count = self.page.evaluate("""() => document.querySelectorAll('video').length""")
            if video_count == 0:
                self.log("Nenhum <video> encontrado para simular play.")
                return
            self.log(f"Simulando play em {video_count} <video>(s)...")
            self.page.evaluate("""
                () => {
                    document.querySelectorAll('video').forEach(v => {
                        try { v.muted = true; v.play(); } catch(e){}
                    });
                }
            """)
            self.page.wait_for_timeout(wait_time)
            self.log(f"Aguardou {wait_time/1000:.1f}s após play em vídeos.")
        except Exception as e:
            self.log(f"Erro ao simular play em vídeos: {e}")
    def __init__(self, log_callback):
        self.log = log_callback
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.base_url = None

    def launch(self):
        """Launch browser and create page"""
        self.log("Iniciando navegador...")
        self.playwright = sync_playwright().start()

        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=BROWSER_ARGS
        )

        self.context = self.browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=1,
        )

        self.page = self.context.new_page()
        return self.page

    def goto(self, url):
        """Navigate to URL"""
        self.log(f"Carregando {url}...")
        try:
            self.page.goto(url, wait_until='load', timeout=BROWSER_TIMEOUT)
            self.log("- Página carregada (load)")
            self.page.wait_for_timeout(3000)
            self.log("- Recursos adicionais carregados")
        except Exception as e:
            self.log(f"Aviso de carregamento: {str(e)[:100]}")
            self.log("Tentando continuar mesmo assim...")

        self.base_url = self.page.url
        self.page.wait_for_timeout(2000)

    def extract_iframe_content(self):
        """
        Check if the page content is inside an iframe (common in site builders)
        and extract the actual content if found.
        """
        # Check for srcdoc iframes
        srcdoc_iframe = self.page.query_selector('iframe[srcdoc]')
        if srcdoc_iframe:
            self.log("Detectado iframe com srcdoc - extraindo conteúdo real...")
            srcdoc = srcdoc_iframe.get_attribute('srcdoc')
            if srcdoc:
                decoded_content = html.unescape(srcdoc)
                return decoded_content, True

        # Check for preview frames
        preview_selectors = [
            'iframe[class*="preview"]',
            'iframe[class*="site-frame"]',
            'iframe[class*="canvas"]',
            'iframe[id*="preview"]',
            '#preview-iframe',
            '.preview-frame iframe',
            '[role="tabpanel"] iframe',
            '[data-testid*="preview"] iframe',
        ]

        for selector in preview_selectors:
            iframe = self.page.query_selector(selector)
            if iframe:
                frames = self.page.frames
                for frame in frames:
                    if frame != self.page.main_frame and frame.url and frame.url != 'about:blank':
                        try:
                            self.log(f"Detectado iframe de preview - extraindo de {frame.url[:50]}...")
                            content = frame.content()
                            if len(content) > 500:
                                self.base_url = frame.url
                                return content, True
                        except:
                            pass

        # Check all frames including srcdoc
        for frame in self.page.frames:
            if frame != self.page.main_frame:
                try:
                    frame_url = frame.url
                    if frame_url == 'about:srcdoc':
                        content = frame.content()
                        if len(content) > 1000:
                            self.log("Detectado iframe srcdoc via frame - extraindo conteúdo...")
                            return content, True
                except:
                    pass

        # Check if main content is suspiciously small
        main_content = self.page.content()
        body = self.page.query_selector('body')
        if body:
            direct_children = self.page.query_selector_all('body > *')
            iframes = self.page.query_selector_all('iframe')

            if len(direct_children) <= 5 and len(iframes) > 0:
                for frame in self.page.frames:
                    if frame != self.page.main_frame:
                        try:
                            content = frame.content()
                            if len(content) > len(main_content) * 0.3:
                                self.log("Detectado wrapper com iframe - usando conteúdo do frame...")
                                if frame.url and frame.url not in ['about:blank', 'about:srcdoc']:
                                    self.base_url = frame.url
                                return content, True
                        except:
                            pass

        return None, False

    def scroll_page(self):
        """Scroll the page to trigger lazy loading"""
        self.log("Rolando página para carregar conteúdo lazy...")
        try:
            # Disable smooth scroll libraries
            self.page.evaluate("""
                () => {
                    if (window.lenis) {
                        try { window.lenis.destroy(); } catch(e) {}
                    }
                    if (window.locomotiveScroll) {
                        try { window.locomotiveScroll.destroy(); } catch(e) {}
                    }
                    document.documentElement.style.scrollBehavior = 'auto';
                    document.body.style.scrollBehavior = 'auto';

                    if (getComputedStyle(document.body).overflow === 'hidden') {
                        document.body.style.overflow = 'auto';
                    }
                    if (getComputedStyle(document.documentElement).overflow === 'hidden') {
                        document.documentElement.style.overflow = 'auto';
                    }
                }
            """)

            # Find scroll container
            scroll_container = self.page.evaluate("""
                () => {
                    const selectors = [
                        '[data-scroll-container]',
                        '.scroll-container',
                        '.smooth-scroll',
                        'main',
                        '#__next',
                        '#__nuxt',
                        '#app'
                    ];

                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.scrollHeight > window.innerHeight) {
                            return sel;
                        }
                    }
                    return null;
                }
            """)

            if scroll_container:
                self.log(f"Detectado container de scroll customizado: {scroll_container}")

            total_height = self.page.evaluate("Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
            viewport_height = self.page.evaluate("window.innerHeight")

            iteration = 0
            current = 0
            while current < total_height and iteration < MAX_SCROLL_ITERATIONS:
                self.page.evaluate(f"""
                    (pos) => {{
                        window.scrollTo(0, pos);
                        document.documentElement.scrollTop = pos;
                        document.body.scrollTop = pos;

                        const containers = document.querySelectorAll('[data-scroll-container], .scroll-container, main');
                        containers.forEach(c => {{ c.scrollTop = pos; }});
                    }}
                """, current)

                self.page.wait_for_timeout(600)
                current += viewport_height
                iteration += 1

                new_height = self.page.evaluate("Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
                if new_height > total_height:
                    total_height = new_height

            # Scroll back to top
            self.page.evaluate("""
                () => {
                    window.scrollTo(0, 0);
                    document.documentElement.scrollTop = 0;
                    document.body.scrollTop = 0;
                }
            """)
            self.page.wait_for_timeout(1000)
        except Exception as e:
            self.log(f"Erro no scroll: {e}")

    def simulate_interactions(self):
        """Simulate mouse movements and hovers to trigger lazy loading"""
        self.log("Simulando interações para carregar recursos dinâmicos...")

        try:
            viewport_height = self.page.evaluate("window.innerHeight")
            viewport_width = self.page.evaluate("window.innerWidth")

            # Move mouse to various positions to trigger hover effects
            positions = [
                (viewport_width * 0.5, viewport_height * 0.3),  # Center-top
                (viewport_width * 0.2, viewport_height * 0.5),  # Left-middle
                (viewport_width * 0.8, viewport_height * 0.5),  # Right-middle
                (viewport_width * 0.5, viewport_height * 0.7),  # Center-bottom
            ]

            for x, y in positions:
                try:
                    self.page.mouse.move(x, y)
                    self.page.wait_for_timeout(INTERACTION_WAIT)
                except:
                    pass

            # Hover over video elements to trigger player initialization
            try:
                videos = self.page.query_selector_all('video')
                for video in videos:
                    box = video.bounding_box()
                    if box and box['width'] > 50 and box['height'] > 50:
                        cx = box['x'] + box['width'] / 2
                        cy = box['y'] + box['height'] / 2
                        self.page.mouse.move(cx, cy)
                        self.page.wait_for_timeout(1000)
            except Exception:
                pass

            self.log("   Interações simuladas")
        except Exception as e:
            self.log(f"Erro ao simular interações: {e}")

    def interact_with_webgl_canvases(self):
        """Simulate focused interactions on WebGL canvas elements to trigger texture loading"""
        self.log("Detectando e interagindo com canvas WebGL...")

        try:
            # Find all canvas elements
            canvases = self.page.query_selector_all('canvas')

            if not canvases:
                self.log("   Nenhum canvas encontrado")
                return

            webgl_canvases = []
            for canvas in canvases:
                try:
                    box = canvas.bounding_box()
                    # Filter for substantial canvases (likely 3D scenes)
                    if box and box['width'] > 100 and box['height'] > 100:
                        webgl_canvases.append((canvas, box))
                except:
                    pass

            if not webgl_canvases:
                self.log("   Nenhum canvas WebGL significativo encontrado")
                return

            self.log(f"   Encontrados {len(webgl_canvases)} canvas para interação")

            # First pass: hover and center interaction
            for canvas, box in webgl_canvases:
                try:
                    center_x = box['x'] + box['width'] / 2
                    center_y = box['y'] + box['height'] / 2

                    # Hover over canvas center
                    self.page.mouse.move(center_x, center_y)
                    self.page.wait_for_timeout(1500)

                    # Sweep pattern: corners and center points
                    sweep_points = [
                        (0.2, 0.2),  # top-left
                        (0.8, 0.2),  # top-right
                        (0.5, 0.5),  # center
                        (0.2, 0.8),  # bottom-left
                        (0.8, 0.8),  # bottom-right
                    ]

                    for x_pct, y_pct in sweep_points:
                        x = box['x'] + box['width'] * x_pct
                        y = box['y'] + box['height'] * y_pct
                        self.page.mouse.move(x, y)
                        self.page.wait_for_timeout(500)

                    # Wait for texture fetches
                    self.page.wait_for_timeout(3000)
                except:
                    pass

            self.log("   Primeiro pass de interações concluído")

            # Wait for initial assets to load
            self.page.wait_for_timeout(5000)

            # Second pass: repeat center hovers (for assets that depend on first batch)
            for canvas, box in webgl_canvases:
                try:
                    center_x = box['x'] + box['width'] / 2
                    center_y = box['y'] + box['height'] / 2
                    self.page.mouse.move(center_x, center_y)
                    self.page.wait_for_timeout(2000)
                except:
                    pass

            self.log("   Segundo pass de interações concluído")

            # Extended wait for larger textures and async loads
            self.page.wait_for_timeout(8000)

            self.log("   Aguardando carregamento assíncrono de texturas...")

            # NOVO: Simular play em todos os vídeos após interações de canvas
            self.play_all_videos(wait_time=8000)

        except Exception as e:
            self.log(f"Erro ao interagir com canvas: {e}")

    def wait_for_css_injection(self, timeout=10000):
        """
        Wait for CSS-in-JS libraries (styled-components, emotion, etc.) to inject styles.

        Next.js and modern SPAs use CSS-in-JS that injects <style> tags dynamically.
        We wait until we see substantive <style> tags in the DOM.
        """
        self.log("💅 Aguardando injeção de CSS-in-JS...")

        try:
            # Wait for <style> tags with data-styled or substantive content
            self.page.wait_for_function("""
                () => {
                    const styles = document.querySelectorAll('style');
                    if (styles.length === 0) return false;

                    // Check for styled-components
                    for (const style of styles) {
                        if (style.hasAttribute('data-styled') && style.textContent.length > 100) {
                            return true;
                        }
                    }

                    // Check for any substantive inline styles (CSS-in-JS injected)
                    let totalLength = 0;
                    for (const style of styles) {
                        totalLength += style.textContent.length;
                    }

                    // If we have >2KB of CSS injected, assume it's ready
                    return totalLength > 2000;
                }
            """, timeout=timeout)

            self.log("   CSS-in-JS detectado e carregado")
            # Extra wait for fonts and final rendering
            self.page.wait_for_timeout(2000)
        except:
            self.log("   Timeout aguardando CSS-in-JS (pode não usar styled-components)")

    def wait_for_network_idle(self, timeout=30000, idle_time=10000):
        """
        Wait for network activity to settle intelligently.
        Monitors network requests and waits for idle_time ms of silence.

        Args:
            timeout: Maximum time to wait (default 30s)
            idle_time: Time of silence to consider network idle (default 10s)
        """
        self.log("Aguardando recursos adicionais (monitorando rede)...")

        import time
        start_time = time.time() * 1000  # Convert to milliseconds
        last_request_time = start_time
        request_count = 0

        # Track network requests
        def on_request(request):
            nonlocal last_request_time, request_count
            # Only track resource requests (not document/navigation)
            if request.resource_type in ['image', 'script', 'stylesheet', 'font', 'xhr', 'fetch', 'media', 'other']:
                last_request_time = time.time() * 1000
                request_count += 1

        # Attach listener
        self.page.on('request', on_request)

        # Wait loop
        while True:
            current_time = time.time() * 1000
            elapsed = current_time - start_time
            idle_duration = current_time - last_request_time

            # Check if we've been idle long enough
            if idle_duration >= idle_time:
                self.log(f"   Rede silenciosa por {idle_duration/1000:.1f}s ({request_count} requests capturados)")
                break

            # Check timeout
            if elapsed >= timeout:
                self.log(f"   Timeout atingido ({timeout/1000:.0f}s, {request_count} requests capturados)")
                break

            # Small sleep to avoid busy loop
            self.page.wait_for_timeout(100)

    def collect_dynamic_asset_urls(self):
        """
        Coleta todas as URLs de assets presentes no DOM (css, js, img, video, audio, source, object, iframe, preload, srcset).
        """
        try:
            urls = self.page.evaluate("""
                () => {
                    const urls = new Set();
                    // Stylesheets
                    document.querySelectorAll('link[rel="stylesheet"]').forEach(l => l.href && urls.add(l.href));
                    // Scripts
                    document.querySelectorAll('script[src]').forEach(s => s.src && urls.add(s.src));
                    // Imagens
                    document.querySelectorAll('img[src]').forEach(i => i.src && urls.add(i.src));
                    // Vídeos e Áudios
                    document.querySelectorAll('video[src], audio[src]').forEach(m => m.src && urls.add(m.src));
                    // <source src>
                    document.querySelectorAll('source[src]').forEach(s => s.src && urls.add(s.src));
                    // <object data>
                    document.querySelectorAll('object[data]').forEach(o => o.data && urls.add(o.data));
                    // <iframe src>
                    document.querySelectorAll('iframe[src]').forEach(f => f.src && urls.add(f.src));
                    // <link rel="preload">
                    document.querySelectorAll('link[rel="preload"]').forEach(l => l.href && urls.add(l.href));
                    // <link rel="preload" as="image"> (srcset)
                    document.querySelectorAll('img[srcset], source[srcset]').forEach(el => {
                        if (el.srcset) {
                            el.srcset.split(',').forEach(src => {
                                const url = src.trim().split(' ')[0];
                                if (url) urls.add(url);
                            });
                        }
                    });
                    return Array.from(urls);
                }
            """)
            self.log(f"   {len(urls)} asset(s) presentes no DOM para fallback")
            return urls
        except Exception as e:
            self.log(f"   Erro ao coletar assets do DOM: {e}")
            return []

    def get_cookies(self):
        """Get browser cookies for requests session"""
        return self.context.cookies()

    def get_content(self):
        """Get page HTML content"""
        return self.page.content()

    def close(self):
        """Close browser"""
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
