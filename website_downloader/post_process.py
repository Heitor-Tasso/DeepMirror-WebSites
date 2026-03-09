"""
Post-Processing - HTML/DOM transformations via BeautifulSoup.
File-based URL rewriting is handled by url_rewrite.URLRewriter.
"""
import os
import re
import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup, NavigableString
from . import TRACKING_SCRIPTS, SMOOTH_SCROLL_LIBS
from .url_rewrite import URLRewriter, rewrite_css_urls


class PostProcessor:
    def __init__(self, base_url, output_dir, log_callback, network_recorder):
        self.base_url = base_url
        self.output_dir = output_dir
        self.log = log_callback
        self.network = network_recorder
        self.rewriter = URLRewriter(base_url, output_dir, log_callback, network_recorder)

        # Path to the JS interceptor template
        self._interceptor_js_path = os.path.join(
            os.path.dirname(__file__), 'fetch_interceptor.js'
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Public entry point
    # ─────────────────────────────────────────────────────────────────────────

    def process_html(self, html_content):
        """Apply all HTML transformations and trigger file-based rewriting."""
        self.log("🔧 Processando HTML e assets...")
        soup = BeautifulSoup(html_content, 'html.parser')

        # DOM-level transformations
        self._remove_canvas_snapshots(soup)
        self._fix_scroll_blocking(soup)
        self._remove_wrapper_iframes(soup)
        self._process_stylesheets(soup)
        self._process_inline_styles(soup)
        self._process_scripts(soup)
        self._process_images(soup)
        self._process_inline_style_attrs(soup)
        self._process_favicons(soup)
        self._process_meta_images(soup)
        self._process_background_attrs(soup)
        self._fix_navigation_links(soup)
        self._handle_spa_frameworks(soup)
        self._remove_preconnects(soup)
        self._process_preloads(soup)
        self._remove_tracking_scripts(soup)

        # Inject fetch interceptor before serializing
        self._inject_fetch_interceptor(soup)

        html_output = str(soup)

        # File-based operations (safe — work on saved files, not the HTML string)
        self.rewriter.rewrite_css_files()
        self.rewriter.process_json_files()
        self.rewriter.remove_sourcemaps()

        # String-level HTML post-processing
        html_output = self.rewriter.rewrite_basenames_in_html(html_output)
        html_output = self.rewriter.rewrite_nextjs_images_in_html(html_output)

        return html_output

    def save_html(self, html_output):
        """Save final HTML to disk."""
        with open(os.path.join(self.output_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html_output)

    # ─────────────────────────────────────────────────────────────────────────
    # DOM transformations
    # ─────────────────────────────────────────────────────────────────────────

    def _remove_canvas_snapshots(self, soup):
        """Remove Playwright-captured canvas elements (width + height + data-engine)."""
        removed = 0
        for canvas in soup.find_all('canvas'):
            if canvas.has_attr('width') and canvas.has_attr('height') and canvas.has_attr('data-engine'):
                self.log(f"   Removendo canvas renderizado: {canvas.get('width')}x{canvas.get('height')}")
                canvas.decompose()
                removed += 1
        if removed:
            self.log(f"   Removidos {removed} canvas renderizados (Playwright snapshots)")

    def _fix_scroll_blocking(self, soup):
        """Remove scroll-blocking classes/attrs and inject minimal scroll-fix CSS."""
        self.log("🔧 Corrigindo problemas de scroll para visualização offline...")

        html_elem = soup.find('html')
        if html_elem:
            classes = html_elem.get('class', [])
            if isinstance(classes, str):
                classes = classes.split()
            lenis_cls = {'lenis', 'lenis-smooth', 'lenis-scrolling', 'lenis-stopped',
                         'has-scroll-smooth', 'has-scroll-init', 'locomotive-scroll'}
            new_cls = [c for c in classes if c.lower() not in lenis_cls]
            if new_cls != classes:
                html_elem['class'] = new_cls
                self.log("   Removidas classes Lenis/Locomotive do html")

        body = soup.find('body')
        if body:
            classes = body.get('class', [])
            if isinstance(classes, str):
                classes = classes.split()
            blocking = {'overflow-hidden', 'no-scroll', 'scroll-lock', 'fixed',
                        'lenis', 'lenis-smooth', 'has-scroll-smooth'}
            new_cls = [c for c in classes if c.lower() not in blocking]
            if 'items-center' in new_cls and 'flex' in new_cls:
                new_cls = ['items-start' if c == 'items-center' else c for c in new_cls]
                self.log("   Corrigida centralização vertical do body")
            if new_cls != classes:
                body['class'] = new_cls

        for elem in soup.find_all(class_=lambda c: c and any(
            x in str(c).lower() for x in ['scroll-container', 'smooth-scroll', 'lenis', 'locomotive']
        )):
            for attr in list(elem.attrs.keys()):
                if 'scroll' in attr.lower() or 'lenis' in attr.lower():
                    del elem[attr]

        scroll_fix_css = """
        /* Scroll fixes - MINIMAL SCOPE */
        html, body {
            overflow: auto !important;
            overflow-x: hidden !important;
            height: auto !important;
            min-height: 100% !important;
            scroll-behavior: auto !important;
        }
        .loader, .preloader, .loading, [class*="loader"], [class*="preloader"] {
            display: none !important;
            opacity: 0 !important;
        }
        html.lenis, html.lenis-smooth,
        body.lenis, body.lenis-smooth,
        .lenis-wrapper, .lenis-content,
        [data-lenis-prevent], [data-scroll-container] {
            overflow: visible !important;
            height: auto !important;
        }
        body.flex.items-center,
        body.flex.justify-center {
            align-items: flex-start !important;
            min-height: 100vh;
            height: auto !important;
        }
        main, #__next, #__nuxt, #app, .main-content {
            overflow: visible !important;
            height: auto !important;
        }
        """

        head = soup.find('head')
        if head:
            fix_style = soup.new_tag('style')
            fix_style['data-scroll-fix'] = 'true'
            fix_style.string = scroll_fix_css
            head.append(fix_style)
            self.log("   Injetado CSS para corrigir scroll")

        scripts_removed = 0
        for script in soup.find_all('script'):
            src = script.get('src', '') or ''
            text = script.string or ''
            if any(x in src.lower() for x in SMOOTH_SCROLL_LIBS):
                script.decompose()
                scripts_removed += 1
            elif any(x in text.lower() for x in ['new lenis', 'new locomotivescroll', 'smoothscroll']):
                script.decompose()
                scripts_removed += 1
        if scripts_removed:
            self.log(f"   Removidos {scripts_removed} scripts de smooth scroll")

    def _remove_wrapper_iframes(self, soup):
        """Remove preview/wrapper iframes from site builders."""
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '') or ''
            srcdoc = iframe.get('srcdoc', '')
            if srcdoc or 'preview' in str(iframe.get('class', '')).lower():
                iframe.decompose()

    def _process_stylesheets(self, soup):
        """Localize external stylesheets and rewrite their url() references."""
        self.log("Processando stylesheets...")
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if not href or href.startswith('data:'):
                continue

            for attr in ['integrity', 'crossorigin', 'nonce']:
                if link.has_attr(attr):
                    del link[attr]

            abs_url = urljoin(self.base_url, href)
            css_content = None

            if abs_url in self.network.network_resources:
                try:
                    css_content = self.network.network_resources[abs_url]['body'].decode('utf-8', errors='ignore')
                except Exception:
                    pass

            if not css_content:
                try:
                    response = self.network.session.get(abs_url, timeout=15, verify=False)
                    if response.status_code == 200:
                        css_content = response.text
                except Exception:
                    pass

            if css_content:
                css_content = rewrite_css_urls(css_content, abs_url, self.network)
                local_path = self.network._save_resource(abs_url, css_content.encode('utf-8'), 'text/css')
                if local_path:
                    link['href'] = local_path

    def _process_inline_styles(self, soup):
        """Rewrite url() in inline <style> tags."""
        self.log("Processando estilos inline...")
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                style_tag.string = rewrite_css_urls(style_tag.string, self.base_url, self.network)

    def _process_scripts(self, soup):
        """Localize external script src attributes."""
        self.log("Processando scripts...")
        for script in soup.find_all('script', src=True):
            src = script.get('src')
            if not src or src.startswith('data:'):
                continue
            local_path = self.network.get_resource(src)
            if local_path and local_path != src:
                script['src'] = local_path
                for attr in ['integrity', 'crossorigin', 'nonce']:
                    if script.has_attr(attr):
                        del script[attr]

    def _process_srcset(self, srcset, base=None):
        """Rewrite a srcset attribute value."""
        if not srcset:
            return srcset

        def _encode(path):
            return path.replace(' ', '%20')

        new_parts = []
        for part in srcset.split(','):
            part = part.strip()
            if not part:
                continue

            match = re.match(r'^(.+)\s+(\d+(?:\.\d+)?[wx])$', part)
            if match:
                url, descriptor = match.group(1).strip(), match.group(2)
            else:
                url, descriptor = part.strip(), ''

            if url.startswith('data:'):
                new_parts.append(part)
                continue

            if '/_next/image' in url and 'url=' in url:
                from urllib.parse import parse_qs, urlparse, unquote
                try:
                    parsed = urlparse(url)
                    query_params = parse_qs(parsed.query)
                    if 'url' in query_params:
                        original_url = unquote(query_params['url'][0])
                        full_url = urljoin(base or self.base_url, url)
                        resolved = self.network.get_resource(full_url, base)
                        if resolved == full_url:
                            resolved = None
                        if not resolved:
                            resolved = self.network.get_resource(original_url, base)
                            if resolved == original_url:
                                resolved = None
                        if resolved:
                            encoded = _encode(resolved)
                            new_parts.append(f"{encoded} {descriptor}" if descriptor else encoded)
                            continue
                except Exception:
                    pass

            local_path = self.network.get_resource(url, base)
            if local_path and local_path != url:
                encoded = _encode(local_path)
                new_parts.append(f"{encoded} {descriptor}" if descriptor else encoded)
            else:
                encoded = _encode(part) if ' ' in url else part
                if descriptor and ' ' in url:
                    encoded = f"{_encode(url)} {descriptor}"
                new_parts.append(encoded)

        return ', '.join(new_parts) if new_parts else ''

    def _process_images(self, soup):
        """Localize src, srcset, data-src, poster attributes on media elements."""
        self.log("Processando imagens...")
        for elem in soup.find_all(['img', 'source', 'video', 'audio', 'picture', 'input']):
            for attr in ['data-src', 'data-original', 'data-lazy-src', 'data-url', 'data-image', 'data-bg']:
                if elem.get(attr):
                    lazy_src = elem[attr]
                    local_path = self.network.get_resource(lazy_src)
                    if local_path and local_path != lazy_src:
                        elem['src'] = local_path
                        del elem[attr]
                    break

            src = elem.get('src')
            if src and not src.startswith('data:'):
                if '/_next/image' in src and 'url=' in src:
                    from urllib.parse import parse_qs, urlparse, unquote
                    try:
                        parsed = urlparse(src)
                        query_params = parse_qs(parsed.query)
                        if 'url' in query_params:
                            original_url = unquote(query_params['url'][0])
                            full_url = urljoin(self.base_url, src)
                            local_path = self.network.get_resource(full_url)
                            if local_path == full_url:
                                local_path = None
                            if not local_path:
                                local_path = self.network.get_resource(original_url)
                                if local_path == original_url:
                                    local_path = None
                            if local_path:
                                elem['src'] = local_path
                            continue
                    except Exception:
                        pass
                local_path = self.network.get_resource(src)
                if local_path and local_path != src:
                    elem['src'] = local_path

            srcset = elem.get('srcset')
            if srcset:
                elem['srcset'] = self._process_srcset(srcset)

            data_srcset = elem.get('data-srcset')
            if data_srcset:
                elem['data-srcset'] = self._process_srcset(data_srcset)

            if elem.name == 'video' and elem.get('poster'):
                poster = elem['poster']
                local_path = self.network.get_resource(poster)
                if local_path and local_path != poster:
                    elem['poster'] = local_path

    def _process_inline_style_attrs(self, soup):
        """Rewrite url() inside inline style='...' attributes."""
        self.log("Processando atributos de estilo inline...")
        for elem in soup.find_all(attrs={'style': True}):
            style = elem['style']
            if 'url(' in style:
                elem['style'] = rewrite_css_urls(style, self.base_url, self.network)

    def _process_favicons(self, soup):
        """Localize favicon and apple-touch-icon link tags."""
        for link in soup.find_all('link'):
            if link.get('href') and link.get('rel'):
                rel = link['rel']
                if isinstance(rel, list):
                    rel = ' '.join(rel)
                if any(x in rel.lower() for x in ['icon', 'apple-touch', 'manifest']):
                    href = link['href']
                    if not href.startswith('data:'):
                        local_path = self.network.get_resource(href)
                        if local_path and local_path != href:
                            link['href'] = local_path

    def _process_meta_images(self, soup):
        """Localize og:image and similar meta tag URLs."""
        for meta in soup.find_all('meta', attrs={'content': True}):
            prop = meta.get('property', '') or meta.get('name', '')
            if 'image' in prop.lower():
                content = meta['content']
                if content and not content.startswith('data:') and ('http' in content or content.startswith('/')):
                    local_path = self.network.get_resource(content)
                    if local_path and local_path != content:
                        meta['content'] = local_path

    def _process_background_attrs(self, soup):
        """Localize data-background attribute values."""
        for elem in soup.find_all(attrs={'data-background': True}):
            bg = elem['data-background']
            if bg and not bg.startswith('data:'):
                local_path = self.network.get_resource(bg)
                if local_path and local_path != bg:
                    elem['data-background'] = local_path

    def _fix_navigation_links(self, soup):
        """Replace internal absolute links with # (they won't work offline)."""
        self.log("Corrigindo links de navegação...")
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href == '/' or (href.startswith('/') and not href.startswith('//')):
                a['href'] = '#'

    def _detect_nextjs(self, soup):
        """Heuristic detection of Next.js pages."""
        for script in soup.find_all('script'):
            text = script.string or ''
            if '__NEXT_DATA__' in script.get('id', '') or '__NEXT_DATA__' in text:
                return True
            if 'self.__next' in text:
                return True
        for script in soup.find_all('script', src=True):
            src = script['src']
            if '_next/' in src or 'webpack' in src.lower():
                return True
        for link in soup.find_all('link'):
            if '_next/' in link.get('href', ''):
                return True
        return False

    def _handle_spa_frameworks(self, soup):
        """Remove only inline hydration scripts from SPAs (Gatsby, Next.js, Nuxt)."""
        is_gatsby = soup.find(id='___gatsby') is not None
        is_nextjs = soup.find(id='__next') is not None or self._detect_nextjs(soup)
        is_nuxt = soup.find(id='__nuxt') is not None

        if not (is_gatsby or is_nextjs or is_nuxt):
            return

        framework = 'Gatsby' if is_gatsby else ('Next.js' if is_nextjs else 'Nuxt')
        self.log(f"🛡️ Detectado {framework} - removendo APENAS scripts de hydration...")

        removed = 0
        for script in soup.find_all('script'):
            if script.get('src'):
                continue
            text = script.string or ''
            if any(marker in text for marker in ['self.__next_f', '__NEXT_DATA__', 'GATSBY___', '__NUXT__']):
                script.decompose()
                removed += 1

        self.log(f"   Removidos {removed} scripts de hydration do {framework}")

    def _remove_preconnects(self, soup):
        """Remove preconnect and dns-prefetch links (useless offline)."""
        removed = 0
        for link in soup.find_all('link', rel=lambda r: r and any(x in r for x in ['preconnect', 'dns-prefetch'])):
            link.decompose()
            removed += 1
        if removed:
            self.log(f"   Removidos {removed} preconnects/dns-prefetch")

    def _process_preloads(self, soup):
        """Localize preload/prefetch/modulepreload href attributes."""
        self.log("Processando preloads...")
        processed = 0
        for link in soup.find_all('link', rel=lambda r: r and any(x in r for x in ['preload', 'prefetch', 'modulepreload'])):
            href = link.get('href')
            if href and not href.startswith(('data:', 'blob:', 'assets/')):
                local_path = self.network.get_resource(href)
                if local_path and local_path != href:
                    link['href'] = local_path
                    processed += 1
        if processed:
            self.log(f"   {processed} preloads reescritos")

    def _remove_tracking_scripts(self, soup):
        """Remove analytics/tracking script tags."""
        self.log("🛡️ Removendo scripts de tracking...")
        removed = 0
        for script in soup.find_all('script', src=True):
            src = script.get('src', '')
            if any(pattern in src.lower() for pattern in TRACKING_SCRIPTS):
                script.decompose()
                removed += 1
        if removed:
            self.log(f"   Removidos {removed} scripts de tracking")

    def _inject_fetch_interceptor(self, soup):
        """Read the JS template, inject resource map, and prepend to <head>."""
        self.log("💉 Injetando fetch interceptor aprimorado...")

        resource_map = self.network.get_resource_map()
        if not resource_map:
            self.log("   Resource map vazio, interceptor não injetado")
            return

        # Load JS template from external file
        try:
            with open(self._interceptor_js_path, 'r', encoding='utf-8') as f:
                js_template = f.read()
        except OSError as e:
            self.log(f"   Erro ao ler fetch_interceptor.js: {e}")
            return

        # Build resource map loading code
        if len(resource_map) > 500:
            map_filename = 'resource-map.json'
            map_path = os.path.join(self.output_dir, 'assets', map_filename)
            with open(map_path, 'w', encoding='utf-8') as f:
                json.dump(resource_map, f)
            map_load_code = f"const response = await fetch('assets/{map_filename}');\n    const resourceMap = await response.json();"
        else:
            map_load_code = f"const resourceMap = {json.dumps(resource_map, ensure_ascii=False)};"

        # Replace placeholder in template
        interceptor_script = js_template.replace('/* __RESOURCE_MAP_CODE__ */', map_load_code)

        head = soup.find('head')
        if head:
            script_tag = soup.new_tag('script')
            script_tag['data-fetch-interceptor'] = 'true'
            script_tag.append(NavigableString(interceptor_script))
            if head.contents:
                head.insert(0, script_tag)
            else:
                head.append(script_tag)
            self.log(f"   Fetch interceptor injetado ({len(resource_map)} mapeamentos)")
        else:
            self.log("   <head> não encontrado, interceptor não injetado")
