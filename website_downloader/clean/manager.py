"""
Site cleaner orchestration.
"""
import os
import shutil
from pathlib import Path

from .. import CLEAN_MAX_SIZE_MB, CLEAN_MAX_SIZE_MB_INVALID, CLEAN_MODE
from .clean_css import clean_css_content
from .clean_html import clean_html_content
from .clean_js import clean_js_content


class SiteCleaner:
    """Clean downloaded sites and organize raw/clean artifacts."""

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
        if CLEAN_MODE == 'raw-only':
            self.log("   Modo raw-only ativo: versão clean será pulada")
            return True

        if CLEAN_MAX_SIZE_MB_INVALID:
            self.log(
                f"   Aviso: DM_CLEAN_MAX_SIZE_MB inválido ({CLEAN_MAX_SIZE_MB_INVALID}), ignorando limite"
            )
            return False

        if CLEAN_MAX_SIZE_MB is None:
            return False

        size_limit_bytes = int(CLEAN_MAX_SIZE_MB * 1024 * 1024)
        current_size = self._site_size_bytes()
        if current_size >= size_limit_bytes:
            self.log(
                f"   Site com {current_size / (1024 * 1024):.1f} MB excede limite de "
                f"{CLEAN_MAX_SIZE_MB:g} MB: versão clean será pulada"
            )
            return True

        return False

    def _copy_site_snapshot(self, destination):
        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=True)

        for item in self.site_dir.iterdir():
            if item.name in {'raw', 'clean', 'serve.py'}:
                continue

            target = destination / item.name
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)

    def process(self):
        self.log("Iniciando limpeza inteligente para consumo por IA...")

        raw_dir = self.site_dir / 'raw'
        clean_dir = self.site_dir / 'clean'

        self.log("   Criando versão raw (backup original)...")
        self._copy_site_snapshot(raw_dir)

        skip_clean_copy = self._should_skip_clean_copy()
        if clean_dir.exists():
            shutil.rmtree(clean_dir)

        if not skip_clean_copy:
            self.log("   Criando versão clean (otimizada para IA)...")
            self._copy_site_snapshot(clean_dir)
            self._clean_directory(clean_dir)

        serve_template = Path(__file__).parent.parent.parent / 'templates' / 'serve_template.py'
        if serve_template.exists():
            shutil.copy(serve_template, raw_dir / 'serve.py')
            if not skip_clean_copy:
                shutil.copy(serve_template, clean_dir / 'serve.py')

        for item in self.site_dir.iterdir():
            if item.name not in {'raw', 'clean', 'serve.py'}:
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

        self.log("   Limpeza completa:")
        self.log(f"      - {self.stats['html_cleaned']} arquivos HTML")
        self.log(f"      - {self.stats['css_cleaned']} arquivos CSS")
        self.log(f"      - {self.stats['js_cleaned']} arquivos JS")
        self.log(f"      - ~{size_str} economizados")
        return True

    def _clean_directory(self, directory):
        for root, _dirs, files in os.walk(directory):
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
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            original_size = len(content)
            cleaned = clean_html_content(content)
            filepath.write_text(cleaned, encoding='utf-8')
            self.stats['html_cleaned'] += 1
            self.stats['total_bytes_saved'] += (original_size - len(cleaned))
        except Exception:
            pass

    def _clean_css_file(self, filepath):
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            original_size = len(content)
            cleaned = clean_css_content(content)
            filepath.write_text(cleaned, encoding='utf-8')
            self.stats['css_cleaned'] += 1
            self.stats['total_bytes_saved'] += (original_size - len(cleaned))
        except Exception:
            pass

    def _clean_js_file(self, filepath):
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            original_size = len(content)
            cleaned = clean_js_content(content, filepath.name)
            if len(cleaned) < original_size:
                filepath.write_text(cleaned, encoding='utf-8')
                self.stats['js_cleaned'] += 1
                self.stats['total_bytes_saved'] += (original_size - len(cleaned))
        except Exception:
            pass


def clean_site(site_dir, log_callback):
    """Public API for cleaning a downloaded site."""
    cleaner = SiteCleaner(site_dir, log_callback)
    return cleaner.process()
