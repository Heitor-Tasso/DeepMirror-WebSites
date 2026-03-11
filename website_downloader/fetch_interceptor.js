/**
 * Fetch/XHR Interceptor - Injected into downloaded sites to resolve remote URLs locally.
 *
 * This script is loaded as a template. Python replaces the placeholder comment below
 * with the actual resource map code before injecting into the page <head>.
 *
 * Placeholder: /* __RESOURCE_MAP_CODE__ * /
 */
(async function() {
    /* __RESOURCE_MAP_CODE__ */

    // Index 1: local-path basename -> [localPaths]  (for relative imports like ./chunk.js)
    const basenameIndex = {};
    // Index 2: original-url basename -> [localPaths]  (for requests using original filename before hash suffix)
    const originalBasenameIndex = {};

    Object.entries(resourceMap).forEach(([originalUrl, localPath]) => {
        // Build local basename index
        if (localPath.startsWith('assets/')) {
            const localBasename = localPath.split('/').pop();
            if (!basenameIndex[localBasename]) basenameIndex[localBasename] = [];
            basenameIndex[localBasename].push(localPath);
        }
        // Build original URL basename index
        try {
            const origBasename = originalUrl.split('/').pop().split('?')[0];
            if (origBasename) {
                if (!originalBasenameIndex[origBasename]) originalBasenameIndex[origBasename] = [];
                originalBasenameIndex[origBasename].push(localPath);
            }
        } catch(e) {}
    });

    // Normalize any URL to absolute href
    function normalizeUrl(url, baseUrl) {
        if (!url) return url;
        if (typeof url === 'object' && url.url) url = url.url; // Request object
        if (url.startsWith('data:') || url.startsWith('blob:')) return url;
        try {
            return new URL(url, baseUrl || window.location.href).href;
        } catch(e) {
            return url;
        }
    }

    // Resolve relative paths (./chunk.js, ../utils.js) using referrer context
    function resolveRelativePath(url, referrer) {
        if (!url.startsWith('./') && !url.startsWith('../')) return null;
        try {
            const referrerUrl = new URL(referrer || window.location.href);
            const referrerDir = referrerUrl.pathname.substring(0, referrerUrl.pathname.lastIndexOf('/') + 1);
            const resolved = new URL(url, window.location.origin + referrerDir).pathname;
            const basename = resolved.split('/').pop();

            if (basenameIndex[basename]) {
                if (basenameIndex[basename].length === 1) return '/' + basenameIndex[basename][0];
                // Multiple matches: prefer same directory structure
                const referrerPath = referrer.replace(window.location.origin, '');
                for (const candidate of basenameIndex[basename]) {
                    if (referrerPath.includes('assets/') && candidate.includes(basename)) {
                        return '/' + candidate;
                    }
                }
                return '/' + basenameIndex[basename][0];
            }
            // Try original basename index too
            if (originalBasenameIndex[basename] && originalBasenameIndex[basename].length === 1) {
                return originalBasenameIndex[basename][0];
            }
        } catch(e) {
            console.warn('[Fetch Interceptor] Relative path resolution failed:', url, e);
        }
        return null;
    }

    // Main lookup: find local path for any URL
    function getLocalPath(url, referrer) {
        const rawUrl = typeof url === 'string'
            ? url
            : (url && typeof url === 'object' && url.url ? url.url : String(url || ''));

        // 1. Relative paths (./x, ../x) - resolve via referrer
        if (rawUrl.startsWith('./') || rawUrl.startsWith('../')) {
            const resolved = resolveRelativePath(rawUrl, referrer);
            if (resolved) return resolved;
        }

        const normalized = normalizeUrl(rawUrl, referrer);

        // 2. Exact match in resource map
        if (resourceMap[normalized]) return resourceMap[normalized];

        // 3. Protocol-relative variant (//domain.com/path)
        const withoutProtocol = normalized.replace(/^https?:/, '');
        if (resourceMap[withoutProtocol]) return resourceMap[withoutProtocol];

        // 4. Basename match against ORIGINAL URL basenames
        //    This handles cases where the saved file has a hash suffix appended:
        //    browser requests "chunk.js" but file was saved as "chunk_abc123.js"
        try {
            const basename = normalized.split('/').pop().split('?')[0];
            if (basename) {
                if (originalBasenameIndex[basename] && originalBasenameIndex[basename].length === 1) {
                    return originalBasenameIndex[basename][0];
                }
                // 5. Fallback: local path basename index
                if (basenameIndex[basename] && basenameIndex[basename].length === 1) {
                    return '/' + basenameIndex[basename][0];
                }
            }
        } catch(e) {}

        return null;
    }

    // Block requests to external CDNs that have no local copy
    function isExternalCDN(url) {
        try {
            const urlObj = new URL(normalizeUrl(url, window.location.href), window.location.href);
            if (urlObj.origin !== window.location.origin) {
                const hostname = urlObj.hostname.toLowerCase();
                const cdnMarkers = ['.b-cdn.', 'cdn.', '.cloudfront.', '.akamai', '.fastly.'];
                return cdnMarkers.some(marker => hostname.includes(marker));
            }
        } catch(e) {}
        return false;
    }

    // Check if URL is external (different origin)
    function isExternal(url) {
        try {
            const urlObj = new URL(normalizeUrl(url, window.location.href), window.location.href);
            return urlObj.origin !== window.location.origin;
        } catch(e) {
            return false;
        }
    }

    function isTrackingEndpoint(url) {
        try {
            const urlObj = new URL(normalizeUrl(url, window.location.href), window.location.href);
            const hostname = urlObj.hostname.toLowerCase();
            const path = (urlObj.pathname || '').toLowerCase();
            const combined = `${hostname}${path}`;
            const markers = [
                'monorail',
                'api/collect',
                '/collect',
                'web-pixels',
                'webpixels',
                'web-pixel',
                '/pixel',
                'pixel.',
                'shopifycloud/web-pixels-manager',
                'hotjar',
                'klaviyo',
                'cookiebot',
                'consentcdn',
            ];
            return markers.some(marker => combined.includes(marker));
        } catch(e) {
            return false;
        }
    }

    function buildMockResponse(url, method) {
        let mockData = {};
        if ((method || 'GET').toUpperCase() === 'GET' && String(url).includes('/rest/')) {
            mockData = [];
        }
        return new Response(JSON.stringify(mockData), {
            status: 200,
            statusText: 'OK (Mocked)',
            headers: { 'Content-Type': 'application/json' }
        });
    }

    function toComparableUrl(url) {
        if (!url) return '';
        try {
            return new URL(url, window.location.href).href;
        } catch (e) {
            return String(url);
        }
    }

    function comparableCandidates(urls) {
        const candidates = new Set();

        for (const url of urls) {
            if (!url) continue;
            const comparable = toComparableUrl(url);
            if (comparable) candidates.add(comparable);

            const localPath = getLocalPath(url, window.location.href);
            const comparableLocal = toComparableUrl(localPath);
            if (comparableLocal) candidates.add(comparableLocal);
        }

        candidates.delete('');
        return candidates;
    }

    function hasExistingAsset(tagName, attrName, urls) {
        const targetUrls = Array.isArray(urls) ? urls : [urls];
        const comparableTargets = comparableCandidates(targetUrls);
        if (!comparableTargets.size) return false;

        const elements = tagName === 'script'
            ? Array.from(document.scripts || [])
            : Array.from(document.querySelectorAll(tagName));

        return elements.some((element) => {
            const currentValue = element.getAttribute(attrName) || element[attrName] || '';
            if (!currentValue) return false;

            const currentComparable = toComparableUrl(currentValue);
            if (currentComparable && comparableTargets.has(currentComparable)) {
                return true;
            }

            const currentLocalPath = getLocalPath(currentValue, window.location.href);
            const currentComparableLocal = toComparableUrl(currentLocalPath);
            return currentComparableLocal && comparableTargets.has(currentComparableLocal);
        });
    }

    function neutralizeDuplicateNode(node, kind, url) {
        node.setAttribute('data-interceptor-duplicate', 'true');

        if (kind === 'script') {
            node.removeAttribute('src');
            node.type = 'application/json';
        } else if (kind === 'link') {
            node.removeAttribute('href');
            node.setAttribute('data-interceptor-disabled', 'true');
        }

        setTimeout(() => {
            const loadEvent = new Event('load');
            if (typeof node.onload === 'function') {
                try { node.onload(loadEvent); } catch (e) {}
            }
            try { node.dispatchEvent(loadEvent); } catch (e) {}
        }, 0);

        console.log('[DOM Interceptor] = Duplicate', kind, url);
        return node;
    }

    function rewriteDynamicElement(node) {
        if (!node || !node.tagName) return node;

        const tagName = node.tagName.toLowerCase();
        if (tagName === 'script') {
            const originalSrc = node.getAttribute('src') || node.src;
            if (!originalSrc) return node;

            const localPath = getLocalPath(originalSrc, window.location.href);
            const targetSrc = localPath || originalSrc;
            if (hasExistingAsset('script', 'src', [originalSrc, targetSrc])) {
                return neutralizeDuplicateNode(node, 'script', targetSrc);
            }

            if (localPath && localPath !== originalSrc) {
                node.setAttribute('src', localPath);
                console.log('[DOM Interceptor] \u2713 script', originalSrc, '->', localPath);
                return node;
            }

            if (isTrackingEndpoint(originalSrc) || (isExternal(originalSrc) && isExternalCDN(originalSrc))) {
                node.removeAttribute('src');
                node.type = 'application/json';
                console.warn('[DOM Interceptor] \u2717 Blocked dynamic script:', originalSrc);
            }
            return node;
        }

        if (tagName === 'link') {
            const rel = (node.getAttribute('rel') || '').toLowerCase();
            if (!rel || !['preload', 'prefetch', 'modulepreload', 'stylesheet'].some(value => rel.includes(value))) {
                return node;
            }

            const originalHref = node.getAttribute('href') || node.href;
            if (!originalHref) return node;

            const localPath = getLocalPath(originalHref, window.location.href);
            const targetHref = localPath || originalHref;
            if (hasExistingAsset('link', 'href', [originalHref, targetHref])) {
                return neutralizeDuplicateNode(node, 'link', targetHref);
            }

            if (localPath && localPath !== originalHref) {
                node.setAttribute('href', localPath);
                console.log('[DOM Interceptor] \u2713 link', originalHref, '->', localPath);
                return node;
            }
        }

        return node;
    }

    const originalAppendChild = Node.prototype.appendChild;
    Node.prototype.appendChild = function(node) {
        return originalAppendChild.call(this, rewriteDynamicElement(node));
    };

    const originalInsertBefore = Node.prototype.insertBefore;
    Node.prototype.insertBefore = function(node, referenceNode) {
        return originalInsertBefore.call(this, rewriteDynamicElement(node), referenceNode);
    };

    const originalReplaceChild = Node.prototype.replaceChild;
    Node.prototype.replaceChild = function(newChild, oldChild) {
        return originalReplaceChild.call(this, rewriteDynamicElement(newChild), oldChild);
    };

    // Intercept fetch()
    const originalFetch = window.fetch;
    window.fetch = function(url, options) {
        const referrer = (options && options.referrer) || document.currentScript?.src || window.location.href;
        const method = (options && options.method) || 'GET';
        const localPath = getLocalPath(url, referrer);

        if (localPath) {
            console.log('[Fetch Interceptor] \u2713', url, '->', localPath);
            return originalFetch(localPath, options);
        }

        if (isTrackingEndpoint(url)) {
            console.warn('[Fetch Interceptor] \u2717 Blocked tracking call:', url);
            return Promise.resolve(buildMockResponse(url, method));
        }

        // CRITICAL FIX: Block all external requests that have no local mapping
        // This prevents 406/CORS errors from leaking to real APIs (Supabase, etc)
        if (isExternal(url)) {
            console.warn('[Fetch Interceptor] \u2717 Blocked external leak:', url);
            return Promise.resolve(buildMockResponse(url, method));
        }

        return originalFetch(url, options);
    };

    // Intercept XMLHttpRequest
    const originalOpen = XMLHttpRequest.prototype.open;
    const originalSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function(method, url, ...args) {
        const referrer = document.currentScript?.src || window.location.href;
        const localPath = getLocalPath(url, referrer);

        // Store original URL for send() interception
        this._interceptedUrl = url;
        this._hasLocalMapping = !!localPath;

        if (localPath) {
            console.log('[XHR Interceptor] \u2713', url, '->', localPath);
            return originalOpen.call(this, method, localPath, ...args);
        }

        // CRITICAL FIX: Allow open() to proceed, but intercept send() for external URLs
        return originalOpen.call(this, method, url, ...args);
    };

    XMLHttpRequest.prototype.send = function(...args) {
        // If URL is external and has no local mapping, block and return mock
        if (this._interceptedUrl && !this._hasLocalMapping && (
            isTrackingEndpoint(this._interceptedUrl) || isExternal(this._interceptedUrl)
        )) {
            if (isTrackingEndpoint(this._interceptedUrl)) {
                console.warn('[XHR Interceptor] \u2717 Blocked tracking call:', this._interceptedUrl);
            } else {
                console.warn('[XHR Interceptor] \u2717 Blocked external leak:', this._interceptedUrl);
            }

            // Simulate successful response
            Object.defineProperty(this, 'status', { value: 200, writable: false });
            Object.defineProperty(this, 'statusText', { value: 'OK (Mocked)', writable: false });
            Object.defineProperty(this, 'responseText', {
                value: this._interceptedUrl.includes('/rest/') ? '[]' : '{}',
                writable: false
            });
            Object.defineProperty(this, 'response', {
                value: this._interceptedUrl.includes('/rest/') ? '[]' : '{}',
                writable: false
            });
            Object.defineProperty(this, 'readyState', { value: 4, writable: false });

            // Trigger load event asynchronously
            setTimeout(() => {
                if (this.onload) this.onload({ type: 'load', target: this });
                if (this.onreadystatechange) this.onreadystatechange({ type: 'readystatechange', target: this });
            }, 0);

            return;
        }

        return originalSend.apply(this, args);
    };

    console.log('[Fetch Interceptor] Installed with', Object.keys(resourceMap).length, 'mappings');
    console.log('[Fetch Interceptor] Basename index:', Object.keys(basenameIndex).length, 'files');
})();
