"""
Clean - Optimize downloaded site for AI consumption
Creates two versions: raw (original) and clean (optimized for tokens)
"""
import os
import re
import shutil
from pathlib import Path


class SiteCleaner:
    """Cleans downloaded site to optimize for AI token consumption"""

    def __init__(self, site_dir, log_callback):
        self.site_dir = Path(site_dir)
        self.log = log_callback
        self.stats = {
            'html_cleaned': 0,
            'css_cleaned': 0,
            'js_cleaned': 0,
            'total_lines_removed': 0,
        }

    def process(self):
        """
        Create two versions of the site:
        - raw/: Exact copy of original download
        - clean/: Optimized for AI (reduced whitespace, removed comments)
        """
        self.log("🧹 Iniciando limpeza para consumo por IA...")

        # Create directories
        raw_dir = self.site_dir / 'raw'
        clean_dir = self.site_dir / 'clean'

        # Copy original to raw/ (exact backup)
        self.log("   📦 Criando versão raw (backup original)...")
        if raw_dir.exists():
            shutil.rmtree(raw_dir)
        shutil.copytree(self.site_dir, raw_dir, ignore=shutil.ignore_patterns('raw', 'clean'))

        # Create clean version
        self.log("   ✨ Criando versão clean (otimizada para IA)...")
        if clean_dir.exists():
            shutil.rmtree(clean_dir)
        shutil.copytree(self.site_dir, clean_dir, ignore=shutil.ignore_patterns('raw', 'clean'))

        # Clean all files in clean/
        self._clean_directory(clean_dir)

        # Copy serve.py to both raw/ and clean/
        serve_template = Path(__file__).parent.parent / 'templates' / 'serve_template.py'
        if serve_template.exists():
            shutil.copy(serve_template, raw_dir / 'serve.py')
            shutil.copy(serve_template, clean_dir / 'serve.py')

        # Remove original files (keep only raw/, clean/, and serve.py)
        # This prevents ZIP from having duplicate content
        # Note: serve.py might not exist yet (created by downloader.py after this)
        for item in self.site_dir.iterdir():
            if item.name not in ['raw', 'clean', 'serve.py']:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        self.log(f"   ✅ Limpeza completa:")
        self.log(f"      • {self.stats['html_cleaned']} arquivos HTML")
        self.log(f"      • {self.stats['css_cleaned']} arquivos CSS")
        self.log(f"      • {self.stats['js_cleaned']} arquivos JS")
        self.log(f"      • ~{self.stats['total_lines_removed']} linhas removidas")

        return True

    def _clean_directory(self, directory):
        """Recursively clean all text files in directory"""
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

    def _clean_html_file(self, filepath):
        """Clean HTML file"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            original_lines = content.count('\n')
            content = self._process_html(content)
            new_lines = content.count('\n')

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            self.stats['html_cleaned'] += 1
            self.stats['total_lines_removed'] += (original_lines - new_lines)
        except:
            pass  # Skip files that can't be processed

    def _clean_css_file(self, filepath):
        """Clean CSS file"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            original_lines = content.count('\n')
            content = self._process_css(content)
            new_lines = content.count('\n')

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            self.stats['css_cleaned'] += 1
            self.stats['total_lines_removed'] += (original_lines - new_lines)
        except:
            pass

    def _clean_js_file(self, filepath):
        """Clean JS file"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Skip if already minified (single line or very few lines)
            if content.count('\n') < 10:
                return  # Already minified, don't touch

            original_lines = content.count('\n')
            content = self._process_js(content)
            new_lines = content.count('\n')

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            self.stats['js_cleaned'] += 1
            self.stats['total_lines_removed'] += (original_lines - new_lines)
        except:
            pass

    def _process_html(self, content):
        """
        Process HTML content - ULTRA CONSERVATIVE MODE
        Preserve ALL functional elements. Only reduce excessive blank lines.

        DO NOT remove:
        - HTML comments (may be DOM markers for frameworks like UnicornStudio, React, etc.)
        - Canvas elements (WebGL/Rive mount points)
        - Empty divs/spans with id/class/data-* (JS mount points)
        - Inline scripts (may contain critical config/state)
        - Meta tags (some frameworks read them at runtime)
        """
        # ONLY normalize whitespace: reduce 4+ consecutive blank lines to 2
        content = re.sub(r'\n\s*\n\s*\n\s*\n+', '\n\n', content)

        return content

    def _process_css(self, content):
        """Process CSS content - conservative: only remove comments and blank lines"""
        # Remove CSS comments (safe — comments are never functional in CSS)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # Reduce multiple blank lines to max 1
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)

        return content

    def _process_js(self, content):
        """Process JS content"""
        # CRITICAL: DO NOT remove comments in JS - too risky
        # Removing // can break:
        # - Regex patterns: /pattern/
        # - URLs: http://, https://
        # - Division operators followed by comments

        # Only normalize whitespace: reduce multiple blank lines to max 1
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)

        # Remove completely empty lines
        lines = [line for line in content.split('\n') if line.strip()]

        return '\n'.join(lines)


def clean_site(site_dir, log_callback):
    """
    Public API for cleaning a downloaded site.

    Args:
        site_dir: Path to the downloaded site directory
        log_callback: Function to log messages

    Returns:
        True if successful
    """
    cleaner = SiteCleaner(site_dir, log_callback)
    return cleaner.process()
