"""
Asset localization and cleanup helpers for post-processing.
"""
import re
from urllib.parse import urljoin, urlparse

from .. import RESOURCE_TIMEOUT, SKIP_DOMAINS, TRACKING_SCRIPTS
from ..url_rewrite import rewrite_css_urls


class PostProcessProcessorsMixin:
    def _prefer_original_root_path(self, original_url, local_path):
        """
        Keep exact same-origin root paths when the saved asset preserved structure.

        This preserves framework runtime semantics such as Next.js assetPrefix
        detection from `document.currentScript.src`, while the local server can
        still resolve `/path` to `assets/path` transparently.
        """
        if not original_url or not local_path or not local_path.startswith('assets/'):
            return local_path

        absolute_url = urljoin(self.base_url, original_url)
        parsed_original = urlparse(absolute_url)
        parsed_base = urlparse(self.base_url)

        if parsed_original.scheme not in {'http', 'https'}:
            return local_path
        if parsed_original.netloc != parsed_base.netloc:
            return local_path
        if parsed_original.query or not parsed_original.path.startswith('/'):
            return local_path

        expected_local = f"assets/{parsed_original.path.lstrip('/')}"
        if local_path == expected_local:
            return parsed_original.path

        return local_path

    def _to_browser_url(self, local_path):
        """Normalize saved paths into URL-like specifiers safe for HTML/runtime APIs."""
        if not local_path:
            return local_path

        if local_path.startswith(('http://', 'https://', '/', './', '../', 'data:', 'blob:')):
            return local_path

        return f"/{local_path.lstrip('/')}"

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
                    response = self.network.session.get(abs_url, timeout=RESOURCE_TIMEOUT, verify=False)
                    if response.status_code == 200:
                        css_content = response.text
                except Exception:
                    pass

            if css_content:
                css_content = rewrite_css_urls(css_content, abs_url, self.network)
                local_path = self.network._save_resource(abs_url, css_content.encode('utf-8'), 'text/css')
                if local_path:
                    link['href'] = self._prefer_original_root_path(href, local_path)

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

            if original_script_urls is not None and absolute_src not in original_script_urls:
                scripts_to_remove.append(script)
                runtime_injected_removed += 1
                continue

            local_path = self.network.get_resource(src)

            if local_path and local_path != src:
                script['src'] = self._prefer_original_root_path(src, local_path)
                for attr in ['integrity', 'crossorigin', 'nonce']:
                    if script.has_attr(attr):
                        del script[attr]
            else:
                is_tracking = any(domain in src for domain in SKIP_DOMAINS)
                if not is_tracking:
                    self.log(f"   ⚠️ Removendo script com download falhado: {src[:80]}...")
                    scripts_to_remove.append(script)

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
                from urllib.parse import parse_qs, unquote, urlparse

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
                    from urllib.parse import parse_qs, unquote, urlparse

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
        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            if href == '/' or (href.startswith('/') and not href.startswith('//')):
                anchor['href'] = '#'

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

    def _is_ssr_framework(self, soup):
        """Detect SSR/SPA frameworks whose runtime mutates the DOM heavily."""
        return any([
            soup.find(id='___gatsby') is not None,
            soup.find(id='__nuxt') is not None,
            soup.find(id='__next') is not None,
            self._detect_nextjs(soup),
        ])

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
        for link in soup.find_all('link', rel=lambda rel: rel and any(item in rel for item in ['preconnect', 'dns-prefetch'])):
            link.decompose()
            removed += 1
        if removed:
            self.log(f"   Removidos {removed} preconnects/dns-prefetch")

    def _process_preloads(self, soup):
        """Localize preload/prefetch/modulepreload href attributes."""
        self.log("Processando preloads...")
        processed = 0
        for link in soup.find_all('link', rel=lambda rel: rel and any(item in rel for item in ['preload', 'prefetch', 'modulepreload'])):
            href = link.get('href')
            if href and not href.startswith(('data:', 'blob:', 'assets/')):
                local_path = self.network.get_resource(href)
                if local_path and local_path != href:
                    link['href'] = self._prefer_original_root_path(href, local_path)
                    processed += 1
        if processed:
            self.log(f"   {processed} preloads reescritos")

    def _remove_tracking_scripts(self, soup):
        """Remove analytics/tracking script tags."""
        self.log("🛡️ Removendo scripts de tracking...")
        removed = 0
        for script in soup.find_all('script'):
            src = (script.get('src', '') or '').lower()
            text = (script.get_text() or '').lower()
            attr_values = []
            if isinstance(getattr(script, 'attrs', None), dict):
                for attr_value in script.attrs.values():
                    if isinstance(attr_value, list):
                        attr_values.extend(str(item).lower() for item in attr_value)
                    else:
                        attr_values.append(str(attr_value).lower())
            haystack = f"{src}\n{text}\n" + '\n'.join(attr_values)
            if any(pattern in haystack for pattern in TRACKING_SCRIPTS):
                script.decompose()
                removed += 1
        if removed:
            self.log(f"   Removidos {removed} scripts de tracking")

    def _remove_tracking_widgets(self, soup):
        """Remove runtime DOM widgets from tracking/marketing vendors."""
        removed = 0
        widget_markers = {
            'klaviyo',
            'kl-private-reset-css',
            'cookiebot',
            'cybotcookiebotdialog',
            'web-pixels',
            'web-pixel',
            'shopify-privacy',
            'hotjar',
            'intercom',
            'drift',
            'crisp',
            'zendesk',
            'tawk',
            'livechat',
            'freshchat',
        }

        for element in list(soup.find_all(True)):
            if element.name in {'html', 'head', 'body', 'meta'}:
                continue
            if element.parent is None:
                continue
            if not isinstance(getattr(element, 'attrs', None), dict):
                continue

            marker_values = []
            for attr_value in element.attrs.values():
                if isinstance(attr_value, list):
                    marker_values.extend(str(item).lower() for item in attr_value)
                else:
                    marker_values.append(str(attr_value).lower())

            if element.name in {'style', 'noscript'}:
                marker_values.append((element.get_text() or '').lower())

            if not marker_values:
                continue

            if any(marker in value for value in marker_values for marker in widget_markers):
                element.decompose()
                removed += 1

        if removed:
            self.log(f"   Removidos {removed} widgets de tracking/marketing")

    def _remove_authoring_bootstrap(self, soup):
        """Remove editor/preview overlays injected by site builders."""
        removed = 0
        authoring_markers = {
            '__framer-editorbar',
            '__framer_force_showing_editorbar_since',
            'framer.com/edit',
            'framer.com/bootstrap.',
            'app.framerstatic.com/editorbar',
            'app.framerstatic.com/',
        }

        for element in list(soup.find_all(['script', 'style', 'iframe', 'link', 'div'])):
            if element.parent is None:
                continue
            if element.name == 'script' and element.get('data-generated-importmap') == 'true':
                continue

            marker_values = []
            if isinstance(getattr(element, 'attrs', None), dict):
                for attr_value in element.attrs.values():
                    if isinstance(attr_value, list):
                        marker_values.extend(str(item).lower() for item in attr_value)
                    else:
                        marker_values.append(str(attr_value).lower())

            if element.name in {'script', 'style'}:
                marker_values.append((element.get_text() or '').lower())

            if not marker_values:
                continue

            if any(marker in value for value in marker_values for marker in authoring_markers):
                element.decompose()
                removed += 1

        if removed:
            self.log(f"   Removidos {removed} elementos de bootstrap de autoria/preview")
