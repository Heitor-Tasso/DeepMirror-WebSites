"""
CSS cleaning helpers.
"""
import re

try:
    import cssbeautifier
    _CSSBEAUTIFIER_AVAILABLE = True
except ImportError:
    _CSSBEAUTIFIER_AVAILABLE = False


def clean_css_content(content):
    """
    Clean CSS for AI readability:
    1. Desminify with cssbeautifier.
    2. Remove comments.
    3. Normalize blank lines.
    """
    if _CSSBEAUTIFIER_AVAILABLE:
        opts = cssbeautifier.default_options()
        opts.indent_size = 2
        opts.end_with_newline = True
        opts.newline_between_rules = True
        try:
            content = cssbeautifier.beautify(content, opts)
        except Exception:
            pass

    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)
    return content
