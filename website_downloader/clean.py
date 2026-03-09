"""
Clean - Optimize downloaded site for AI consumption
REFACTORED: Intelligent cleaning that reduces noise without breaking functionality
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
            'total_bytes_saved': 0,
        }

    def process(self):
        """
        Create two versions of the site:
        - raw/: Exact copy of original download
        - clean/: Optimized for AI (reduced comments, console.logs, etc.)
        """
        self.log("Iniciando limpeza inteligente para consumo por IA...")

        # Create directories
        raw_dir = self.site_dir / 'raw'
        clean_dir = self.site_dir / 'clean'

        # Copy original to raw/ (exact backup)
        self.log("   Criando versão raw (backup original)...")
        if raw_dir.exists():
            shutil.rmtree(raw_dir)
        shutil.copytree(self.site_dir, raw_dir, ignore=shutil.ignore_patterns('raw', 'clean'))

        # Create clean version
        self.log("   Criando versão clean (otimizada para IA)...")
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
        for item in self.site_dir.iterdir():
            if item.name not in ['raw', 'clean', 'serve.py']:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        # Format bytes saved
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
        """Clean HTML file - intelligent removal of noise"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            original_size = len(content)
            content = self._process_html(content)
            new_size = len(content)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            self.stats['html_cleaned'] += 1
            self.stats['total_bytes_saved'] += (original_size - new_size)
        except:
            pass

    def _clean_css_file(self, filepath):
        """Clean CSS file - safe removal of comments and whitespace"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            original_size = len(content)
            content = self._process_css(content)
            new_size = len(content)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            self.stats['css_cleaned'] += 1
            self.stats['total_bytes_saved'] += (original_size - new_size)
        except:
            pass

    def _clean_js_file(self, filepath):
        """Clean JS file - surgical removal of debug code"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            original_size = len(content)
            content = self._process_js(content)
            new_size = len(content)

            # Only write if we actually saved space
            if new_size < original_size:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

                self.stats['js_cleaned'] += 1
                self.stats['total_bytes_saved'] += (original_size - new_size)
        except:
            pass

    def _process_html(self, content):
        """
        Process HTML content - INTELLIGENT CLEANING

        Safe to remove:
        - HTML comments (except IE conditionals, which we preserve)
        - Excessive blank lines
        - Test/analytics attributes (data-test-id, data-gtm, etc.)

        Preserve:
        - Framework markers (data-v-*, data-react*, etc.)
        - Inline scripts/styles (functional)
        - Meta tags
        - All structural elements
        """
        # 1. Remove HTML comments (but preserve IE conditionals like <!--[if IE]>)
        # Match: <!-- not followed by [if
        content = re.sub(r'<!--(?!\[if).*?-->', '', content, flags=re.DOTALL)

        # 2. Remove test/analytics attributes
        test_attributes = [
            r'\s+data-test-id="[^"]*"',
            r'\s+data-testid="[^"]*"',
            r'\s+data-cy="[^"]*"',
            r'\s+data-test="[^"]*"',
            r'\s+data-gtm="[^"]*"',
            r'\s+data-gtm-[^=]+="[^"]*"',
            r'\s+data-analytics="[^"]*"',
            r'\s+data-analytics-[^=]+="[^"]*"',
            r'\s+data-tracking="[^"]*"',
            r'\s+data-qa="[^"]*"',
        ]
        for pattern in test_attributes:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)

        # 3. Normalize whitespace: reduce 3+ consecutive blank lines to 2
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)

        return content

    def _process_css(self, content):
        """
        Process CSS content - SAFE REMOVAL

        Safe to remove:
        - Comments (CSS comments are never functional)
        - Excessive blank lines

        Preserve:
        - All CSS rules (even if seemingly unused - may be JS-dependent)
        - Whitespace that affects parsing
        """
        # 1. Remove CSS comments
        # Match: /* ... */ but preserve minified code integrity
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        # 2. Normalize whitespace: reduce multiple blank lines to max 2
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)

        # 3. Remove trailing whitespace from lines (safe)
        content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)

        return content

    def _process_js(self, content):
        """
        Process JS content - SURGICAL REMOVAL

        Safe to remove (CAREFULLY):
        - console.log/warn/error/info statements
        - debugger statements
        - Single-line comments starting with // (WITH EXCEPTIONS)
        - Block comments /* ... */ (WITH EXCEPTIONS)

        CRITICAL: DO NOT break:
        - Regex patterns containing // (e.g., /https?:\/\//)
        - Division operators (a / b)
        - URLs in strings ("https://example.com")
        - License headers (preserve for legal reasons)

        Strategy: Use context-aware regex that only matches actual comments/console.log
        """
        original_content = content

        # Check if file is minified (heuristic: < 10 lines OR average line length > 200 chars)
        lines = content.split('\n')
        is_minified = len(lines) < 10 or (len(content) / max(len(lines), 1)) > 200

        if is_minified:
            # For minified files: only remove console.* and debugger (safer)
            content = self._clean_minified_js(content)
        else:
            # For non-minified files: more aggressive cleaning
            content = self._clean_formatted_js(content)

        # Final: normalize excessive blank lines
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)

        return content

    def _clean_minified_js(self, content):
        """
        Clean minified JavaScript (single-line or very few lines)

        Strategy: ULTRA CONSERVATIVE
        - Only remove console.* calls
        - Only remove debugger statements
        - NO comment removal (too risky in minified code)
        """
        # Remove console.* statements
        # Pattern: console.log(...), console.warn(...), etc.
        # Must handle nested parentheses and strings carefully

        # Simple approach: match console.method(...) where ... doesn't cross statement boundaries
        # Look for: console.log( ... ); or console.log( ... ),
        patterns = [
            r'console\.log\([^;]*?\);?',
            r'console\.warn\([^;]*?\);?',
            r'console\.error\([^;]*?\);?',
            r'console\.info\([^;]*?\);?',
            r'console\.debug\([^;]*?\);?',
        ]

        for pattern in patterns:
            # Use non-greedy matching and be careful with statement terminators
            content = re.sub(pattern, '', content)

        # Remove debugger statements
        content = re.sub(r'\bdebugger\s*;?', '', content)

        return content

    def _clean_formatted_js(self, content):
        """
        Clean formatted (non-minified) JavaScript

        Strategy: CAREFUL REMOVAL
        - Remove console.* statements (line by line)
        - Remove debugger statements
        - Remove single-line comments // (but NOT in strings or regex)
        - Remove block comments /* ... */ (but preserve license headers)
        """
        lines = content.split('\n')
        cleaned_lines = []

        in_multiline_comment = False
        in_string = False
        string_char = None
        preserve_comment_block = False

        for line in lines:
            original_line = line

            # Check if line contains console.* statement
            # Match: console.log(...), console.warn(...), etc.
            # Only match if it's a full statement (not in strings)
            if re.search(r'^\s*console\.(log|warn|error|info|debug)\s*\(', line):
                # Skip this line (it's a console statement)
                continue

            # Check if line contains debugger
            if re.match(r'^\s*debugger\s*;?\s*$', line):
                # Skip this line (it's a debugger statement)
                continue

            # Remove single-line comments (but be careful)
            # Only remove if:
            # 1. Line starts with // (after optional whitespace)
            # 2. OR comment is at end of line after code
            if re.match(r'^\s*//', line):
                # Entire line is a comment - check if it's a license/important comment
                if self._is_important_comment(line):
                    cleaned_lines.append(line)
                # Otherwise skip
                continue
            else:
                # Check for trailing comments (e.g., "var x = 5; // comment")
                # Only remove if not in a string
                # Simple heuristic: if // appears after code and not in quotes
                match = re.search(r'^([^"\']*?)\s+//.*$', line)
                if match:
                    # Extract code part before comment
                    code_part = match.group(1)
                    # Verify it's not in a string by checking balanced quotes
                    if self._is_trailing_comment_safe(line):
                        line = code_part.rstrip()

            # Add the cleaned line
            cleaned_lines.append(line)

        content = '\n'.join(cleaned_lines)

        # Remove block comments /* ... */ (but preserve licenses)
        content = self._remove_block_comments(content)

        return content

    def _is_important_comment(self, line):
        """
        Check if a comment line is important (license, copyright, etc.)

        Important markers:
        - @license
        - Copyright
        - (c)
        - MIT, BSD, Apache, GPL
        """
        important_keywords = [
            '@license',
            'copyright',
            '(c)',
            'mit license',
            'bsd license',
            'apache',
            'gnu general public license',
            'gpl',
        ]

        line_lower = line.lower()
        return any(keyword in line_lower for keyword in important_keywords)

    def _is_trailing_comment_safe(self, line):
        """
        Check if removing a trailing comment // is safe

        Safe if:
        - Not inside a string literal
        - Not inside a regex pattern

        Heuristic: count quotes before // to determine if we're in a string
        """
        # Find position of //
        comment_pos = line.find('//')
        if comment_pos == -1:
            return False

        # Count quotes before comment
        before_comment = line[:comment_pos]

        # Count single and double quotes
        single_quotes = before_comment.count("'") - before_comment.count("\\'")
        double_quotes = before_comment.count('"') - before_comment.count('\\"')

        # If odd number of quotes, we're likely inside a string
        if single_quotes % 2 != 0 or double_quotes % 2 != 0:
            return False

        # Check for regex pattern (heuristic: contains / before //)
        # This is not perfect but catches most cases
        if '/' in before_comment and not before_comment.strip().endswith('/'):
            # Might be a regex, be conservative
            return False

        return True

    def _remove_block_comments(self, content):
        """
        Remove block comments /* ... */ but preserve license headers

        Strategy:
        1. Find all /* ... */ blocks
        2. Check if they contain license/copyright info
        3. Remove non-license blocks
        """
        def replacer(match):
            comment_text = match.group(0)

            # Check if it's an important comment
            if self._is_important_comment(comment_text):
                return comment_text  # Preserve

            # Otherwise remove
            return ''

        # Match /* ... */ including multiline
        content = re.sub(r'/\*.*?\*/', replacer, content, flags=re.DOTALL)

        return content


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
