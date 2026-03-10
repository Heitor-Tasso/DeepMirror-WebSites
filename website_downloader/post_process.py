"""
Post-Processing - HTML/DOM transformations via BeautifulSoup.
File-based URL rewriting is handled by url_rewrite.URLRewriter.
"""
import os
import re
import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup, NavigableString
from . import TRACKING_SCRIPTS
from .url_rewrite import URLRewriter, rewrite_css_urls


class PostProcessor:
    def __init__(self, base_url, output_dir, log_callback, network_recorder):
        self.base_url = base_url
        self.output_dir = output_dir
        self.log = log_callback
        self.network = network_recorder
        self.rewriter = URLRewriter(base_url, output_dir, log_callback, network_recorder)
        self._original_script_urls = None
        self._original_html_soup = None

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
        self._cleanup_runtime_dom_state(soup)
        self._restore_original_svg_transforms(soup)
        self._restore_original_style_tags(soup)
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

    def _get_original_script_urls(self):
        """Return the external script URLs present in the original HTML response."""
        original_soup = self._get_original_html_soup()
        if not original_soup:
            self._original_script_urls = None
            return None

        if self._original_script_urls is not None:
            return self._original_script_urls

        self._original_script_urls = {
            urljoin(self.base_url, script.get('src'))
            for script in original_soup.find_all('script', src=True)
            if script.get('src')
        }
        return self._original_script_urls

    def _get_original_html_soup(self):
        """Return the original HTML response parsed as BeautifulSoup."""
        if self._original_html_soup is not None:
            return self._original_html_soup

        original_html = self.network.get_document_html(self.base_url)
        if not original_html:
            return None

        self._original_html_soup = BeautifulSoup(original_html, 'html.parser')
        return self._original_html_soup

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

    def _cleanup_runtime_dom_state(self, soup):
        """
        Remove transient runtime flags/styles saved by page.content().

        These markers are useful while the live page is running, but persisting
        them into the offline HTML can block re-initialization on the next load.
        """
        initialized_attrs_removed = 0
        animation_play_state_removed = 0
        transform_style_resets = 0

        transient_style_props = {'translate', 'rotate', 'scale', 'transform-origin'}

        for element in soup.find_all(True):
            for attr in list(element.attrs.keys()):
                if attr.endswith('-initialized'):
                    del element[attr]
                    initialized_attrs_removed += 1

            style = element.get('style')
            if not style:
                continue

            declarations = []
            for raw_decl in style.split(';'):
                if ':' not in raw_decl:
                    continue
                key, value = raw_decl.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                if not key:
                    continue
                declarations.append((key, value))

            if not declarations:
                continue

            kept = [(key, value) for key, value in declarations if key != 'animation-play-state']
            if len(kept) != len(declarations):
                animation_play_state_removed += 1

            # GSAP often leaves transform bookkeeping inline after the initial
            # run. If those are the only persisted styles, drop them so the next
            # runtime can compute its own clean baseline.
            if kept and all(key in transient_style_props for key, _ in kept):
                element.attrs.pop('style', None)
                transform_style_resets += 1
                continue

            if kept:
                element['style'] = '; '.join(f"{key}: {value}" for key, value in kept) + ';'
            else:
                element.attrs.pop('style', None)

        if initialized_attrs_removed:
            self.log(f"   Removidos {initialized_attrs_removed} flags de inicialização em runtime")
        if animation_play_state_removed:
            self.log(f"   Limpos {animation_play_state_removed} estados transitórios de animation-play-state")
        if transform_style_resets:
            self.log(f"   Limpos {transform_style_resets} estilos transitórios de transform do runtime")

    def _element_dom_path(self, element):
        """Build a stable nth-of-type DOM path for matching original/current nodes."""
        parts = []
        current = element

        while current and getattr(current, 'name', None):
            parent = getattr(current, 'parent', None)
            index = 1

            if parent and getattr(parent, 'children', None):
                for sibling in parent.children:
                    if getattr(sibling, 'name', None) != current.name:
                        continue
                    if sibling is current:
                        break
                    index += 1

            parts.append(f"{current.name}:{index}")
            current = parent if getattr(parent, 'name', None) else None

        return tuple(reversed(parts))

    def _restore_original_svg_transforms(self, soup):
        """
        Restore SVG transform attributes to their original server-rendered state.

        Runtime animation libraries often persist matrix transforms into the DOM.
        If those transforms did not exist in the original HTML response, the next
        offline load starts from an already-mutated SVG state and animations drift.
        """
        original_soup = self._get_original_html_soup()
        if not original_soup:
            return

        original_lookup = {}
        for original_elem in original_soup.find_all(True):
            if original_elem.name != 'svg' and not original_elem.find_parent('svg'):
                continue
            original_lookup[self._element_dom_path(original_elem)] = original_elem

        restored = 0
        for current_elem in soup.find_all(True):
            if not current_elem.has_attr('transform'):
                continue
            if current_elem.name != 'svg' and not current_elem.find_parent('svg'):
                continue

            original_elem = original_lookup.get(self._element_dom_path(current_elem))
            if not original_elem:
                continue

            original_transform = original_elem.get('transform')
            current_transform = current_elem.get('transform')
            if original_transform == current_transform:
                continue

            if original_transform is None:
                del current_elem['transform']
            else:
                current_elem['transform'] = original_transform
            restored += 1

        if restored:
            self.log(f"   Restaurados {restored} transforms SVG do HTML original")

    def _restore_original_style_tags(self, soup):
        """
        Restore critical inline <style> tags from the original HTML response.

        CSS-in-JS libraries may leave placeholder tags in the hydrated DOM while
        the real server-rendered CSS still exists in the original HTML response.
        """
        original_soup = self._get_original_html_soup()
        if not original_soup:
            return

        head = soup.find('head')
        original_head = original_soup.find('head')
        if not head or not original_head:
            return

        restored = 0
        current_styles = head.find_all('style')

        def _style_signature(tag):
            return tuple(sorted((key, str(value)) for key, value in tag.attrs.items()))

        current_by_sig = {}
        for style_tag in current_styles:
            current_by_sig.setdefault(_style_signature(style_tag), []).append(style_tag)

        for original_style in original_head.find_all('style'):
            original_css = original_style.get_text() or ''
            if not original_css.strip():
                continue

            signature = _style_signature(original_style)
            candidates = current_by_sig.get(signature, [])
            replaced = False

            for candidate in candidates:
                candidate_css = candidate.get_text() or ''
                if candidate_css.strip():
                    replaced = True
                    break
                candidate.clear()
                candidate.append(NavigableString(original_css))
                restored += 1
                replaced = True
                break

            if replaced:
                continue

            new_style = soup.new_tag('style')
            for key, value in original_style.attrs.items():
                new_style[key] = value
            new_style.append(NavigableString(original_css))
            head.append(new_style)
            restored += 1

        if restored:
            self.log(f"   Restaurados {restored} blocos <style> críticos do HTML original")

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
        """

        head = soup.find('head')
        if head:
            fix_style = soup.new_tag('style')
            fix_style['data-scroll-fix'] = 'true'
            fix_style.string = scroll_fix_css
            head.append(fix_style)
            self.log("   Injetado CSS para corrigir scroll")

        # Preserve scroll libraries and let the runtime initialize normally.
        # The minimal CSS override above is enough to prevent hard scroll locks
        # without breaking controllers such as Lenis/Locomotive.

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
        """
        Localize external script src attributes.

        CRITICAL FIX: Remove scripts that failed to download to prevent SyntaxError cascades.
        When a .js file fails to download, the SPA router returns index.html,
        causing the browser to execute HTML as JavaScript -> SyntaxError.
        """
        self.log("Processando scripts...")

        scripts_to_remove = []
        original_script_urls = self._get_original_script_urls()
        runtime_injected_removed = 0

        for script in soup.find_all('script', src=True):
            src = script.get('src')
            if not src or src.startswith('data:'):
                continue

            absolute_src = urljoin(self.base_url, src)

            # page.content() includes the DOM after loaders have already run.
            # Persisting runtime-injected <script src> tags makes them execute a
            # second time offline when the original loader runs again.
            if original_script_urls is not None and absolute_src not in original_script_urls:
                scripts_to_remove.append(script)
                runtime_injected_removed += 1
                continue

            local_path = self.network.get_resource(src)

            # Check if download failed (resource returned unchanged or not localized)
            if local_path and local_path != src:
                # Success - update src to local path
                script['src'] = local_path
                for attr in ['integrity', 'crossorigin', 'nonce']:
                    if script.has_attr(attr):
                        del script[attr]
            else:
                # CRITICAL: Download failed - check if it's a critical script
                # Don't remove tracking scripts (they're expected to fail)
                from . import SKIP_DOMAINS

                is_tracking = any(domain in src for domain in SKIP_DOMAINS)

                if not is_tracking:
                    # Non-tracking script that failed to download
                    # Remove it to prevent SPA router from serving index.html as JS
                    self.log(f"   ⚠️ Removendo script com download falhado: {src[:80]}...")
                    scripts_to_remove.append(script)

        # Remove failed scripts from DOM
        for script in scripts_to_remove:
            script.decompose()

        if runtime_injected_removed:
            self.log(f"   Removidos {runtime_injected_removed} scripts injetados em runtime")

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
        """Preserve framework hydration/runtime scripts for offline execution."""
        is_gatsby = soup.find(id='___gatsby') is not None
        is_nextjs = soup.find(id='__next') is not None or self._detect_nextjs(soup)
        is_nuxt = soup.find(id='__nuxt') is not None

        if not (is_gatsby or is_nextjs or is_nuxt):
            return

        framework = 'Gatsby' if is_gatsby else ('Next.js' if is_nextjs else 'Nuxt')
        self.log(f"🛡️ Detectado {framework} - preservando scripts de hydration/runtime")

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
