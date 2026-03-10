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
        // 1. Relative paths (./x, ../x) - resolve via referrer
        if (url.startsWith('./') || url.startsWith('../')) {
            const resolved = resolveRelativePath(url, referrer);
            if (resolved) return resolved;
        }

        const normalized = normalizeUrl(url, referrer);

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
            const urlObj = new URL(url, window.location.href);
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
            const urlObj = new URL(url, window.location.href);
            return urlObj.origin !== window.location.origin;
        } catch(e) {
            return false;
        }
    }

    // Intercept fetch()
    const originalFetch = window.fetch;
    window.fetch = function(url, options) {
        const referrer = (options && options.referrer) || document.currentScript?.src || window.location.href;
        const localPath = getLocalPath(url, referrer);

        if (localPath) {
            console.log('[Fetch Interceptor] \u2713', url, '->', localPath);
            return originalFetch(localPath, options);
        }

        // CRITICAL FIX: Block all external requests that have no local mapping
        // This prevents 406/CORS errors from leaking to real APIs (Supabase, etc)
        if (isExternal(url)) {
            console.warn('[Fetch Interceptor] \u2717 Blocked external leak:', url);

            // CRITICAL: Return empty array [] for REST GET endpoints to prevent React crashes
            // React expects arrays from API list endpoints - returning objects causes .map() errors
            const method = (options && options.method) || 'GET';
            let mockData = [];

            // If it looks like a REST API endpoint requesting a list, return empty array
            if (method.toUpperCase() === 'GET' && url.includes('/rest/')) {
                mockData = [];
            } else {
                // For other requests, fail silently with empty response
                mockData = null;
            }

            return Promise.resolve(new Response(JSON.stringify(mockData), {
                status: 200,
                statusText: 'OK (Mocked)',
                headers: { 'Content-Type': 'application/json' }
            }));
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
        if (this._interceptedUrl && !this._hasLocalMapping && isExternal(this._interceptedUrl)) {
            console.warn('[XHR Interceptor] \u2717 Blocked external leak:', this._interceptedUrl);

            // CRITICAL: Return empty array [] for REST API to prevent React crashes
            let mockResponse = '[]';
            if (this._interceptedUrl.includes('/rest/')) {
                mockResponse = '[]';
            }

            // Simulate successful response
            Object.defineProperty(this, 'status', { value: 200, writable: false });
            Object.defineProperty(this, 'statusText', { value: 'OK (Mocked)', writable: false });
            Object.defineProperty(this, 'responseText', {
                value: mockResponse,
                writable: false
            });
            Object.defineProperty(this, 'response', {
                value: mockResponse,
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
