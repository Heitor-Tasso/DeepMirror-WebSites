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
            mime = content_type.split(';')[0].strip()
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

        # URLs with significant query strings (API endpoints like /_next/image/?url=...)
        # must use hash-based naming to avoid collisions — skip structure preservation
        has_significant_query = bool(query) and path.rstrip('/') in (
            '_next/image', 'image', 'api/image', '_next/static/image'
        )

        # If preserve_structure and path looks like a file path (not an API endpoint)
        if preserve_structure and path and '/' in path and not has_significant_query:
            # Strip trailing slash — it's a directory-like URL, not a file
            path_clean = path.rstrip('/')
            parts = path_clean.split('/')
            # Check: last part must have a file extension or be a meaningful name
            last_part = parts[-1] if parts else ''
            if len(parts) >= 2 and '?' not in path_clean and last_part:
                clean_parts = []
                for part in parts:
                    if part == parts[-1]:  # Last part (filename)
                        clean_parts.append(part)
                    else:  # Folder names
                        # Preserve @ for npm packages (@rive-app, @react, etc)
                        clean_part = re.sub(r'[^a-zA-Z0-9_@.-]', '_', part)[:50]
                        if clean_part:
                            clean_parts.append(clean_part)

                if clean_parts:
                    return '/'.join(clean_parts)

        # Fallback: hashed filename — includes full URL (with query) for uniqueness
        ext = self._get_extension(url, content_type)
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
        """Download a resource with retry logic (FASE 6: 2 attempts with backoff)"""
        if url in self.resource_cache:
            return self.resource_cache[url]

        if not url or url.startswith(('data:', 'blob:', '#')):
            return url

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
