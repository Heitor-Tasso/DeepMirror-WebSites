"""
Post-Processing - HTML/CSS rewriting and cleanup
REFACTORED: Surgical URL rewriting to avoid breaking JS syntax
"""
import os
import re
import json
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from . import TRACKING_SCRIPTS, SMOOTH_SCROLL_LIBS


class PostProcessor:
    def __init__(self, base_url, output_dir, log_callback, network_recorder):
        self.base_url = base_url
        self.output_dir = output_dir
        self.log = log_callback
        self.network = network_recorder

    def process_html(self, html_content):
        """Process HTML and apply all transformations"""
        self.log("🔧 Processando HTML e assets...")
        soup = BeautifulSoup(html_content, 'html.parser')

        # Apply all processing steps
        self._remove_canvas_placeholder_comments(soup)
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

        # Fase 4: Extra processors
        self._remove_preconnects(soup)
        self._process_preloads(soup)
        self._remove_tracking_scripts(soup)

        # Inject fetch interceptor BEFORE converting to string (Fase 3)
        self._inject_fetch_interceptor(soup)

        # Convert soup to string ONCE
        html_output = str(soup)

        # Post-string operations (SAFE operations only)
        self._safe_url_rewrite_css_only()  # NEW: Only rewrite CSS files safely
        self._process_json_files()  # SAFE: JSON parsing and rewriting
        self._remove_sourcemaps()

        # FASE 3.3: Rewrite basenames in HTML output (inline CSS/JS)
        html_output = self._rewrite_basenames_in_content(html_output)

        # CRITICAL FIX: Rewrite Next.js Image API in HTML string
        html_output = self._rewrite_nextjs_images_in_html(html_output)

        return html_output

    def _rewrite_css_urls(self, css_content, css_url):
        """Rewrite all url() references in CSS content"""
        def replacer(match):
            full_match = match.group(0)
            url_content = match.group(1).strip()

            # Remove quotes if present
            if url_content.startswith(("'", '"')) and url_content.endswith(("'", '"')):
                url_content = url_content[1:-1]

            if not url_content or url_content.startswith('data:'):
                return full_match

            # Make absolute URL relative to CSS file
            abs_url = urljoin(css_url, url_content)
            local_path = self.network.get_resource(abs_url)

            if local_path and local_path.startswith('assets/'):
                # CSS is in assets/, so reference sibling files directly
                return f'url("{os.path.basename(local_path)}")'

            return full_match

        return re.sub(r'url\(\s*([^)]+)\s*\)', replacer, css_content)

    def _remove_canvas_placeholder_comments(self, soup):
        """
        Remove Playwright-captured canvas elements that will be recreated by WebGL libraries.
        """
        removed = 0

        # Find all canvas elements
        for canvas in soup.find_all('canvas'):
            # Check if it has dimension attributes (sign it's a Playwright snapshot)
            has_width_attr = canvas.has_attr('width')
            has_height_attr = canvas.has_attr('height')
            has_engine_attr = canvas.has_attr('data-engine')

            # If it has ALL three attributes, it's a rendered snapshot - remove it
            if has_width_attr and has_height_attr and has_engine_attr:
                self.log(f"   Removendo canvas renderizado: {canvas.get('width')}x{canvas.get('height')} ({canvas.get('class', [])})")
                canvas.decompose()
                removed += 1

        if removed > 0:
            self.log(f"   Removidos {removed} canvas renderizados (Playwright snapshots)")

    def _process_srcset(self, srcset, base=None):
        """Process a srcset attribute and return the rewritten version"""
        if not srcset:
            return srcset

        from urllib.parse import quote

        def _encode_srcset_url(path):
            """Encode spaces in srcset URLs so browsers can parse them."""
            return path.replace(' ', '%20')

        new_parts = []
        parts = srcset.split(',')

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Parse srcset: split by last whitespace to separate URL from descriptor
            match = re.match(r'^(.+)\s+(\d+(?:\.\d+)?[wx])$', part)

            if match:
                url = match.group(1).strip()
                descriptor = match.group(2)
            else:
                url = part.strip()
                descriptor = ''

            if url.startswith('data:'):
                new_parts.append(part)
                continue

            # Special handling for Next.js Image API in srcset
            if '/_next/image' in url and 'url=' in url:
                from urllib.parse import parse_qs, urlparse, unquote
                try:
                    parsed = urlparse(url)
                    query_params = parse_qs(parsed.query)
                    if 'url' in query_params:
                        original_url = unquote(query_params['url'][0])
                        resolved = None

                        full_url = urljoin(base or self.base_url, url)
                        resolved = self.network.get_resource(full_url, base)
                        if resolved and resolved == full_url:
                            resolved = None

                        if not resolved:
                            resolved = self.network.get_resource(original_url, base)
                            if resolved and resolved == original_url:
                                resolved = None

                        if resolved:
                            encoded = _encode_srcset_url(resolved)
                            if descriptor:
                                new_parts.append(f"{encoded} {descriptor}")
                            else:
                                new_parts.append(encoded)
                            continue
                except:
                    pass

            local_path = self.network.get_resource(url, base)
            if local_path and local_path != url:
                encoded = _encode_srcset_url(local_path)
                if descriptor:
                    new_parts.append(f"{encoded} {descriptor}")
                else:
                    new_parts.append(encoded)
            else:
                # Keep original but encode if it has spaces
                encoded = _encode_srcset_url(part) if ' ' in url else part
                if descriptor and ' ' in url:
                    encoded = f"{_encode_srcset_url(url)} {descriptor}"
                new_parts.append(encoded)

        return ', '.join(new_parts) if new_parts else ''

    def _fix_scroll_blocking(self, soup):
        """Fix CSS and HTML issues that block scrolling in offline viewing"""
        self.log("🔧 Corrigindo problemas de scroll para visualização offline...")

        # Fix html element
        html_elem = soup.find('html')
        if html_elem:
            html_classes = html_elem.get('class', [])
            if isinstance(html_classes, str):
                html_classes = html_classes.split()

            lenis_classes = ['lenis', 'lenis-smooth', 'lenis-scrolling', 'lenis-stopped',
                           'has-scroll-smooth', 'has-scroll-init', 'locomotive-scroll']
            new_classes = [c for c in html_classes if c.lower() not in [lc.lower() for lc in lenis_classes]]
            if new_classes != html_classes:
                html_elem['class'] = new_classes
                self.log("   Removidas classes Lenis/Locomotive do html")

        # Fix body element
        body = soup.find('body')
        if body:
            body_classes = body.get('class', [])
            if isinstance(body_classes, str):
                body_classes = body_classes.split()

            blocking_classes = ['overflow-hidden', 'no-scroll', 'scroll-lock', 'fixed',
                              'lenis', 'lenis-smooth', 'has-scroll-smooth']
            new_classes = [c for c in body_classes if c.lower() not in [bc.lower() for bc in blocking_classes]]

            # Fix flex centering
            if 'items-center' in new_classes and 'flex' in new_classes:
                new_classes = [c if c != 'items-center' else 'items-start' for c in new_classes]
                self.log("   Corrigida centralização vertical do body")

            if new_classes != body_classes:
                body['class'] = new_classes

        # Remove scroll container data attributes
        for elem in soup.find_all(class_=lambda c: c and any(
            x in str(c).lower() for x in ['scroll-container', 'smooth-scroll', 'lenis', 'locomotive']
        )):
            for attr in list(elem.attrs.keys()):
                if 'scroll' in attr.lower() or 'lenis' in attr.lower():
                    del elem[attr]

        # FASE 5: Inject MINIMAL scroll fix CSS
        scroll_fix_css = """
        /* Scroll fixes - MINIMAL SCOPE */
        html, body {
            overflow: auto !important;
            overflow-x: hidden !important;
            height: auto !important;
            min-height: 100% !important;
            scroll-behavior: auto !important;
        }

        /* Remove loaders only */
        .loader, .preloader, .loading, [class*="loader"], [class*="preloader"] {
            display: none !important;
            opacity: 0 !important;
        }

        /* Reset smooth scroll containers */
        html.lenis, html.lenis-smooth,
        body.lenis, body.lenis-smooth,
        .lenis-wrapper, .lenis-content,
        [data-lenis-prevent], [data-scroll-container] {
            overflow: visible !important;
            height: auto !important;
        }

        /* Fix flex containers */
        body.flex.items-center,
        body.flex.justify-center {
            align-items: flex-start !important;
            min-height: 100vh;
            height: auto !important;
        }

        /* Ensure main content scrolls */
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

        # Remove smooth scroll library scripts
        scripts_removed = 0
        for script in soup.find_all('script'):
            src = script.get('src', '') or ''
            script_text = script.string or ''

            if any(x in src.lower() for x in SMOOTH_SCROLL_LIBS):
                script.decompose()
                scripts_removed += 1
            elif any(x in script_text.lower() for x in ['new lenis', 'new locomotivescroll', 'smoothscroll']):
                script.decompose()
                scripts_removed += 1

        if scripts_removed > 0:
            self.log(f"   Removidos {scripts_removed} scripts de smooth scroll")

    def _remove_wrapper_iframes(self, soup):
        """Remove wrapper iframes (preview frames from site builders)"""
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '') or ''
            srcdoc = iframe.get('srcdoc', '')

            # Remove preview/wrapper iframes
            if srcdoc or 'preview' in str(iframe.get('class', '')).lower():
                iframe.decompose()

    def _process_stylesheets(self, soup):
        """Process external stylesheets"""
        self.log("Processando stylesheets...")
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if not href or href.startswith('data:'):
                continue

            # Remove integrity/crossorigin attributes that break offline
            for attr in ['integrity', 'crossorigin', 'nonce']:
                if link.has_attr(attr):
                    del link[attr]

            abs_url = urljoin(self.base_url, href)

            # Try to get CSS content
            css_content = None
            if abs_url in self.network.network_resources:
                try:
                    css_content = self.network.network_resources[abs_url]['body'].decode('utf-8', errors='ignore')
                except:
                    pass

            if not css_content:
                # Fallback download
                try:
                    response = self.network.session.get(abs_url, timeout=15, verify=False)
                    if response.status_code == 200:
                        css_content = response.text
                except:
                    pass

            if css_content:
                css_content = self._rewrite_css_urls(css_content, abs_url)
                local_path = self.network._save_resource(abs_url, css_content.encode('utf-8'), 'text/css')
                if local_path:
                    link['href'] = local_path

    def _process_inline_styles(self, soup):
        """Process inline <style> tags"""
        self.log("Processando estilos inline...")
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                style_tag.string = self._rewrite_css_urls(style_tag.string, self.base_url)

    def _process_scripts(self, soup):
        """Process external scripts"""
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

    def _process_images(self, soup):
        """Process all image-related elements"""
        self.log("Processando imagens...")
        for elem in soup.find_all(['img', 'source', 'video', 'audio', 'picture', 'input']):
            # Check lazy loading attributes first
            for attr in ['data-src', 'data-original', 'data-lazy-src', 'data-url', 'data-image', 'data-bg']:
                if elem.get(attr):
                    lazy_src = elem[attr]
                    local_path = self.network.get_resource(lazy_src)
                    if local_path and local_path != lazy_src:
                        elem['src'] = local_path
                        del elem[attr]
                    break

            # Process src
            src = elem.get('src')
            if src and not src.startswith('data:'):
                # Special handling for Next.js Image API
                if '/_next/image' in src and 'url=' in src:
                    from urllib.parse import parse_qs, urlparse, unquote
                    try:
                        parsed = urlparse(src)
                        query_params = parse_qs(parsed.query)
                        if 'url' in query_params:
                            original_url = unquote(query_params['url'][0])
                            local_path = None

                            # Strategy 1: Try the full /_next/image URL
                            full_url = urljoin(self.base_url, src)
                            local_path = self.network.get_resource(full_url)
                            if local_path and local_path == full_url:
                                local_path = None

                            # Strategy 2: Try the inner url= parameter
                            if not local_path:
                                local_path = self.network.get_resource(original_url)
                                if local_path and local_path == original_url:
                                    local_path = None

                            if local_path:
                                elem['src'] = local_path
                                self.log(f"   Next.js Image API: {src[:60]}... -> {local_path}")
                            continue
                    except Exception as e:
                        pass

                local_path = self.network.get_resource(src)
                if local_path and local_path != src:
                    elem['src'] = local_path

            # Process srcset
            srcset = elem.get('srcset')
            if srcset:
                new_srcset = self._process_srcset(srcset)
                elem['srcset'] = new_srcset

            # Process data-srcset
            data_srcset = elem.get('data-srcset')
            if data_srcset:
                elem['data-srcset'] = self._process_srcset(data_srcset)

            # Process poster for video
            if elem.name == 'video' and elem.get('poster'):
                poster = elem['poster']
                local_path = self.network.get_resource(poster)
                if local_path and local_path != poster:
                    elem['poster'] = local_path

    def _process_inline_style_attrs(self, soup):
        """Process inline style attributes with url()"""
        self.log("Processando atributos de estilo inline...")
        for elem in soup.find_all(attrs={'style': True}):
            style = elem['style']
            if 'url(' in style:
                elem['style'] = self._rewrite_css_urls(style, self.base_url)

    def _process_favicons(self, soup):
        """Process favicons and other link tags"""
        for link in soup.find_all('link'):
            if link.get('href') and link.get('rel'):
                rel = link['rel']
                if isinstance(rel, list):
                    rel = ' '.join(rel)
                if 'icon' in rel.lower() or 'apple-touch' in rel.lower() or 'manifest' in rel.lower():
                    href = link['href']
                    if not href.startswith('data:'):
                        local_path = self.network.get_resource(href)
                        if local_path and local_path != href:
                            link['href'] = local_path

    def _process_meta_images(self, soup):
        """Process meta tags with image URLs (og:image, etc.)"""
        for meta in soup.find_all('meta', attrs={'content': True}):
            prop = meta.get('property', '') or meta.get('name', '')
            if 'image' in prop.lower():
                content = meta['content']
                if content and not content.startswith('data:') and ('http' in content or content.startswith('/')):
                    local_path = self.network.get_resource(content)
                    if local_path and local_path != content:
                        meta['content'] = local_path

    def _process_background_attrs(self, soup):
        """Process data-background attributes"""
        for elem in soup.find_all(attrs={'data-background': True}):
            bg = elem['data-background']
            if bg and not bg.startswith('data:'):
                local_path = self.network.get_resource(bg)
                if local_path and local_path != bg:
                    elem['data-background'] = local_path

    def _fix_navigation_links(self, soup):
        """Fix navigation links that won't work locally"""
        self.log("Corrigindo links de navegação...")
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href == '/':
                a['href'] = '#'
            elif href.startswith('/') and not href.startswith('//'):
                a['href'] = '#'

    def _detect_nextjs(self, soup):
        """Detect if page is built with Next.js"""
        for script in soup.find_all('script'):
            script_id = script.get('id', '')
            script_text = script.string or ''
            if '__NEXT_DATA__' in script_id or '__NEXT_DATA__' in script_text:
                return True
            if 'self.__next' in script_text:
                return True

        for script in soup.find_all('script', src=True):
            src = script['src']
            if '_next/' in src or 'webpack' in src.lower():
                return True

        for link in soup.find_all('link'):
            href = link.get('href', '')
            if '_next/' in href:
                return True

        return False

    def _handle_spa_frameworks(self, soup):
        """
        Handle SPA frameworks (Gatsby, Next.js, Nuxt)
        CONSERVATIVE: Only remove hydration/routing scripts that break offline viewing.
        """
        is_gatsby = soup.find(id='___gatsby') is not None
        is_nextjs = soup.find(id='__next') is not None or self._detect_nextjs(soup)
        is_nuxt = soup.find(id='__nuxt') is not None

        if is_gatsby or is_nextjs or is_nuxt:
            framework = 'Gatsby' if is_gatsby else ('Next.js' if is_nextjs else 'Nuxt')
            self.log(f"🛡️ Detectado {framework} - removendo APENAS scripts de hydration...")

            scripts_removed = 0

            for script in soup.find_all('script'):
                src = script.get('src', '')
                script_text = script.string or ''

                should_remove = False

                # Only remove inline scripts that explicitly do hydration/routing
                if not src:
                    if ('self.__next_f' in script_text or
                        '__NEXT_DATA__' in script_text or
                        'GATSBY___' in script_text or
                        '__NUXT__' in script_text):
                        should_remove = True

                if should_remove:
                    script.decompose()
                    scripts_removed += 1

            self.log(f"   Removidos {scripts_removed} scripts de hydration do {framework}")

    def _safe_url_rewrite_css_only(self):
        """
        REFACTORED: SAFE URL rewriting - CSS FILES ONLY

        JavaScript files are now handled EXCLUSIVELY by the Fetch Interceptor at runtime.
        This prevents syntax corruption from blind string replacement.

        Only CSS files are rewritten here because:
        1. CSS has simpler syntax (url() patterns only)
        2. CSS doesn't have complex string contexts like JS
        3. Regex-based URL rewriting is safe in CSS
        """
        self.log("🔄 Aplicando substituição de URLs em arquivos CSS...")

        resource_map = self.network.get_resource_map()
        if not resource_map:
            return

        # Get CSS files only (recursive)
        assets_dir = os.path.join(self.output_dir, 'assets')
        css_extensions = ['.css']

        files_to_process = []
        if os.path.exists(assets_dir):
            for root, dirs, files in os.walk(assets_dir):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    _, ext = os.path.splitext(filename)
                    if ext.lower() in css_extensions:
                        files_to_process.append(filepath)

        # Process each CSS file
        replacements_count = 0
        for filepath in files_to_process:
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                original_content = content

                # Replace each URL in resource_map
                for original_url, local_path in resource_map.items():
                    # Skip if already local
                    if original_url.startswith('assets/'):
                        continue

                    # Skip data/blob URLs
                    if original_url.startswith(('data:', 'blob:')):
                        continue

                    # Generate URL variants to replace
                    variants = [original_url]

                    # Add protocol-relative variant (//domain.com/path)
                    if original_url.startswith('https://'):
                        variants.append(original_url.replace('https://', '//'))
                    elif original_url.startswith('http://'):
                        variants.append(original_url.replace('http://', '//'))

                    # Replace all variants with local path
                    for variant in variants:
                        if variant in content:
                            # For CSS files in assets/, reference sibling files by basename only
                            if local_path.startswith('assets/'):
                                replacement = os.path.basename(local_path)
                            else:
                                replacement = local_path

                            content = content.replace(variant, replacement)

                # Generate CDN patterns automatically from resource_map
                cdn_domains = set()
                for original_url in resource_map.keys():
                    if original_url.startswith(('http://', 'https://')):
                        parsed = urlparse(original_url)
                        if parsed.netloc:
                            cdn_domains.add(parsed.netloc)

                # Generate replacement patterns for each domain
                for domain in cdn_domains:
                    # Pattern 1: https://domain/ -> /assets/
                    pattern_https = f'https://{domain}/'
                    if pattern_https in content:
                        content = content.replace(pattern_https, '/assets/')

                    # Pattern 2: http://domain/ -> /assets/
                    pattern_http = f'http://{domain}/'
                    if pattern_http in content:
                        content = content.replace(pattern_http, '/assets/')

                    # Pattern 3: domain/ (protocol-relative, quoted)
                    for quote in ['"', "'"]:
                        pattern_with_quote = f'{quote}{domain}/'
                        if pattern_with_quote in content:
                            content = content.replace(pattern_with_quote, f'{quote}assets/')

                # Replace relative basenames (for CSS files)
                for original_url, local_path in resource_map.items():
                    if local_path.startswith('assets/'):
                        basename = os.path.basename(local_path)
                        # CSS-specific patterns: url("basename")
                        patterns = [
                            f'url("{basename}")',
                            f"url('{basename}')",
                            f'url({basename})',
                        ]
                        for pattern in patterns:
                            if pattern in content:
                                # Replace with absolute path
                                replacement = pattern.replace(basename, f'/{local_path}')
                                content = content.replace(pattern, replacement)

                # Write back if changed
                if content != original_content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    replacements_count += 1

            except Exception as e:
                self.log(f"Erro ao processar {os.path.basename(filepath)}: {e}")

        if replacements_count > 0:
            self.log(f"   {replacements_count} arquivos CSS reescritos")
        else:
            self.log(f"   Nenhum arquivo CSS precisou de reescrita")

    def _process_json_files(self):
        """
        FASE 3.4: Process JSON and manifest files to rewrite URLs
        SAFE: Uses JSON parsing, not blind string replacement
        """
        self.log("🔄 Processando arquivos JSON/manifest...")

        resource_map = self.network.get_resource_map()
        if not resource_map:
            return

        assets_dir = os.path.join(self.output_dir, 'assets')
        json_extensions = ['.json', '.webmanifest']

        files_to_process = []
        if os.path.exists(assets_dir):
            for root, dirs, files in os.walk(assets_dir):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    _, ext = os.path.splitext(filename)
                    if ext.lower() in json_extensions:
                        files_to_process.append(filepath)

        # Also check root directory for manifest files
        for ext in ['.json', '.webmanifest']:
            root_manifest = os.path.join(self.output_dir, f'manifest{ext}')
            if os.path.exists(root_manifest):
                files_to_process.append(root_manifest)

        def make_relative_path(json_filepath, resource_path):
            """Calculate relative path from JSON file to resource."""
            json_dir = os.path.dirname(json_filepath)
            output_dir = self.output_dir

            # Check if JSON is inside assets/
            json_relative = os.path.relpath(json_dir, output_dir)
            is_json_in_assets = json_relative.startswith('assets')

            if is_json_in_assets and resource_path.startswith('assets/'):
                # Both JSON and resource are in assets/
                resource_abs = os.path.join(output_dir, resource_path)
                relative = os.path.relpath(resource_abs, json_dir)
                return relative
            else:
                # JSON is in root or resource is external
                return resource_path

        def rewrite_json_value(value, json_filepath):
            """Recursively rewrite URLs in JSON values"""
            if isinstance(value, str):
                # Check if it's a URL-like string
                if value.startswith(('http://', 'https://', '//', '/')):
                    # Try to match against resource_map
                    abs_url = urljoin(self.base_url, value)
                    if abs_url in resource_map:
                        local_path = resource_map[abs_url]
                        return make_relative_path(json_filepath, local_path)
                    # Try protocol-relative
                    if value.startswith('//'):
                        https_variant = 'https:' + value
                        if https_variant in resource_map:
                            local_path = resource_map[https_variant]
                            return make_relative_path(json_filepath, local_path)
                # Also handle paths that already start with 'assets/'
                elif value.startswith('assets/'):
                    return make_relative_path(json_filepath, value)
                return value
            elif isinstance(value, dict):
                return {k: rewrite_json_value(v, json_filepath) for k, v in value.items()}
            elif isinstance(value, list):
                return [rewrite_json_value(item, json_filepath) for item in value]
            else:
                return value

        processed_count = 0
        for filepath in files_to_process:
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    data = json.load(f)

                original_data = json.dumps(data, sort_keys=True)
                rewritten_data = rewrite_json_value(data, filepath)
                new_data_str = json.dumps(rewritten_data, sort_keys=True)

                if new_data_str != original_data:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(rewritten_data, f, indent=2, ensure_ascii=False)
                    processed_count += 1
                    self.log(f"   Reescrito: {os.path.basename(filepath)}")

            except json.JSONDecodeError:
                # Not valid JSON, skip
                pass
            except Exception as e:
                self.log(f"   Erro ao processar {os.path.basename(filepath)}: {e}")

        if processed_count > 0:
            self.log(f"   {processed_count} arquivos JSON/manifest reescritos")

    def _rewrite_basenames_in_content(self, content):
        """
        FASE 3.3: Rewrite relative basenames in HTML content (for inline CSS/JS)
        Pattern: url("basename.svg") -> url("/assets/path/basename.svg")
        """
        resource_map = self.network.get_resource_map()
        if not resource_map:
            return content

        # Replace relative basenames
        for original_url, local_path in resource_map.items():
            if local_path.startswith('assets/'):
                basename = os.path.basename(local_path)
                # Replace patterns like url("basename") or src="basename"
                patterns = [
                    (f'url("{basename}")', f'url("/{local_path}")'),
                    (f"url('{basename}')", f"url('/{local_path}')"),
                    (f'url({basename})', f'url(/{local_path})'),
                    (f'src="{basename}"', f'src="/{local_path}"'),
                    (f"src='{basename}'", f"src='/{local_path}'"),
                ]
                for old_pattern, new_pattern in patterns:
                    if old_pattern in content:
                        content = content.replace(old_pattern, new_pattern)

        return content

    def _rewrite_nextjs_images_in_html(self, html_content):
        """
        CRITICAL FIX: Rewrite Next.js Image API URLs in HTML string
        Pattern: /_next/image/?url=%2Fpath%2Fimage.png&amp;w=96&amp;q=75 -> assets/image_hash.png
        """
        import re
        from urllib.parse import parse_qs, urlparse, unquote

        resource_map = self.network.get_resource_map()
        if not resource_map:
            return html_content

        # Match /_next/image with optional trailing slash
        pattern = r'/_next/image/?\?[^"\'<>\s]+'

        def replace_nextjs_url(match):
            full_match = match.group(0)

            try:
                # Normalize &amp; to &
                normalized = full_match.replace('&amp;', '&')
                parsed = urlparse(normalized)
                query_params = parse_qs(parsed.query)

                if 'url' not in query_params:
                    return full_match

                original_url = unquote(query_params['url'][0])

                # Strategy 1: Try the full /_next/image URL
                full_abs = urljoin(self.base_url, normalized)
                local_path = resource_map.get(full_abs)

                # Strategy 2: Try the inner url= parameter
                if not local_path:
                    abs_url = urljoin(self.base_url, original_url)
                    local_path = resource_map.get(abs_url) or resource_map.get(original_url)

                if local_path:
                    self.log(f"   Reescrito Next.js no HTML: {full_match[:60]}... -> {local_path}")
                    return local_path
            except:
                pass

            return full_match

        result = re.sub(pattern, replace_nextjs_url, html_content)

        return result

    def _inject_fetch_interceptor(self, soup):
        """
        REFACTORED: Enhanced fetch/XHR interceptor with:
        1. Relative path resolution (for dynamic imports)
        2. CDN blocking (prevent external leaks)
        3. Better error handling
        """
        self.log("💉 Injetando fetch interceptor aprimorado...")

        resource_map = self.network.get_resource_map()
        if not resource_map:
            self.log("   Resource map vazio, interceptor não injetado")
            return

        # Decide: inline or external JSON?
        if len(resource_map) > 500:
            # Save as external JSON file
            map_filename = 'resource-map.json'
            map_path = os.path.join(self.output_dir, 'assets', map_filename)
            with open(map_path, 'w', encoding='utf-8') as f:
                json.dump(resource_map, f)

            map_load_code = f'''
            const response = await fetch('assets/{map_filename}');
            const resourceMap = await response.json();
            '''
        else:
            # Inline in script
            map_load_code = f'''
            const resourceMap = {json.dumps(resource_map, ensure_ascii=False)};
            '''

        interceptor_script = f'''
(async function() {{
    {map_load_code}

    // Build reverse index: basename -> full paths (for relative imports)
    const basenameIndex = {{}};
    Object.entries(resourceMap).forEach(([originalUrl, localPath]) => {{
        if (localPath.startsWith('assets/')) {{
            const basename = localPath.split('/').pop();
            if (!basenameIndex[basename]) {{
                basenameIndex[basename] = [];
            }}
            basenameIndex[basename].push(localPath);
        }}
    }});

    // Helper: normalize URL to absolute
    function normalizeUrl(url, baseUrl) {{
        if (!url) return url;
        if (typeof url === 'object' && url.url) url = url.url; // Request object
        if (url.startsWith('data:') || url.startsWith('blob:')) return url;

        // Make absolute
        try {{
            const base = baseUrl || window.location.href;
            return new URL(url, base).href;
        }} catch(e) {{
            return url;
        }}
    }}

    // Helper: resolve relative path from current script context
    function resolveRelativePath(url, referrer) {{
        if (!url.startsWith('./') && !url.startsWith('../')) {{
            return null; // Not a relative path
        }}

        try {{
            // Get the directory of the referrer (current script location)
            const referrerUrl = new URL(referrer || window.location.href);
            const referrerDir = referrerUrl.pathname.substring(0, referrerUrl.pathname.lastIndexOf('/') + 1);

            // Resolve relative URL
            const resolved = new URL(url, window.location.origin + referrerDir).pathname;

            // Extract basename and try to match
            const basename = resolved.split('/').pop();
            if (basenameIndex[basename]) {{
                // If we have exactly one match, use it
                if (basenameIndex[basename].length === 1) {{
                    return '/' + basenameIndex[basename][0];
                }}
                // Multiple matches: try to find one in same directory structure
                const referrerPath = referrer.replace(window.location.origin, '');
                for (const candidate of basenameIndex[basename]) {{
                    if (referrerPath.includes('assets/') && candidate.includes(basename)) {{
                        return '/' + candidate;
                    }}
                }}
                // Fallback: use first match
                return '/' + basenameIndex[basename][0];
            }}
        }} catch(e) {{
            console.warn('[Fetch Interceptor] Relative path resolution failed:', url, e);
        }}

        return null;
    }}

    // Helper: check if URL is in map
    function getLocalPath(url, referrer) {{
        // Try relative resolution first (for dynamic imports)
        if (url.startsWith('./') || url.startsWith('../')) {{
            const resolved = resolveRelativePath(url, referrer);
            if (resolved) return resolved;
        }}

        const normalized = normalizeUrl(url, referrer);
        if (resourceMap[normalized]) return resourceMap[normalized];

        // Try protocol-relative variant
        const withoutProtocol = normalized.replace(/^https?:/, '');
        if (resourceMap[withoutProtocol]) return resourceMap[withoutProtocol];

        // Try basename matching (last resort for CDN URLs)
        try {{
            const basename = normalized.split('/').pop().split('?')[0]; // Remove query params
            if (basenameIndex[basename]) {{
                if (basenameIndex[basename].length === 1) {{
                    return '/' + basenameIndex[basename][0];
                }}
            }}
        }} catch(e) {{}}

        return null;
    }}

    // Helper: check if URL is external CDN (should be blocked)
    function isExternalCDN(url) {{
        try {{
            const urlObj = new URL(url, window.location.href);
            // Block if:
            // 1. Different origin than current page
            // 2. Contains CDN markers
            if (urlObj.origin !== window.location.origin) {{
                const hostname = urlObj.hostname.toLowerCase();
                const cdnMarkers = ['.b-cdn.', 'cdn.', '.cloudfront.', '.akamai', '.fastly.'];
                return cdnMarkers.some(marker => hostname.includes(marker));
            }}
        }} catch(e) {{}}
        return false;
    }}

    // Intercept fetch
    const originalFetch = window.fetch;
    window.fetch = function(url, options) {{
        const referrer = (options && options.referrer) || document.currentScript?.src || window.location.href;
        const localPath = getLocalPath(url, referrer);

        if (localPath) {{
            console.log('[Fetch Interceptor] ✓', url, '->', localPath);
            return originalFetch(localPath, options);
        }}

        // Block external CDN requests
        if (isExternalCDN(url)) {{
            console.warn('[Fetch Interceptor] ✗ Blocked CDN leak:', url);
            return Promise.reject(new Error('CDN request blocked: ' + url));
        }}

        return originalFetch(url, options);
    }};

    // Intercept XMLHttpRequest
    const originalOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url, ...args) {{
        const referrer = document.currentScript?.src || window.location.href;
        const localPath = getLocalPath(url, referrer);

        if (localPath) {{
            console.log('[XHR Interceptor] ✓', url, '->', localPath);
            return originalOpen.call(this, method, localPath, ...args);
        }}

        // Block external CDN requests
        if (isExternalCDN(url)) {{
            console.warn('[XHR Interceptor] ✗ Blocked CDN leak:', url);
            // Return 404-like error
            return originalOpen.call(this, method, 'data:text/plain,404', ...args);
        }}

        return originalOpen.call(this, method, url, ...args);
    }};

    // Intercept dynamic imports (ES modules)
    // This is tricky because we can't directly intercept import(), but the fetch interceptor will catch it

    console.log('[Fetch Interceptor] Installed with', Object.keys(resourceMap).length, 'mappings');
    console.log('[Fetch Interceptor] Basename index:', Object.keys(basenameIndex).length, 'files');
}})();
'''

        # Inject as FIRST script in <head>
        head = soup.find('head')
        if head:
            script_tag = soup.new_tag('script')
            script_tag['data-fetch-interceptor'] = 'true'
            from bs4 import NavigableString
            script_tag.append(NavigableString(interceptor_script))

            # Insert as first child
            if head.contents:
                head.insert(0, script_tag)
            else:
                head.append(script_tag)

            self.log(f"   Fetch interceptor aprimorado injetado ({len(resource_map)} mapeamentos)")
        else:
            self.log("   <head> não encontrado, interceptor não injetado")

    def _remove_preconnects(self, soup):
        """FASE 4: Remove preconnect and dns-prefetch"""
        removed = 0
        for link in soup.find_all('link', rel=lambda r: r and any(x in r for x in ['preconnect', 'dns-prefetch'])):
            link.decompose()
            removed += 1

        if removed > 0:
            self.log(f"   Removidos {removed} preconnects/dns-prefetch")

    def _process_preloads(self, soup):
        """FASE 4: Process preload/prefetch links"""
        self.log("Processando preloads...")
        processed = 0

        for link in soup.find_all('link', rel=lambda r: r and any(x in r for x in ['preload', 'prefetch', 'modulepreload'])):
            href = link.get('href')
            if href and not href.startswith(('data:', 'blob:', 'assets/')):
                local_path = self.network.get_resource(href)
                if local_path and local_path != href:
                    link['href'] = local_path
                    processed += 1

        if processed > 0:
            self.log(f"   {processed} preloads reescritos")

    def _remove_tracking_scripts(self, soup):
        """FASE 4: Remove tracking/analytics scripts"""
        self.log("🛡️ Removendo scripts de tracking...")
        removed = 0

        for script in soup.find_all('script', src=True):
            src = script.get('src', '')
            if any(pattern in src.lower() for pattern in TRACKING_SCRIPTS):
                script.decompose()
                removed += 1

        if removed > 0:
            self.log(f"   Removidos {removed} scripts de tracking")

    def _remove_sourcemaps(self):
        """FASE 4: Remove sourceMappingURL from JS files"""
        self.log("🗺️ Removendo sourcemaps...")
        assets_dir = os.path.join(self.output_dir, 'assets')
        cleaned = 0

        if os.path.exists(assets_dir):
            for root, dirs, files in os.walk(assets_dir):
                for filename in files:
                    if filename.endswith('.js'):
                        filepath = os.path.join(root, filename)
                        try:
                            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()

                            # Remove sourceMappingURL comments
                            new_content = re.sub(r'//# sourceMappingURL=.*', '', content)
                            new_content = re.sub(r'/\*# sourceMappingURL=.*\*/', '', new_content)

                            if new_content != content:
                                with open(filepath, 'w', encoding='utf-8') as f:
                                    f.write(new_content)
                                cleaned += 1
                        except:
                            pass

        if cleaned > 0:
            self.log(f"   {cleaned} arquivos JS limpos")

    def save_html(self, html_output):
        """Save final HTML to disk"""
        with open(os.path.join(self.output_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html_output)
