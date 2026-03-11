"""
HTML cleaning helpers.
"""
import re

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False


_ANALYTICS_ATTRS = re.compile(
    r'''\s+(?:data-(?:test(?:-id)?|testid|cy|qa|gtm(?:-[^\s=]+)?|analytics(?:-[^\s=]+)?|tracking(?:-[^\s=]+)?|g-tag|g-tm|hs-[^\s=]+|heap-[^\s=]+|amplitude-[^\s=]+|segment-[^\s=]+|mixpanel-[^\s=]+|fb-[^\s=]+|pixel-[^\s=]+))=["\'][^"\']*["\']''',
    re.IGNORECASE,
)

_SVG_PATH_COMPLEXITY_THRESHOLD = 80


def clean_html_content(content):
    """
    Clean HTML for AI readability:
    1. Remove HTML comments (preserve IE conditionals).
    2. Remove analytics/tracking data attributes.
    3. Simplify complex inline SVG path data.
    4. Normalize excessive blank lines.
    """
    content = re.sub(r'<!--(?!\[if).*?-->', '', content, flags=re.DOTALL)
    content = _ANALYTICS_ATTRS.sub('', content)

    if _BS4_AVAILABLE:
        content = simplify_svg_paths(content)

    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    return content


def simplify_svg_paths(html_content):
    """
    Replace complex SVG path data with a readable placeholder.
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        modified = False

        for path in soup.find_all('path', d=True):
            if len(path.get('d', '')) > _SVG_PATH_COMPLEXITY_THRESHOLD:
                path['d'] = '[complex-path]'
                modified = True

        if modified:
            return str(soup)
    except Exception:
        pass

    return html_content
