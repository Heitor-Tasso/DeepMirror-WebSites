"""
Clean - Optimize downloaded site for AI consumption.

Strategy: Segregation of Responsibility.
- raw/: Exact copy, fully functional.
- clean/: Readable for AI — desminified, annotated, noise-removed.
  - HTML: Remove analytics attributes, simplify large inline SVGs.
  - CSS: Desminify, remove comments (cssbeautifier).
  - JS:  Remove console.*, debugger, block comments from non-minified files.
"""
import os
import re
import shutil
from pathlib import Path

try:
    import cssbeautifier
    _CSSBEAUTIFIER_AVAILABLE = True
except ImportError:
    _CSSBEAUTIFIER_AVAILABLE = False

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False


# Attributes that are purely for analytics/tracking — safe to remove from HTML
_ANALYTICS_ATTRS = re.compile(
    r'''\s+(?:data-(?:test(?:-id)?|testid|cy|qa|gtm(?:-[^\s=]+)?|analytics(?:-[^\s=]+)?|tracking(?:-[^\s=]+)?|g-tag|g-tm|hs-[^\s=]+|heap-[^\s=]+|amplitude-[^\s=]+|segment-[^\s=]+|mixpanel-[^\s=]+|fb-[^\s=]+|pixel-[^\s=]+))=["\'][^"\']*["\']''',
    re.IGNORECASE,
)

# SVG path data length threshold: paths longer than this are considered "complex"
_SVG_PATH_COMPLEXITY_THRESHOLD = 80

# Known vendor JS library patterns (filename substrings)
_VENDOR_JS_PATTERNS = [
    'jquery', 'react', 'react-dom', 'vue', 'angular', 'gsap', 'three',
    'framer-motion', 'lottie', 'swiper', 'locomotive', 'lenis', 'split-type',
    'bootstrap', 'tailwind', 'normalize', 'modernizr', 'lodash', 'underscore',
    'moment', 'dayjs', 'axios', 'babel', 'polyfill', 'webpack', 'vite',
]


class SiteCleaner:
    """Cleans downloaded site to optimize for AI token consumption."""

    def __init__(self, site_dir, log_callback):
        self.site_dir = Path(site_dir)
        self.log = log_callback
        self.stats = {
            'html_cleaned': 0,
            'css_cleaned': 0,
            'js_cleaned': 0,
            'total_bytes_saved': 0,
        }

    def _site_size_bytes(self):
        total = 0
        for path in self.site_dir.rglob('*'):
            if path.is_file():
                try:
                    total += path.stat().st_size
                except OSError:
                    continue
        return total

    def _should_skip_clean_copy(self):
        clean_mode = os.getenv('DM_CLEAN_MODE', 'full').strip().lower()
        if clean_mode == 'raw-only':
            self.log("   Modo raw-only ativo: versão clean será pulada")
            return True

        size_limit_mb = os.getenv('DM_CLEAN_MAX_SIZE_MB', '').strip()
        if not size_limit_mb:
            return False

        try:
            size_limit_bytes = int(float(size_limit_mb) * 1024 * 1024)
        except ValueError:
            self.log(f"   Aviso: DM_CLEAN_MAX_SIZE_MB inválido ({size_limit_mb}), ignorando limite")
            return False

        current_size = self._site_size_bytes()
        if current_size >= size_limit_bytes:
            self.log(
                f"   Site com {current_size / (1024 * 1024):.1f} MB excede limite de "
                f"{size_limit_mb} MB: versão clean será pulada"
            )
            return True

        return False

    def process(self):
        """
        Produce two versions:
        - raw/: Exact copy (functional backup).
        - clean/: Optimized for AI analysis.
        """
        self.log("Iniciando limpeza inteligente para consumo por IA...")

        raw_dir = self.site_dir / 'raw'
        clean_dir = self.site_dir / 'clean'

        self.log("   Criando versão raw (backup original)...")
        if raw_dir.exists():
            shutil.rmtree(raw_dir)
        shutil.copytree(self.site_dir, raw_dir, ignore=shutil.ignore_patterns('raw', 'clean'))

        skip_clean_copy = self._should_skip_clean_copy()
        if clean_dir.exists():
            shutil.rmtree(clean_dir)

        if not skip_clean_copy:
            self.log("   Criando versão clean (otimizada para IA)...")
            shutil.copytree(self.site_dir, clean_dir, ignore=shutil.ignore_patterns('raw', 'clean'))
            self._clean_directory(clean_dir)

        serve_template = Path(__file__).parent.parent / 'templates' / 'serve_template.py'
        if serve_template.exists():
            shutil.copy(serve_template, raw_dir / 'serve.py')
            if not skip_clean_copy:
                shutil.copy(serve_template, clean_dir / 'serve.py')

        for item in self.site_dir.iterdir():
            if item.name not in ['raw', 'clean', 'serve.py']:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        bytes_saved = self.stats['total_bytes_saved']
        if bytes_saved > 1024 * 1024:
            size_str = f"{bytes_saved / (1024 * 1024):.2f} MB"
        elif bytes_saved > 1024:
            size_str = f"{bytes_saved / 1024:.2f} KB"
        else:
            size_str = f"{bytes_saved} bytes"

        self.log(f"   Limpeza completa:")
        self.log(f"      - {self.stats['html_cleaned']} arquivos HTML")
        self.log(f"      - {self.stats['css_cleaned']} arquivos CSS")
        self.log(f"      - {self.stats['js_cleaned']} arquivos JS")
        self.log(f"      - ~{size_str} economizados")
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Directory walker
    # ─────────────────────────────────────────────────────────────────────────

    def _clean_directory(self, directory):
        for root, dirs, files in os.walk(directory):
            for filename in files:
                filepath = Path(root) / filename
                ext = filepath.suffix.lower()
                if ext == '.html':
                    self._clean_html_file(filepath)
                elif ext == '.css':
                    self._clean_css_file(filepath)
                elif ext == '.js':
                    self._clean_js_file(filepath)

    # ─────────────────────────────────────────────────────────────────────────
    # Per-file entry points
    # ─────────────────────────────────────────────────────────────────────────

    def _clean_html_file(self, filepath):
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            original_size = len(content)
            content = self._process_html(content)
            filepath.write_text(content, encoding='utf-8')
            self.stats['html_cleaned'] += 1
            self.stats['total_bytes_saved'] += (original_size - len(content))
        except Exception:
            pass

    def _clean_css_file(self, filepath):
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            original_size = len(content)
            content = self._process_css(content)
            filepath.write_text(content, encoding='utf-8')
            self.stats['css_cleaned'] += 1
            self.stats['total_bytes_saved'] += (original_size - len(content))
        except Exception:
            pass

    def _clean_js_file(self, filepath):
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            original_size = len(content)
            content = self._process_js(content, filepath.name)
            if len(content) < original_size:
                filepath.write_text(content, encoding='utf-8')
                self.stats['js_cleaned'] += 1
                self.stats['total_bytes_saved'] += (original_size - len(content))
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # HTML processing
    # ─────────────────────────────────────────────────────────────────────────

    def _process_html(self, content):
        """
        Clean HTML for AI readability:
        1. Remove HTML comments (preserve IE conditionals).
        2. Remove analytics/tracking data attributes.
        3. Simplify complex inline SVG path data.
        4. Normalize excessive blank lines.
        """
        # 1. Remove HTML comments (preserve <!--[if IE]> conditionals)
        content = re.sub(r'<!--(?!\[if).*?-->', '', content, flags=re.DOTALL)

        # 2. Remove analytics/tracking data attributes
        content = _ANALYTICS_ATTRS.sub('', content)

        # 3. Simplify large inline SVG paths using BeautifulSoup
        if _BS4_AVAILABLE:
            content = self._simplify_svg_paths(content)

        # 4. Normalize whitespace
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)

        return content

    def _simplify_svg_paths(self, html_content):
        """
        Replace complex SVG <path d="..."> data with a human-readable placeholder.
        The AI needs to know an icon exists, not its bezier coordinates.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            modified = False

            for path in soup.find_all('path', d=True):
                d = path.get('d', '')
                if len(d) > _SVG_PATH_COMPLEXITY_THRESHOLD:
                    path['d'] = '[complex-path]'
                    modified = True

            if modified:
                return str(soup)
        except Exception:
            pass
        return html_content

    # ─────────────────────────────────────────────────────────────────────────
    # CSS processing
    # ─────────────────────────────────────────────────────────────────────────

    def _process_css(self, content):
        """
        Clean CSS for AI readability:
        1. Desminify with cssbeautifier (most impactful step).
        2. Remove comments.
        3. Normalize blank lines.
        """
        # 1. Desminify (expands single-line minified CSS to readable multi-line)
        if _CSSBEAUTIFIER_AVAILABLE:
            opts = cssbeautifier.default_options()
            opts.indent_size = 2
            opts.end_with_newline = True
            opts.newline_between_rules = True
            try:
                content = cssbeautifier.beautify(content, opts)
            except Exception:
                pass

        # 2. Remove CSS comments (/* ... */) — never functional in CSS
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # 3. Normalize whitespace
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)

        return content

    # ─────────────────────────────────────────────────────────────────────────
    # JS processing
    # ─────────────────────────────────────────────────────────────────────────

    def _process_js(self, content, filename=''):
        """
        Clean JS for AI readability:
        - Vendor/library files: conservative — only remove console.* and debugger.
        - Minified files: conservative — same.
        - Non-minified app code: remove console.*, debugger, comments.
        """
        is_vendor = any(p in filename.lower() for p in _VENDOR_JS_PATTERNS)
        lines = content.split('\n')
        is_minified = len(lines) < 10 or (len(content) / max(len(lines), 1)) > 200

        if is_vendor or is_minified:
            content = self._clean_minified_js(content)
        else:
            content = self._clean_formatted_js(content)

        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        return content

    def _clean_minified_js(self, content):
        """Ultra-conservative: only remove console.* and debugger."""
        for method in ('log', 'warn', 'error', 'info', 'debug'):
            content = re.sub(rf'console\.{method}\([^;]*?\);?', '', content)
        content = re.sub(r'\bdebugger\s*;?', '', content)
        return content

    def _clean_formatted_js(self, content):
        """Remove console.*, debugger, block/line comments from non-minified JS."""
        lines = content.split('\n')
        cleaned = []

        for line in lines:
            # Skip full console.* statement lines
            if re.match(r'^\s*console\.(log|warn|error|info|debug)\s*\(', line):
                continue
            # Skip debugger lines
            if re.match(r'^\s*debugger\s*;?\s*$', line):
                continue
            # Skip full-line comments (unless important)
            if re.match(r'^\s*//', line):
                if self._is_important_comment(line):
                    cleaned.append(line)
                continue
            cleaned.append(line)

        content = '\n'.join(cleaned)
        content = self._remove_block_comments(content)
        return content

    def _is_important_comment(self, line):
        keywords = ['@license', 'copyright', '(c)', 'mit license', 'bsd license', 'apache', 'gpl']
        lower = line.lower()
        return any(k in lower for k in keywords)

    def _remove_block_comments(self, content):
        def replacer(match):
            if self._is_important_comment(match.group(0)):
                return match.group(0)
            return ''
        return re.sub(r'/\*.*?\*/', replacer, content, flags=re.DOTALL)


def clean_site(site_dir, log_callback):
    """Public API for cleaning a downloaded site."""
    cleaner = SiteCleaner(site_dir, log_callback)
    return cleaner.process()
