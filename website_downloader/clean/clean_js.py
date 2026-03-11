"""
JavaScript cleaning helpers.
"""
import re


_VENDOR_JS_PATTERNS = [
    'jquery', 'react', 'react-dom', 'vue', 'angular', 'gsap', 'three',
    'framer-motion', 'lottie', 'swiper', 'locomotive', 'lenis', 'split-type',
    'bootstrap', 'tailwind', 'normalize', 'modernizr', 'lodash', 'underscore',
    'moment', 'dayjs', 'axios', 'babel', 'polyfill', 'webpack', 'vite',
]


def clean_js_content(content, filename=''):
    """
    Clean JS conservatively for AI readability.
    """
    is_vendor = any(pattern in filename.lower() for pattern in _VENDOR_JS_PATTERNS)
    lines = content.split('\n')
    is_minified = len(lines) < 10 or (len(content) / max(len(lines), 1)) > 200

    if is_vendor or is_minified:
        content = _clean_minified_js(content)
    else:
        content = _clean_formatted_js(content)

    return re.sub(r'\n\s*\n\s*\n+', '\n\n', content)


def _clean_minified_js(content):
    for method in ('log', 'warn', 'error', 'info', 'debug'):
        content = re.sub(rf'console\.{method}\([^;]*?\);?', '', content)
    content = re.sub(r'\bdebugger\s*;?', '', content)
    return content


def _clean_formatted_js(content):
    lines = content.split('\n')
    cleaned = []

    for line in lines:
        if re.match(r'^\s*console\.(log|warn|error|info|debug)\s*\(', line):
            continue
        if re.match(r'^\s*debugger\s*;?\s*$', line):
            continue
        if re.match(r'^\s*//', line):
            if _is_important_comment(line):
                cleaned.append(line)
            continue
        cleaned.append(line)

    content = '\n'.join(cleaned)
    return _remove_block_comments(content)


def _is_important_comment(line):
    keywords = ['@license', 'copyright', '(c)', 'mit license', 'bsd license', 'apache', 'gpl']
    lower = line.lower()
    return any(keyword in lower for keyword in keywords)


def _remove_block_comments(content):
    def replacer(match):
        block = match.group(0)
        if _is_important_comment(block):
            return block
        return ''

    return re.sub(r'/\*.*?\*/', replacer, content, flags=re.DOTALL)
