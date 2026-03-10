"""
Network Recorder - Intercept and save all network resources
"""
import os
import re
import hashlib
import requests
import urllib3
import mimetypes
from urllib.parse import urlparse, urljoin
from . import RESOURCE_TIMEOUT, SKIP_DOMAINS, MAX_RETRIES, RETRY_BACKOFF
import time

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class NetworkRecorder:
    def extract_css_from_js_files(self):
        """
        Extract lazily-referenced assets from saved JS files.

        Modern bundlers frequently keep chunk URLs as string literals inside JS
        (Vite __vite__mapDeps, webpack runtime manifests, Next.js split chunks).
        This scans saved JS files for those literal paths and downloads missing
        JS/CSS/assets without attempting to parse the bundle syntax.
        """
        import re
        from urllib.parse import urljoin, urlparse

        self.log("Extraindo assets referenciados em arquivos JS...")

        asset_refs_found = 0
        assets_downloaded = 0
        seen_refs = set()

        asset_patterns = [
            r'["\']((?:https?:)?//[^"\']+\.(?:css|js|mjs)(?:\?[^"\']*)?)["\']',
            r'["\']((?:\./|\.\./|/)?(?:_next/static/(?:css|chunks)|assets|static)/(?:[A-Za-z0-9@_./-]+)\.(?:css|js|mjs|png|jpe?g|svg|webp|avif|gif|woff2?|ttf|otf|eot|json|wasm))["\']',
            r'["\']((?:\./|\.\./)?[A-Za-z0-9][A-Za-z0-9_.-]*-[A-Za-z0-9_.-]+\.(?:css|js|mjs|png|jpe?g|svg|webp|avif|gif|woff2?|ttf|otf|eot|json|wasm))["\']',
        ]

        # Scan all saved JS files
        for url, local_path in list(self.resource_cache.items()):
            if not local_path.endswith(('.js', '.mjs')):
                continue

            abs_path = os.path.join(self.assets_dir, local_path.replace('assets/', '', 1))
            if not os.path.isfile(abs_path):
                continue

            try:
                with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                for pattern in asset_patterns:
                    matches = re.findall(pattern, content)
                    for asset_ref in matches:
                        if asset_ref in seen_refs:
                            continue

                        seen_refs.add(asset_ref)
                        asset_refs_found += 1

                        if asset_ref.startswith('http'):
                            asset_url = asset_ref
                        elif asset_ref.startswith('//'):
                            parsed_base = urlparse(url)
                            asset_url = f"{parsed_base.scheme}:{asset_ref}"
                        elif asset_ref.startswith(('assets/', '_next/', 'static/')):
                            # Bundler manifests often store site-root asset paths without a
                            # leading slash (e.g. "assets/chunk.js"). Resolving those
                            # against the current JS file creates bogus ".../assets/assets/"
                            # URLs, so they must resolve from the site base instead.
                            asset_url = urljoin(self.base_url, asset_ref)
                        else:
                            # Resolve relative chunk paths against the JS file URL itself.
                            asset_url = urljoin(url, asset_ref)

                        if asset_url not in self.resource_cache:
                            local_asset = self._download_fallback(asset_url)
                            if local_asset:
                                assets_downloaded += 1

            except Exception as e:
                # Silent failure - don't break on parse errors
                pass

        if assets_downloaded > 0:
            self.log(f"   {assets_downloaded} asset(s) baixados via extração de JS")
        elif asset_refs_found > 0:
            self.log(f"   {asset_refs_found} referência(s) de asset encontradas (já baixadas)")

    def postprocess_m3u8_files(self):
        """
        Após salvar todos os assets, parseia arquivos .m3u8 baixados e força o download de todas as variantes e chunks referenciados.
        """
        import re
        from urllib.parse import urljoin
        m3u8_files = []
        for url, local_path in self.resource_cache.items():
            if local_path.endswith('.m3u8'):
                m3u8_files.append((url, local_path))
        for url, local_path in m3u8_files:
            try:
                abs_path = os.path.join(self.assets_dir, local_path.replace('assets/', '', 1))
                if not os.path.isfile(abs_path):
                    continue
                with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                # Regex para capturar URIs de chunks e variantes
                uris = re.findall(r'^(?!#)([^\r\n]+)$', content, re.MULTILINE)
                base_url = url.rsplit('/', 1)[0] + '/'
                for ref in uris:
                    ref = ref.strip()
                    if not ref or ref.startswith('#'):
                        continue
                    # Se for URL absoluta, usa direto; senão, resolve relativa ao .m3u8
                    ref_url = ref if ref.startswith('http') else urljoin(base_url, ref)
                    # Força o download se ainda não baixado
                    if ref_url not in self.resource_cache:
                        self._download_fallback(ref_url)
            except Exception as e:
                self.log(f"Erro ao processar {local_path}: {e}")
    def __init__(self, base_url, assets_dir, log_callback):
        # CRITICAL FIX: Normalize base_url to always end with /
        # This prevents urljoin bugs that create malformed URLs like "domain.comassets/"
        self.base_url = base_url if base_url.endswith('/') else base_url + '/'
        self.assets_dir = assets_dir
        self.log = log_callback
        self.network_resources = {}  # url -> {'body': bytes, 'content_type': str}
        self.resource_cache = {}  # url -> local_path (resource_map)
        self.session = None
        # Stats by resource type
        self.stats_by_type = {
            'image': 0,
            'script': 0,
            'stylesheet': 0,
            'font': 0,
            'media': 0,
            'other': 0
        }
        # FASE 6: Tracking de falhas e ignorados
        self.failed_resources = []  # [(url, reason), ...]
        self.ignored_resources = []  # [(url, reason), ...]
        # Debug: Track all seen URLs
        self.all_seen_urls = []  # For debugging

    def get_document_html(self, url=None):
        """
        Return the captured HTML body for the main document when available.

        The network recorder stores HTML responses in-memory alongside assets.
        Post-processing can use the original response HTML as a baseline to
        detect runtime-injected external scripts that should not be persisted.
        """
        candidates = []

        def _add_candidate(candidate):
            if not candidate:
                return
            candidates.append(candidate)
            trimmed = candidate.rstrip('/')
            if trimmed:
                candidates.append(trimmed)
                candidates.append(trimmed + '/')

        _add_candidate(url)
        _add_candidate(self.base_url)

        seen = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)

            resource = self.network_resources.get(candidate)
            if not resource:
                continue

            content_type = (resource.get('content_type') or '').lower()
            if 'html' not in content_type:
                continue

            body = resource.get('body') or b''
            if not body:
                continue

            charset_match = re.search(r'charset=([^\s;]+)', content_type)
            encoding = charset_match.group(1).strip('"\'') if charset_match else 'utf-8'

            try:
                return body.decode(encoding, errors='ignore')
            except LookupError:
                return body.decode('utf-8', errors='ignore')

        return None

    def setup_session(self, cookies):
        """Setup requests session with browser cookies"""
        self.session = requests.Session()
        parsed_base = urlparse(self.base_url)
        origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': self.base_url,
            'Origin': origin,
        })
        for cookie in cookies:
            self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', ''))

    def _validate_content_type(self, url, content_type, body):
        """
        Validate that content-type matches expected file extension.
        Prevents saving Soft 404s (HTML error pages as .js/.css files).

        Returns False if content is invalid (mismatch detected).
        """
        if not content_type or not body:
            return True  # No validation possible, allow

        ct_lower = content_type.lower().split(';')[0].strip()
        url_lower = url.lower()

        # CRITICAL: Detect HTML content masquerading as other types (Soft 404)
        if ct_lower in ('text/html', 'application/xhtml+xml'):
            # HTML is only valid for .html files or directory endpoints
            if not (url_lower.endswith(('.html', '.htm')) or url.rstrip('?#').endswith('/')):
                # Soft 404: server returned HTML error page for a .js/.css request
                return False

        # Validate JavaScript files - strict check against HTML disguised as JS
        if url_lower.endswith('.js'):
            # Content-type must be JS-compatible
            valid_js_types = ('javascript', 'ecmascript', 'text/plain', 'application/octet-stream')

            # If content-type is explicitly HTML, reject immediately
            if ct_lower in ('text/html', 'application/xhtml+xml'):
                return False

            # If content-type is unknown/generic, inspect body
            if ct_lower in ('', 'application/octet-stream', 'text/plain'):
                try:
                    body_start = body[:500].decode('utf-8', errors='ignore').lstrip()
                    # JS files should NOT start with HTML tags
                    if body_start.startswith(('<!DOCTYPE', '<html', '<HTML', '<!doctype')):
                        return False
                    # Check for common HTML patterns (even without doctype)
                    if '<head>' in body_start[:200].lower() or '<body>' in body_start[:200].lower():
                        return False
                except:
                    pass

        # Validate CSS files - strict check against HTML disguised as CSS
        if url_lower.endswith('.css'):
            # Content-type must be CSS-compatible
            valid_css_types = ('css', 'text/plain', 'application/octet-stream')

            # If content-type is explicitly HTML, reject immediately
            if ct_lower in ('text/html', 'application/xhtml+xml'):
                return False

            # If content-type is unknown/generic, inspect body
            if ct_lower in ('', 'application/octet-stream', 'text/plain'):
                try:
                    body_start = body[:500].decode('utf-8', errors='ignore').lstrip()
                    # CSS files should NOT start with HTML tags
                    if body_start.startswith(('<!DOCTYPE', '<html', '<HTML', '<!doctype')):
                        return False
                    # Check for common HTML patterns
                    if '<head>' in body_start[:200].lower() or '<body>' in body_start[:200].lower():
                        return False
                except:
                    pass

        # Validate JSON files (API responses)
        if 'json' in ct_lower or url_lower.endswith('.json'):
            # JSON should not start with HTML tags (Soft 404 from API)
            try:
                body_start = body[:100].decode('utf-8', errors='ignore').lstrip()
                if body_start.startswith(('<!DOCTYPE', '<html', '<HTML', '<!doctype')):
                    return False
            except:
                pass

        return True

    def _classify_resource(self, content_type, url=''):
        """Classify resource by type for statistics"""
        ct = content_type.lower()
        if 'image' in ct:
            return 'image'
        elif 'javascript' in ct or 'ecmascript' in ct or url.endswith('.js'):
            return 'script'
        elif 'css' in ct or url.endswith('.css'):
            return 'stylesheet'
        elif 'font' in ct or any(url.endswith(ext) for ext in ['.woff', '.woff2', '.ttf', '.otf', '.eot']):
            return 'font'
        elif 'video' in ct or 'audio' in ct:
            return 'media'
        elif 'json' in ct or url.endswith('.json'):
            return 'other'  # JSON APIs classified as 'other' for now
        else:
            return 'other'

    def get_response_handler(self):
        """Return handler for page.on('response')"""
        def capture_response(response):
            try:
                url = response.url

                # Debug: Track all URLs we see
                self.all_seen_urls.append((url, response.status))

                # Skip data/blob URLs
                if url.startswith(('data:', 'blob:')):
                    return

                # FASE 6: Track ignored resources (tracking domains)
                parsed = urlparse(url)
                if any(skip in parsed.netloc for skip in SKIP_DOMAINS):
                    self.ignored_resources.append((url, 'tracking domain'))
                    return

                # Only save successful responses
                if response.status == 200:
                    try:
                        body = response.body()
                        content_type = response.headers.get('content-type', '')

                        # FASE 6: Check size limit
                        from . import MAX_RESOURCE_SIZE
                        if len(body) > MAX_RESOURCE_SIZE:
                            self.ignored_resources.append((url, f'size > {MAX_RESOURCE_SIZE/1024/1024:.0f}MB'))
                            return

                        # CRITICAL FIX: Validate content-type matches expected file extension
                        # Prevents saving HTML error pages as .js/.css files
                        if not self._validate_content_type(url, content_type, body):
                            self.failed_resources.append((url, 'content-type mismatch'))
                            return

                        resource_data = {
                            'body': body,
                            'content_type': content_type
                        }
                        # Store by final URL
                        self.network_resources[url] = resource_data

                        # Also store by original request URL (handles redirects)
                        request_url = response.request.url
                        if request_url != url:
                            self.network_resources[request_url] = resource_data

                        # Update stats
                        res_type = self._classify_resource(content_type, url)
                        self.stats_by_type[res_type] += 1
                    except Exception as e:
                        self.failed_resources.append((url, f'capture error: {str(e)[:50]}'))
                elif response.status >= 400:
                    self.failed_resources.append((url, f'HTTP {response.status}'))
            except:
                pass

        return capture_response

    def _get_extension(self, url, content_type=''):
        """Get file extension from URL or content-type"""
        parsed = urlparse(url)
        path = parsed.path
        _, ext = os.path.splitext(path)

        if ext and len(ext) <= 6:
            return ext

        if content_type:
            mime = content_type.split(';')[0].strip().lower()

            # Explicit mapping for common API content-types
            if 'json' in mime:
                return '.json'
            elif mime == 'text/plain':
                # Don't force .txt for plain text - rely on URL
                pass
            else:
                guessed = mimetypes.guess_extension(mime)
                if guessed:
                    return guessed

        return ''

    def _generate_filename(self, url, content_type='', preserve_structure=True):
        """
        Generate a filename for a resource.

        Args:
            url: Original URL
            content_type: MIME type
            preserve_structure: If True, preserves URL path structure for better compatibility

        Returns:
            Relative path within assets/ (e.g., "gl/textures/diffuse.webp" or "file_hash.ext")
        """
        from urllib.parse import unquote

        parsed = urlparse(url)
        path = parsed.path
        query = parsed.query

        # URL decode path to handle %2C, %20, etc
        path = unquote(path)

        # Remove leading slash
        if path.startswith('/'):
            path = path[1:]

        # Remove "assets/" prefix if present (avoid duplication)
        if path.startswith('assets/'):
            path = path[7:]  # len('assets/') = 7

        # Detect API endpoints (REST APIs, GraphQL, etc) by content-type
        is_api_endpoint = False
        if content_type:
            ct_lower = content_type.lower()
            if 'json' in ct_lower or 'graphql' in ct_lower:
                is_api_endpoint = True

        # CRITICAL FIX: Any URL with query strings must use hash-based naming
        # to avoid collisions. Examples:
        # - /rest/v1/properties?select=A -> properties_hash1.json
        # - /rest/v1/properties?select=B -> properties_hash2.json
        # - /_next/image/?url=X&w=256 -> image_hash3.jpg
        has_query_string = bool(query)

        def _normalize_host(netloc):
            return netloc.lower().lstrip('www.')

        # If preserve_structure and path looks like a real file path (no query string, not an API),
        # preserve the original filename. This keeps runtime relative imports working offline.
        if preserve_structure and path and not has_query_string and not is_api_endpoint:
            # Strip trailing slash — it's a directory-like URL, not a file
            path_clean = path.rstrip('/')
            parts = [part for part in path_clean.split('/') if part]
            # Check: last part must have a file extension or be a meaningful name
            last_part = parts[-1] if parts else ''
            if '?' not in path_clean and last_part:
                clean_parts = []
                parsed_base = urlparse(self.base_url)
                same_origin = _normalize_host(parsed.netloc) == _normalize_host(parsed_base.netloc)

                # Cross-origin root-level files need a stable directory to preserve
                # sibling relative imports without colliding with same-origin assets.
                if len(parts) == 1 and not same_origin and parsed.netloc:
                    host_part = re.sub(r'[^a-zA-Z0-9_@.-]', '_', parsed.netloc)[:100]
                    if host_part:
                        clean_parts.append(host_part)

                for part in parts:
                    if part == parts[-1]:  # Last part (filename)
                        clean_parts.append(part)
                    else:  # Folder names
                        # Preserve @ for npm packages (@rive-app, @react, etc)
                        clean_part = re.sub(r'[^a-zA-Z0-9_@.-]', '_', part)[:50]
                        if clean_part:
                            clean_parts.append(clean_part)

                if clean_parts:
                    structured_path = '/'.join(clean_parts)
                    # Ensure JSON API endpoints get .json extension
                    if is_api_endpoint and not structured_path.endswith('.json'):
                        structured_path += '.json'
                    return structured_path

        # Fallback: hashed filename — includes full URL (with query) for uniqueness
        ext = self._get_extension(url, content_type)

        # Force .json for API endpoints without extension
        if is_api_endpoint and not ext:
            ext = '.json'

        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]

        name = os.path.basename(path.rstrip('/')) if path.rstrip('/') else 'resource'
        if name:
            name = re.sub(r'[^a-zA-Z0-9_-]', '_', name.split('.')[0])[:30]
        else:
            name = 'resource'

        return f"{name}_{url_hash}{ext}"

    def _save_resource(self, url, content, content_type=''):
        """Save a resource to disk and return relative path"""
        if url in self.resource_cache:
            return self.resource_cache[url]

        if not content:
            return None

        filename = self._generate_filename(url, content_type, preserve_structure=True)
        filepath = os.path.join(self.assets_dir, filename)

        # If the generated filename has no extension (directory-like URL ending in /),
        # and the URL actually ends with /, save as index.html inside it.
        # BUT: only if the filename doesn't already have an extension (hash-based names do).
        _, filename_ext = os.path.splitext(filename.rstrip('/'))
        if not filename_ext and url.rstrip('?#').endswith('/'):
            filepath = os.path.join(filepath, 'index.html')
            filename = os.path.join(filename, 'index.html')

        # Create directories if needed
        file_dir = os.path.dirname(filepath)
        if file_dir and not os.path.exists(file_dir):
            os.makedirs(file_dir, exist_ok=True)

        # Safety: if filepath collides with existing directory, append index.html
        if os.path.isdir(filepath):
            filepath = os.path.join(filepath, 'index.html')
            filename = os.path.join(filename, 'index.html')

        with open(filepath, 'wb') as f:
            f.write(content if isinstance(content, bytes) else content.encode('utf-8'))

        rel_path = f"assets/{filename}"
        self.resource_cache[url] = rel_path
        return rel_path

    def _download_fallback(self, url):
        """
        Download a resource with retry logic (FASE 6: 2 attempts with backoff).

        CRITICAL FIX: Block API endpoints from fallback downloads.
        APIs require dynamic headers (Auth tokens, CORS) that requests.get doesn't have.
        Attempting to download them results in 406/401 errors and pollutes logs.
        """
        if url in self.resource_cache:
            return self.resource_cache[url]

        if not url or url.startswith(('data:', 'blob:', '#')):
            return url

        # CRITICAL: Block API endpoints - they need browser context (auth headers, cookies)
        # Attempting requests.get on APIs will ALWAYS fail with 406/401/CORS
        url_lower = url.lower()
        api_indicators = [
            'supabase.co',
            '/rest/v1/',
            '/api/',
            '/graphql',
            'api.',  # api.domain.com
        ]

        if any(indicator in url_lower for indicator in api_indicators):
            # This is an API endpoint - don't attempt fallback download
            # Let the fetch_interceptor handle it with mocks
            self.log(f"   Bloqueando fallback de API: {url[:80]}...")
            return None

        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=RESOURCE_TIMEOUT, verify=False)
                if response.status_code == 200:
                    # FASE 6: Check size limit
                    from . import MAX_RESOURCE_SIZE
                    if len(response.content) > MAX_RESOURCE_SIZE:
                        self.ignored_resources.append((url, f'size > {MAX_RESOURCE_SIZE/1024/1024:.0f}MB'))
                        return None

                    content_type = response.headers.get('content-type', '')

                    # CRITICAL FIX: Validate content-type to prevent Soft 404
                    if not self._validate_content_type(url, content_type, response.content):
                        self.failed_resources.append((url, 'content-type mismatch (Soft 404)'))
                        return None

                    local_path = self._save_resource(url, response.content, content_type)
                    return local_path
                else:
                    last_error = f'HTTP {response.status_code}'
            except Exception as e:
                last_error = str(e)[:50]
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BACKOFF ** attempt)
                    continue

        # FASE 6: Track failed download
        if last_error:
            self.failed_resources.append((url, last_error))

        return None

    def get_resource(self, url, base=None):
        """Get a resource - from cache, network capture, or fallback download"""
        if not url or url.startswith(('data:', 'blob:', '#')):
            return url

        # CRITICAL FIX: Ensure base URL ends with / for correct urljoin behavior
        # Without this, urljoin("https://domain.com", "assets/file.png")
        # becomes "https://domain.comassets/file.png" (missing slash)
        base_url = base or self.base_url
        if not base_url.endswith('/'):
            base_url = base_url + '/'

        # Make absolute URL
        abs_url = urljoin(base_url, url)

        # Check cache first
        if abs_url in self.resource_cache:
            return self.resource_cache[abs_url]

        # Check network captures
        if abs_url in self.network_resources:
            res = self.network_resources[abs_url]
            return self._save_resource(abs_url, res['body'], res.get('content_type', ''))

        # Fallback download
        local_path = self._download_fallback(abs_url)
        if local_path:
            return local_path

        # Return original if all fails
        return url

    def save_all_captured_resources(self):
        """FASE 3: Save all network-captured resources to disk"""
        saved_count = 0
        for url, resource_data in self.network_resources.items():
            if url not in self.resource_cache:
                local_path = self._save_resource(url, resource_data['body'], resource_data.get('content_type', ''))
                if local_path:
                    saved_count += 1

        if saved_count > 0:
            self.log(f"   {saved_count} recursos salvos em disco")

        # NOVO: pós-processamento de .m3u8 para garantir todos os chunks/variantes
        self.postprocess_m3u8_files()

        # CRITICAL: Extract chunks/assets referenced in JS files (Vite, Next.js, Webpack)
        self.extract_css_from_js_files()

    def ensure_resources_downloaded(self, urls):
        """
        Download any URLs from the list that are not already in resource_cache.

        Used to ensure dynamically-injected stylesheets (e.g. Next.js router CSS)
        are saved even if they were missed by the Playwright response handler.
        """
        if not urls:
            return
        downloaded = 0
        for url in urls:
            if not url or url in self.resource_cache:
                continue
            local_path = self._download_fallback(url)
            if local_path:
                downloaded += 1
        if downloaded:
            self.log(f"   {downloaded} stylesheet(s) baixados via fallback")

    def get_resource_map(self):
        """Return the resource_map for URL rewriting"""
        return self.resource_cache.copy()

    def get_stats(self):
        """Return statistics"""
        return {
            'captured': len(self.network_resources),
            'saved': len(self.resource_cache),
            'by_type': self.stats_by_type.copy()
        }

    def log_stats(self):
        """Log detailed statistics"""
        stats = self.get_stats()
        self.log(f"Recursos capturados por tipo:")
        if stats['by_type']['image'] > 0:
            self.log(f"   Imagens: {stats['by_type']['image']}")
        if stats['by_type']['script'] > 0:
            self.log(f"   Scripts: {stats['by_type']['script']}")
        if stats['by_type']['stylesheet'] > 0:
            self.log(f"   CSS: {stats['by_type']['stylesheet']}")
        if stats['by_type']['font'] > 0:
            self.log(f"   Fonts: {stats['by_type']['font']}")
        if stats['by_type']['media'] > 0:
            self.log(f"   Mídia: {stats['by_type']['media']}")
        if stats['by_type']['other'] > 0:
            self.log(f"   Outros: {stats['by_type']['other']}")

    def generate_final_report(self):
        """FASE 6: Generate comprehensive final report"""
        self.log("\n" + "="*60)
        self.log("RELATÓRIO FINAL")
        self.log("="*60)

        # Resources by type
        total = sum(self.stats_by_type.values())
        self.log(f"\nTotal baixado: {total} recursos")
        for res_type, count in self.stats_by_type.items():
            if count > 0:
                percentage = (count / total * 100) if total > 0 else 0
                emoji = {'image': '🖼️', 'script': '📝', 'stylesheet': '🎨',
                        'font': '✍️', 'media': '🎬', 'other': '📦'}[res_type]
                self.log(f"   {emoji} {res_type.capitalize()}: {count} ({percentage:.1f}%)")

        # Debug: Critical URLs seen but not captured
        critical_patterns = ['webgl', 'draco', 'texture', 'wasm', '.glb', '.gltf']
        critical_seen = []
        for url, status in self.all_seen_urls:
            if any(pattern in url.lower() for pattern in critical_patterns):
                if url not in self.network_resources:
                    critical_seen.append((url, status))

        if critical_seen:
            self.log(f"\nURLs críticas vistas mas NÃO capturadas: {len(critical_seen)}")
            for url, status in critical_seen[:10]:
                short_url = url[:80] + '...' if len(url) > 80 else url
                self.log(f"   - [HTTP {status}] {short_url}")
            if len(critical_seen) > 10:
                self.log(f"   ... e mais {len(critical_seen) - 10}")

        # Failed resources
        if self.failed_resources:
            self.log(f"\nFalhas: {len(self.failed_resources)} recursos")
            # Show up to 20
            for url, reason in self.failed_resources[:20]:
                short_url = url[:60] + '...' if len(url) > 60 else url
                self.log(f"   - {short_url}")
                self.log(f"     Motivo: {reason}")
            if len(self.failed_resources) > 20:
                self.log(f"   ... e mais {len(self.failed_resources) - 20}")

        # Ignored resources
        if self.ignored_resources:
            self.log(f"\nIgnorados: {len(self.ignored_resources)} recursos")
            # Group by reason
            by_reason = {}
            for url, reason in self.ignored_resources:
                by_reason.setdefault(reason, []).append(url)
            for reason, urls in by_reason.items():
                self.log(f"   - {reason}: {len(urls)}")

        self.log("="*60 + "\n")
