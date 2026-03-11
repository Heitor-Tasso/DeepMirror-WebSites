"""
Post-Processing - HTML/DOM transformations via BeautifulSoup.
File-based URL rewriting is handled by url_rewrite.URLRewriter.
"""
import os
import re
import json
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup, NavigableString
from . import TRACKING_SCRIPTS, RESOURCE_TIMEOUT
from .url_rewrite import URLRewriter, rewrite_css_urls


class PostProcessor:
    def __init__(self, base_url, output_dir, log_callback, network_recorder):
        self.base_url = base_url
        self.output_dir = output_dir
        self.log = log_callback
        self.network = network_recorder
        self.rewriter = URLRewriter(base_url, output_dir, log_callback, network_recorder)
        self._original_script_urls = None
        self._original_html_soup = None

        # Path to the JS interceptor template
        self._interceptor_js_path = os.path.join(
            os.path.dirname(__file__), 'fetch_interceptor.js'
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Public entry point
    # ─────────────────────────────────────────────────────────────────────────

    def process_html(self, html_content):
        """Apply all HTML transformations and trigger file-based rewriting."""
        self.log("🔧 Processando HTML e assets...")
        baseline_html = self._select_document_baseline(html_content)
        soup = BeautifulSoup(baseline_html, 'html.parser')
        is_ssr_framework = self._is_ssr_framework(soup)

        # DOM-level transformations
        self._cleanup_runtime_dom_state(soup)
        if is_ssr_framework:
            if self._should_prune_runtime_nodes(soup):
                self._prune_runtime_only_nodes(soup)
            self._restore_empty_runtime_hosts(soup)
        self._restore_missing_original_support_nodes(soup)
        self._restore_original_form_controls(soup)
        self._restore_original_inline_styles(soup)
        self._restore_original_svg_transforms(soup)
        self._restore_original_style_tags(soup)
        self._remove_canvas_snapshots(soup)
        self._fix_scroll_blocking(soup)
        self._remove_wrapper_iframes(soup)
        self._process_stylesheets(soup)
        self._process_inline_styles(soup)
        self._process_scripts(soup)
        self._process_images(soup)
        self._process_inline_style_attrs(soup)
        self._process_favicons(soup)
        self._process_meta_images(soup)
        self._process_background_attrs(soup)
        self._fix_navigation_links(soup)
        self._handle_spa_frameworks(soup)
        self._remove_preconnects(soup)
        self._process_preloads(soup)
        self._inject_external_preload_bootstrap(soup)
        self._remove_tracking_scripts(soup)
        self._remove_tracking_widgets(soup)
        self._inject_import_map(soup)
        self._inject_shopify_bootstrap(soup)

        # Inject fetch interceptor before serializing
        self._inject_fetch_interceptor(soup)

        html_output = str(soup)

        # File-based operations (safe — work on saved files, not the HTML string)
        self.rewriter.rewrite_css_files()
        self.rewriter.process_json_files()
        self.rewriter.remove_sourcemaps()

        # String-level HTML post-processing
        html_output = self.rewriter.rewrite_basenames_in_html(html_output)
        html_output = self.rewriter.rewrite_nextjs_images_in_html(html_output)

        return html_output

    def save_html(self, html_output):
        """Save final HTML to disk."""
        with open(os.path.join(self.output_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html_output)

    def _body_has_meaningful_ssr_content(self, soup):
        """Heuristic to detect whether the original HTML already contains useful body markup."""
        body = soup.find('body')
        if not body:
            return False

        element_children = [child for child in body.children if getattr(child, 'name', None)]
        if len(element_children) >= 3:
            return True

        text_content = ' '.join(body.stripped_strings)
        return len(text_content) >= 200

    def _select_document_baseline(self, html_content):
        """
        Choose the safest HTML baseline for post-processing.

        For SSR frameworks, page.content() can capture a heavily mutated runtime
        DOM that no longer matches the server response expected by hydration.
        In those cases prefer the original HTML captured from the network.
        """
        original_html = self.network.get_document_html(self.base_url)
        if not original_html or original_html == html_content:
            return html_content

        original_soup = BeautifulSoup(original_html, 'html.parser')
        is_ssr_framework = any([
            original_soup.find(id='__next') is not None,
            original_soup.find(id='__nuxt') is not None,
            original_soup.find(id='___gatsby') is not None,
            'self.__next_f.push' in original_html,
            '__NEXT_DATA__' in original_html,
        ])

        if not is_ssr_framework:
            return html_content

        if not self._body_has_meaningful_ssr_content(original_soup):
            return html_content

        self.log("   Usando HTML original da resposta como baseline do documento")
        return original_html

    def _get_original_script_urls(self):
        """Return the external script URLs present in the original HTML response."""
        original_soup = self._get_original_html_soup()
        if not original_soup:
            self._original_script_urls = None
            return None

        if self._original_script_urls is not None:
            return self._original_script_urls

        self._original_script_urls = {
            urljoin(self.base_url, script.get('src'))
            for script in original_soup.find_all('script', src=True)
            if script.get('src')
        }
        return self._original_script_urls

    def _get_original_html_soup(self):
        """Return the original HTML response parsed as BeautifulSoup."""
        if self._original_html_soup is not None:
            return self._original_html_soup

        original_html = self.network.get_document_html(self.base_url)
        if not original_html:
            return None

        self._original_html_soup = BeautifulSoup(original_html, 'html.parser')
        return self._original_html_soup

    # ─────────────────────────────────────────────────────────────────────────
    # DOM transformations
    # ─────────────────────────────────────────────────────────────────────────

    def _remove_canvas_snapshots(self, soup):
        """Remove Playwright-captured canvas elements (width + height + data-engine)."""
        removed = 0
        for canvas in soup.find_all('canvas'):
            if canvas.has_attr('width') and canvas.has_attr('height') and canvas.has_attr('data-engine'):
                self.log(f"   Removendo canvas renderizado: {canvas.get('width')}x{canvas.get('height')}")
                canvas.decompose()
                removed += 1
        if removed:
            self.log(f"   Removidos {removed} canvas renderizados (Playwright snapshots)")

    def _cleanup_runtime_dom_state(self, soup):
        """
        Remove transient runtime flags/styles saved by page.content().

        These markers are useful while the live page is running, but persisting
        them into the offline HTML can block re-initialization on the next load.
        """
        initialized_attrs_removed = 0
        animation_play_state_removed = 0
        transform_style_resets = 0
        playwright_attrs_removed = 0

        transient_style_props = {'translate', 'rotate', 'scale', 'transform-origin'}
        transient_class_markers = {
            'klaviyo',
            'needsclick',
            'kl-private-reset-css',
            'cookiebot',
            'cybotcookiebotdialog',
            'web-pixels',
            'web-pixel',
            'shopify-privacy',
        }

        for element in soup.find_all(True):
            if not isinstance(getattr(element, 'attrs', None), dict):
                continue

            for attr in list(element.attrs.keys()):
                if attr.endswith('-initialized'):
                    del element[attr]
                    initialized_attrs_removed += 1
                    continue
                if attr.startswith('data-playwright'):
                    del element[attr]
                    playwright_attrs_removed += 1

            classes = element.get('class', [])
            if isinstance(classes, str):
                classes = classes.split()
            if classes:
                filtered_classes = [
                    cls for cls in classes
                    if not any(marker in cls.lower() for marker in transient_class_markers)
                ]
                if filtered_classes != classes:
                    element['class'] = filtered_classes

            style = element.get('style')
            if not style:
                continue

            declarations = []
            for raw_decl in style.split(';'):
                if ':' not in raw_decl:
                    continue
                key, value = raw_decl.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                if not key:
                    continue
                declarations.append((key, value))

            if not declarations:
                continue

            kept = [(key, value) for key, value in declarations if key != 'animation-play-state']
            if len(kept) != len(declarations):
                animation_play_state_removed += 1

            # GSAP often leaves transform bookkeeping inline after the initial
            # run. If those are the only persisted styles, drop them so the next
            # runtime can compute its own clean baseline.
            if kept and all(key in transient_style_props for key, _ in kept):
                element.attrs.pop('style', None)
                transform_style_resets += 1
                continue

            if kept:
                element['style'] = '; '.join(f"{key}: {value}" for key, value in kept) + ';'
            else:
                element.attrs.pop('style', None)

        if initialized_attrs_removed:
            self.log(f"   Removidos {initialized_attrs_removed} flags de inicialização em runtime")
        if playwright_attrs_removed:
            self.log(f"   Removidos {playwright_attrs_removed} atributos temporários do Playwright")
        if animation_play_state_removed:
            self.log(f"   Limpos {animation_play_state_removed} estados transitórios de animation-play-state")
        if transform_style_resets:
            self.log(f"   Limpos {transform_style_resets} estilos transitórios de transform do runtime")

    def _restore_empty_runtime_hosts(self, soup):
        """
        Reset server-empty runtime hosts back to their original empty state.

        Scene mounts and canvas containers often start empty in the server HTML
        and are populated only after client boot. Persisting those runtime
        children offline can freeze scene re-initialization on the next load.
        """
        original_soup = self._get_original_html_soup()
        if not original_soup:
            return

        path_lookup, signature_lookup = self._build_original_element_lookups(original_soup)

        cleared = 0

        for current_elem in list(soup.find_all(True)):
            if current_elem.parent is None:
                continue
            if not isinstance(getattr(current_elem, 'attrs', None), dict):
                continue

            original_elem = self._match_original_element(current_elem, path_lookup, signature_lookup)
            if not original_elem:
                continue

            original_children = [child for child in original_elem.children if getattr(child, 'name', None)]
            if original_children:
                continue

            current_children = [child for child in current_elem.children if getattr(child, 'name', None)]
            if not current_children:
                continue

            removable_children = []
            for child in current_children:
                if child.name == 'canvas':
                    removable_children.append(child)
                    continue
                if child.has_attr('data-scene-id') or child.find('canvas'):
                    removable_children.append(child)

            if len(removable_children) != len(current_children):
                continue

            for child in list(current_children):
                child.decompose()
                cleared += 1

        if cleared:
            self.log(f"   Restaurados {cleared} hosts vazios do HTML original para reinicialização em runtime")

    def _is_support_source_node(self, element):
        """Heuristic for original HTML nodes that act as data sources for client boot."""
        if element is None or not isinstance(getattr(element, 'attrs', None), dict):
            return False

        if element.name in {'script', 'style', 'link', 'meta', 'noscript'}:
            return False

        classes = set(self._normalized_classes(element))
        if classes.intersection({'w-dyn-list', 'w-dyn-item'}):
            return True

        descendant_count = len(element.find_all(True))
        text_length = len(' '.join(element.stripped_strings))
        support_markers = {
            'button',
            'list',
            'filter',
            'menu',
            'control',
            'instruction',
            'wrapper',
            'source',
            'template',
        }
        element_id = str(element.get('id') or '').lower()
        if element_id and descendant_count <= 25 and text_length <= 160:
            if any(marker in element_id for marker in support_markers):
                return True

        if classes and descendant_count <= 25 and text_length <= 160:
            if any(any(marker in cls.lower() for marker in support_markers) for cls in classes):
                return True

        for attr in element.attrs:
            if attr.startswith('data-'):
                return True

        if element.find(attrs=lambda attrs: attrs and any(key.startswith('data-') for key in attrs)):
            return True

        if element.find(class_='w-dyn-item') or element.find(class_='w-dyn-list'):
            return True

        return False

    def _restore_missing_original_support_nodes(self, soup):
        """
        Restore original source nodes that page.content() may lose after client boot.

        Some sites consume hidden CMS lists/templates during startup and remove them
        from the live DOM. Persisting only the mutated runtime DOM makes the next
        offline boot fail because the source nodes are no longer present.
        """
        original_soup = self._get_original_html_soup()
        if not original_soup:
            return

        current_body = soup.find('body')
        original_body = original_soup.find('body')
        if not current_body or not original_body:
            return

        _, original_signature_lookup = self._build_original_element_lookups(original_soup)
        current_path_lookup, current_signature_lookup = self._build_original_element_lookups(soup)
        restored = 0

        for original_elem in original_body.find_all(True):
            signature = self._element_identity_signature(original_elem)
            if not signature:
                continue
            if signature[0] == 'class' and len(original_signature_lookup.get(signature, [])) != 1:
                continue
            if self._match_original_element(original_elem, current_path_lookup, current_signature_lookup):
                continue
            if not self._is_support_source_node(original_elem):
                continue

            clone_soup = BeautifulSoup(str(original_elem), 'html.parser')
            clone = clone_soup.find(True)
            if clone is None:
                continue

            original_parent = original_elem.parent if getattr(original_elem.parent, 'name', None) else None
            target_parent = current_body
            if original_parent is not None:
                matched_parent = self._match_original_element(
                    original_parent,
                    current_path_lookup,
                    current_signature_lookup,
                )
                if matched_parent is not None:
                    target_parent = matched_parent

            target_parent.append(clone)
            restored += 1

        if restored:
            self.log(f"   Restaurados {restored} nós-fonte do HTML original consumidos pelo runtime")

    def _looks_runtime_enhanced_form_control(self, original_elem, current_elem):
        """Detect form controls replaced by client-side UI wrappers in the live DOM."""
        if original_elem is None or current_elem is None:
            return False

        if original_elem.name not in {'select', 'input', 'textarea'}:
            return False

        if current_elem.name != original_elem.name:
            return False

        original_hidden = original_elem.has_attr('hidden') or original_elem.get('type') == 'hidden'
        current_hidden = current_elem.has_attr('hidden') or current_elem.get('type') == 'hidden'
        if current_hidden and not original_hidden:
            return True

        if current_elem.has_attr('data-choice') and not original_elem.has_attr('data-choice'):
            return True

        if current_elem.get('tabindex') == '-1' and original_elem.get('tabindex') != '-1':
            return True

        for ancestor in current_elem.parents:
            if not getattr(ancestor, 'name', None) or ancestor.name in {'form', 'body', 'html'}:
                break

            role = str(ancestor.get('role') or '').lower()
            classes = set(self._normalized_classes(ancestor))
            if role in {'listbox', 'combobox'}:
                return True
            if ancestor.get('aria-expanded') is not None and current_hidden:
                return True
            if 'choices' in classes or any(cls.startswith('choices__') for cls in classes):
                return True

        return False

    def _find_runtime_form_wrapper(self, current_elem):
        """Pick the outermost transient wrapper around a runtime-enhanced form control."""
        target = current_elem
        for ancestor in current_elem.parents:
            if not getattr(ancestor, 'name', None) or ancestor.name in {'form', 'body', 'html'}:
                break

            role = str(ancestor.get('role') or '').lower()
            classes = set(self._normalized_classes(ancestor))
            if role in {'listbox', 'combobox'}:
                target = ancestor
                continue
            if ancestor.get('aria-expanded') is not None and current_elem.has_attr('hidden'):
                target = ancestor
                continue
            if 'choices' in classes or any(cls.startswith('choices__') for cls in classes):
                target = ancestor

        return target

    def _match_current_form_control(self, original_elem, current_body, path_lookup, signature_lookup):
        """Match original form controls even when runtime enhancers change classes/parents."""
        matched = self._match_original_element(original_elem, path_lookup, signature_lookup)
        if matched is not None:
            return matched

        stable_data_attrs = {
            attr for attr in original_elem.attrs
            if attr.startswith('data-') and attr not in {'data-choice', 'data-item', 'data-id', 'data-value'}
        }
        if stable_data_attrs:
            candidates = []
            for candidate in current_body.find_all(original_elem.name):
                candidate_data_attrs = {
                    attr for attr in candidate.attrs
                    if attr.startswith('data-') and attr not in {'data-choice', 'data-item', 'data-id', 'data-value'}
                }
                if stable_data_attrs.issubset(candidate_data_attrs):
                    candidates.append(candidate)
            if len(candidates) == 1:
                return candidates[0]

        if original_elem.name == 'select':
            original_options = [
                (option.get('value', ''), option.get_text(' ', strip=True))
                for option in original_elem.find_all('option')
            ]
            candidates = []
            for candidate in current_body.find_all('select'):
                candidate_options = [
                    (option.get('value', ''), option.get_text(' ', strip=True))
                    for option in candidate.find_all('option')
                ]
                if candidate_options == original_options:
                    candidates.append(candidate)
            if len(candidates) == 1:
                return candidates[0]

        return None

    def _restore_original_form_controls(self, soup):
        """
        Restore original form controls when runtime UI libraries replace them in-place.

        Libraries that enhance <select>/<input> often hide the original control and
        inject interactive wrappers. Persisting that mutated DOM causes duplicate
        initialization offline because the library boots again on top of an already
        enhanced control.
        """
        original_soup = self._get_original_html_soup()
        if not original_soup:
            return

        original_body = original_soup.find('body')
        current_body = soup.find('body')
        if not original_body or not current_body:
            return

        restored = 0
        while True:
            current_path_lookup, current_signature_lookup = self._build_original_element_lookups(soup)
            changed = False

            for original_elem in original_body.find_all(['select', 'input', 'textarea']):
                current_elem = self._match_current_form_control(
                    original_elem,
                    current_body,
                    current_path_lookup,
                    current_signature_lookup,
                )
                if current_elem is None:
                    continue
                if not self._looks_runtime_enhanced_form_control(original_elem, current_elem):
                    continue

                clone_soup = BeautifulSoup(str(original_elem), 'html.parser')
                clone = clone_soup.find(original_elem.name)
                if clone is None:
                    continue

                replacement_target = self._find_runtime_form_wrapper(current_elem)
                replacement_target.replace_with(clone)
                restored += 1
                changed = True
                break

            if not changed:
                break

        if restored:
            self.log(f"   Restaurados {restored} controles de formulário ao estado original")

    def _normalized_classes(self, element):
        """Return a normalized list of CSS classes for element matching."""
        if element is None or not isinstance(getattr(element, 'attrs', None), dict):
            return []
        classes = element.get('class', [])
        if isinstance(classes, str):
            classes = classes.split()
        return [cls for cls in classes if cls]

    def _elements_equivalent(self, current_elem, original_elem):
        """Heuristic element matcher that tolerates extra runtime siblings."""
        if current_elem.name != original_elem.name:
            return False

        current_id = current_elem.get('id')
        original_id = original_elem.get('id')
        if current_id or original_id:
            return current_id == original_id

        current_classes = tuple(self._normalized_classes(current_elem))
        original_classes = tuple(self._normalized_classes(original_elem))
        if current_classes or original_classes:
            return current_classes == original_classes

        for attr in ('role', 'aria-label', 'name', 'type'):
            current_value = current_elem.get(attr)
            original_value = original_elem.get(attr)
            if current_value or original_value:
                return current_value == original_value

        return True

    def _is_probable_runtime_only_node(self, element):
        """Heuristic for nodes injected by client runtime after the server HTML."""
        for attr in element.attrs:
            if attr.startswith('data-playwright'):
                return True
            if attr in {
                'data-scene-id',
                'data-lenis-prevent',
                'data-lenis-prevent-touch',
                'data-lenis-prevent-wheel',
            }:
                return True

        classes = set(self._normalized_classes(element))
        if classes.intersection({'word', 'char', 'line'}):
            return True

        marker_values = []
        for attr_name, attr_value in element.attrs.items():
            if isinstance(attr_value, list):
                marker_values.extend(str(item).lower() for item in attr_value)
            else:
                marker_values.append(str(attr_value).lower())

        vendor_markers = {
            'klaviyo',
            'kl-private-reset-css',
            'cookiebot',
            'cybotcookiebotdialog',
            'web-pixels',
            'web-pixel',
            'shopify-privacy',
            'hotjar',
            'intercom',
            'drift',
            'crisp',
            'zendesk',
            'tawk',
            'livechat',
            'freshchat',
        }
        if any(marker in value for value in marker_values for marker in vendor_markers):
            return True

        return False

    def _prune_runtime_only_nodes(self, soup):
        """
        Remove DOM nodes added only after client boot.

        page.content() captures the hydrated DOM, which may include overlays,
        split-text wrappers, cookie banners and modal trees that were not part
        of the server HTML. Keeping those nodes can freeze client runtimes on
        the offline replay because the app hydrates against an already-mutated
        structure instead of the original baseline.
        """
        original_soup = self._get_original_html_soup()
        if not original_soup:
            return

        current_body = soup.find('body')
        original_body = original_soup.find('body')
        if not current_body or not original_body:
            return

        removed = self._prune_runtime_only_descendants(current_body, original_body)
        if removed:
            self.log(f"   Removidos {removed} nós gerados apenas em runtime")

    def _should_prune_runtime_nodes(self, soup, max_elements=1800):
        """
        Skip recursive runtime-node pruning on very large SSR DOMs.

        The recursive matcher is useful on moderate trees, but on heavily
        hydrated documents it can dominate post-processing time. In those
        cases we keep the cheaper SSR restorations (empty hosts, inline styles,
        style tags) and let targeted tracking/widget removal handle overlays.
        """
        original_soup = self._get_original_html_soup()
        if not original_soup:
            return False

        current_body = soup.find('body')
        original_body = original_soup.find('body')
        if not current_body or not original_body:
            return False

        current_count = len(current_body.find_all(True))
        original_count = len(original_body.find_all(True))
        if max(current_count, original_count) > max_elements:
            self.log(
                f"   Pulando poda recursiva de nós runtime-only em DOM grande "
                f"({current_count}/{original_count} elementos)"
            )
            return False

        return True

    def _prune_runtime_only_descendants(self, current_parent, original_parent):
        """Recursively remove extra runtime-only children while preserving originals."""
        removed = 0

        current_children = [child for child in current_parent.children if getattr(child, 'name', None)]
        original_children = [child for child in original_parent.children if getattr(child, 'name', None)]

        current_index = 0
        original_index = 0

        while current_index < len(current_children):
            current_child = current_children[current_index]
            original_child = original_children[original_index] if original_index < len(original_children) else None

            if original_child and self._elements_equivalent(current_child, original_child):
                removed += self._prune_runtime_only_descendants(current_child, original_child)
                current_index += 1
                original_index += 1
                continue

            if self._is_probable_runtime_only_node(current_child):
                current_child.decompose()
                removed += 1
                current_children = [child for child in current_parent.children if getattr(child, 'name', None)]
                continue

            match_index = None
            if original_child is not None:
                for probe_index in range(current_index + 1, min(current_index + 5, len(current_children))):
                    if self._elements_equivalent(current_children[probe_index], original_child):
                        match_index = probe_index
                        break

            if match_index is not None:
                extra_children = current_children[current_index:match_index]
                for extra_child in extra_children:
                    if extra_child.parent and self._is_probable_runtime_only_node(extra_child):
                        extra_child.decompose()
                        removed += 1
                current_children = [child for child in current_parent.children if getattr(child, 'name', None)]
                continue

            if original_child is not None and current_child.name == original_child.name:
                removed += self._prune_runtime_only_descendants(current_child, original_child)
                current_index += 1
                original_index += 1
                continue

            current_index += 1

        return removed

    def _element_dom_path(self, element):
        """Build a stable nth-of-type DOM path for matching original/current nodes."""
        parts = []
        current = element

        while current and getattr(current, 'name', None):
            parent = getattr(current, 'parent', None)
            index = 1

            if parent and getattr(parent, 'children', None):
                for sibling in parent.children:
                    if getattr(sibling, 'name', None) != current.name:
                        continue
                    if sibling is current:
                        break
                    index += 1

            parts.append(f"{current.name}:{index}")
            current = parent if getattr(parent, 'name', None) else None

        return tuple(reversed(parts))

    def _element_identity_signature(self, element):
        """Return a stable identity signature for fallback original/current matching."""
        if element is None or not isinstance(getattr(element, 'attrs', None), dict):
            return None

        element_id = element.get('id')
        if element_id:
            return ('id', element.name, element_id)

        classes = tuple(self._normalized_classes(element))
        if classes:
            return ('class', element.name, classes)

        name_attr = element.get('name')
        if name_attr:
            return ('name', element.name, name_attr)

        return None

    def _build_original_element_lookups(self, original_soup):
        """Build path and signature lookups for the original HTML."""
        path_lookup = {}
        signature_lookup = {}

        for original_elem in original_soup.find_all(True):
            path_lookup[self._element_dom_path(original_elem)] = original_elem
            signature = self._element_identity_signature(original_elem)
            if signature:
                signature_lookup.setdefault(signature, []).append(original_elem)

        return path_lookup, signature_lookup

    def _match_original_element(self, current_elem, path_lookup, signature_lookup):
        """Match a current DOM node back to the original HTML."""
        if current_elem is None or current_elem.parent is None:
            return None
        if not isinstance(getattr(current_elem, 'attrs', None), dict):
            return None

        original_elem = path_lookup.get(self._element_dom_path(current_elem))
        if original_elem:
            return original_elem

        signature = self._element_identity_signature(current_elem)
        if not signature:
            return None

        candidates = signature_lookup.get(signature, [])
        if len(candidates) == 1:
            return candidates[0]

        return None

    def _normalize_inline_style(self, style):
        """Return a normalized representation of an inline style string."""
        if not style:
            return ()

        declarations = []
        for raw_decl in style.split(';'):
            if ':' not in raw_decl:
                continue
            key, value = raw_decl.split(':', 1)
            key = key.strip().lower()
            value = ' '.join(value.strip().split())
            if key:
                declarations.append((key, value))

        return tuple(declarations)

    def _restore_original_inline_styles(self, soup):
        """
        Restore inline style attributes to the original server-rendered HTML.

        Runtime animation libraries frequently persist transform/opacity/clip-path
        states into the captured DOM. Replaying those mutated inline styles
        offline can freeze entrances, scroll reveals and embedded widgets.
        """
        original_soup = self._get_original_html_soup()
        if not original_soup:
            return

        path_lookup, signature_lookup = self._build_original_element_lookups(original_soup)

        removed = 0
        restored = 0

        for current_elem in soup.find_all(True):
            original_elem = self._match_original_element(current_elem, path_lookup, signature_lookup)
            if not original_elem:
                continue

            current_style = current_elem.get('style')
            original_style = original_elem.get('style')

            if self._normalize_inline_style(current_style) == self._normalize_inline_style(original_style):
                continue

            if original_style is None:
                if current_style is not None:
                    del current_elem['style']
                    removed += 1
                continue

            current_elem['style'] = original_style
            restored += 1

        if removed:
            self.log(f"   Removidos {removed} estilos inline gerados apenas em runtime")
        if restored:
            self.log(f"   Restaurados {restored} estilos inline do HTML original")

    def _restore_original_svg_transforms(self, soup):
        """
        Restore SVG transform attributes to their original server-rendered state.

        Runtime animation libraries often persist matrix transforms into the DOM.
        If those transforms did not exist in the original HTML response, the next
        offline load starts from an already-mutated SVG state and animations drift.
        """
        original_soup = self._get_original_html_soup()
        if not original_soup:
            return

        original_lookup = {}
        for original_elem in original_soup.find_all(True):
            if original_elem.name != 'svg' and not original_elem.find_parent('svg'):
                continue
            original_lookup[self._element_dom_path(original_elem)] = original_elem

        restored = 0
        for current_elem in soup.find_all(True):
            if not current_elem.has_attr('transform'):
                continue
            if current_elem.name != 'svg' and not current_elem.find_parent('svg'):
                continue

            original_elem = original_lookup.get(self._element_dom_path(current_elem))
            if not original_elem:
                continue

            original_transform = original_elem.get('transform')
            current_transform = current_elem.get('transform')
            if original_transform == current_transform:
                continue

            if original_transform is None:
                del current_elem['transform']
            else:
                current_elem['transform'] = original_transform
            restored += 1

        if restored:
            self.log(f"   Restaurados {restored} transforms SVG do HTML original")

    def _restore_original_style_tags(self, soup):
        """
        Restore critical inline <style> tags from the original HTML response.

        CSS-in-JS libraries may leave placeholder tags in the hydrated DOM while
        the real server-rendered CSS still exists in the original HTML response.
        """
        original_soup = self._get_original_html_soup()
        if not original_soup:
            return

        head = soup.find('head')
        original_head = original_soup.find('head')
        if not head or not original_head:
            return

        restored = 0
        deduplicated = 0
        current_styles = head.find_all('style')

        def _style_signature(tag):
            return tuple(sorted((key, str(value)) for key, value in tag.attrs.items()))

        def _css_in_js_key(tag):
            if tag.has_attr('data-styled-version'):
                return ('styled-components', str(tag.get('data-styled-version')))
            if tag.has_attr('data-emotion'):
                return ('emotion', str(tag.get('data-emotion')))
            return None

        current_by_sig = {}
        current_by_css_in_js = {}
        for style_tag in current_styles:
            current_by_sig.setdefault(_style_signature(style_tag), []).append(style_tag)
            css_in_js_key = _css_in_js_key(style_tag)
            if css_in_js_key:
                current_by_css_in_js.setdefault(css_in_js_key, []).append(style_tag)

        for original_style in original_head.find_all('style'):
            original_css = original_style.get_text() or ''
            if not original_css.strip():
                continue

            signature = _style_signature(original_style)
            candidates = current_by_sig.get(signature, [])
            replaced = False

            for candidate in candidates:
                candidate_css = candidate.get_text() or ''
                if candidate_css.strip():
                    replaced = True
                    break
                candidate.clear()
                candidate.append(NavigableString(original_css))
                restored += 1
                replaced = True
                break

            if not replaced:
                css_in_js_key = _css_in_js_key(original_style)
                if css_in_js_key:
                    candidates = current_by_css_in_js.get(css_in_js_key, [])
                    if any((candidate.get_text() or '').strip() for candidate in candidates):
                        replaced = True
                    else:
                        placeholder = next(
                            (
                                candidate for candidate in candidates
                                if not (candidate.get_text() or '').strip()
                            ),
                            None,
                        )
                        if placeholder:
                            placeholder.attrs = dict(original_style.attrs)
                            placeholder.clear()
                            placeholder.append(NavigableString(original_css))
                            restored += 1
                            replaced = True

                            for candidate in candidates:
                                if candidate is placeholder:
                                    continue
                                if not (candidate.get_text() or '').strip():
                                    candidate.decompose()
                                    deduplicated += 1

            if replaced:
                continue

            new_style = soup.new_tag('style')
            for key, value in original_style.attrs.items():
                new_style[key] = value
            new_style.append(NavigableString(original_css))
            head.append(new_style)
            restored += 1

        if restored:
            self.log(f"   Restaurados {restored} blocos <style> críticos do HTML original")
        if deduplicated:
            self.log(f"   Removidos {deduplicated} placeholders duplicados de CSS-in-JS")

    def _fix_scroll_blocking(self, soup):
        """Remove scroll-blocking classes/attrs and inject minimal scroll-fix CSS."""
        self.log("🔧 Corrigindo problemas de scroll para visualização offline...")

        html_elem = soup.find('html')
        if html_elem:
            classes = html_elem.get('class', [])
            if isinstance(classes, str):
                classes = classes.split()
            blocking = {'overflow-hidden', 'no-scroll', 'scroll-lock', 'fixed', 'modal-open'}
            new_cls = [c for c in classes if c.lower() not in blocking]
            if new_cls != classes:
                html_elem['class'] = new_cls

        body = soup.find('body')
        if body:
            classes = body.get('class', [])
            if isinstance(classes, str):
                classes = classes.split()
            blocking = {'overflow-hidden', 'no-scroll', 'scroll-lock', 'fixed', 'modal-open'}
            new_cls = [c for c in classes if c.lower() not in blocking]
            if 'items-center' in new_cls and 'flex' in new_cls:
                new_cls = ['items-start' if c == 'items-center' else c for c in new_cls]
                self.log("   Corrigida centralização vertical do body")
            if new_cls != classes:
                body['class'] = new_cls

        scroll_fix_css = """
        /* Scroll fixes - MINIMAL SCOPE */
        html, body {
            overflow: auto !important;
            overflow-x: hidden !important;
            height: auto !important;
            min-height: 100% !important;
            scroll-behavior: auto !important;
        }
        .loader, .preloader, .loading, [class*="loader"], [class*="preloader"] {
            display: none !important;
            opacity: 0 !important;
        }
        """

        head = soup.find('head')
        if head:
            fix_style = soup.new_tag('style')
            fix_style['data-scroll-fix'] = 'true'
            fix_style.string = scroll_fix_css
            head.append(fix_style)
            self.log("   Injetado CSS para corrigir scroll")

        # Preserve scroll libraries and let the runtime initialize normally.
        # The minimal CSS override above is enough to prevent hard scroll locks
        # without breaking controllers such as Lenis/Locomotive.

    def _remove_wrapper_iframes(self, soup):
        """Remove preview/wrapper iframes from site builders."""
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '') or ''
            srcdoc = iframe.get('srcdoc', '')
            if srcdoc or 'preview' in str(iframe.get('class', '')).lower():
                iframe.decompose()

    def _prefer_original_root_path(self, original_url, local_path):
        """
        Keep exact same-origin root paths when the saved asset preserved structure.

        This preserves framework runtime semantics such as Next.js assetPrefix
        detection from `document.currentScript.src`, while the local server can
        still resolve `/path` to `assets/path` transparently.
        """
        if not original_url or not local_path or not local_path.startswith('assets/'):
            return local_path

        absolute_url = urljoin(self.base_url, original_url)
        parsed_original = urlparse(absolute_url)
        parsed_base = urlparse(self.base_url)

        if parsed_original.scheme not in {'http', 'https'}:
            return local_path
        if parsed_original.netloc != parsed_base.netloc:
            return local_path
        if parsed_original.query or not parsed_original.path.startswith('/'):
            return local_path

        expected_local = f"assets/{parsed_original.path.lstrip('/')}"
        if local_path == expected_local:
            return parsed_original.path

        return local_path

    def _to_browser_url(self, local_path):
        """Normalize saved paths into URL-like specifiers safe for HTML/runtime APIs."""
        if not local_path:
            return local_path

        if local_path.startswith(('http://', 'https://', '/', './', '../', 'data:', 'blob:')):
            return local_path

        return f"/{local_path.lstrip('/')}"

    def _process_stylesheets(self, soup):
        """Localize external stylesheets and rewrite their url() references."""
        self.log("Processando stylesheets...")
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if not href or href.startswith('data:'):
                continue

            for attr in ['integrity', 'crossorigin', 'nonce']:
                if link.has_attr(attr):
                    del link[attr]

            abs_url = urljoin(self.base_url, href)
            css_content = None

            if abs_url in self.network.network_resources:
                try:
                    css_content = self.network.network_resources[abs_url]['body'].decode('utf-8', errors='ignore')
                except Exception:
                    pass

            if not css_content:
                try:
                    response = self.network.session.get(abs_url, timeout=RESOURCE_TIMEOUT, verify=False)
                    if response.status_code == 200:
                        css_content = response.text
                except Exception:
                    pass

            if css_content:
                css_content = rewrite_css_urls(css_content, abs_url, self.network)
                local_path = self.network._save_resource(abs_url, css_content.encode('utf-8'), 'text/css')
                if local_path:
                    link['href'] = self._prefer_original_root_path(href, local_path)

    def _process_inline_styles(self, soup):
        """Rewrite url() in inline <style> tags."""
        self.log("Processando estilos inline...")
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                style_tag.string = rewrite_css_urls(style_tag.string, self.base_url, self.network)

    def _process_scripts(self, soup):
        """
        Localize external script src attributes.

        CRITICAL FIX: Remove scripts that failed to download to prevent SyntaxError cascades.
        When a .js file fails to download, the SPA router returns index.html,
        causing the browser to execute HTML as JavaScript -> SyntaxError.
        """
        self.log("Processando scripts...")

        scripts_to_remove = []
        original_script_urls = self._get_original_script_urls()
        runtime_injected_removed = 0

        for script in soup.find_all('script', src=True):
            src = script.get('src')
            if not src or src.startswith('data:'):
                continue

            absolute_src = urljoin(self.base_url, src)

            # page.content() includes the DOM after loaders have already run.
            # Persisting runtime-injected <script src> tags makes them execute a
            # second time offline when the original loader runs again.
            if original_script_urls is not None and absolute_src not in original_script_urls:
                scripts_to_remove.append(script)
                runtime_injected_removed += 1
                continue

            local_path = self.network.get_resource(src)

            # Check if download failed (resource returned unchanged or not localized)
            if local_path and local_path != src:
                # Success - update src to local path
                script['src'] = self._prefer_original_root_path(src, local_path)
                for attr in ['integrity', 'crossorigin', 'nonce']:
                    if script.has_attr(attr):
                        del script[attr]
            else:
                # CRITICAL: Download failed - check if it's a critical script
                # Don't remove tracking scripts (they're expected to fail)
                from . import SKIP_DOMAINS

                is_tracking = any(domain in src for domain in SKIP_DOMAINS)

                if not is_tracking:
                    # Non-tracking script that failed to download
                    # Remove it to prevent SPA router from serving index.html as JS
                    self.log(f"   ⚠️ Removendo script com download falhado: {src[:80]}...")
                    scripts_to_remove.append(script)

        # Remove failed scripts from DOM
        for script in scripts_to_remove:
            script.decompose()

        if runtime_injected_removed:
            self.log(f"   Removidos {runtime_injected_removed} scripts injetados em runtime")

    def _process_srcset(self, srcset, base=None):
        """Rewrite a srcset attribute value."""
        if not srcset:
            return srcset

        def _encode(path):
            return path.replace(' ', '%20')

        new_parts = []
        for part in srcset.split(','):
            part = part.strip()
            if not part:
                continue

            match = re.match(r'^(.+)\s+(\d+(?:\.\d+)?[wx])$', part)
            if match:
                url, descriptor = match.group(1).strip(), match.group(2)
            else:
                url, descriptor = part.strip(), ''

            if url.startswith('data:'):
                new_parts.append(part)
                continue

            if '/_next/image' in url and 'url=' in url:
                from urllib.parse import parse_qs, urlparse, unquote
                try:
                    parsed = urlparse(url)
                    query_params = parse_qs(parsed.query)
                    if 'url' in query_params:
                        original_url = unquote(query_params['url'][0])
                        full_url = urljoin(base or self.base_url, url)
                        resolved = self.network.get_resource(full_url, base)
                        if resolved == full_url:
                            resolved = None
                        if not resolved:
                            resolved = self.network.get_resource(original_url, base)
                            if resolved == original_url:
                                resolved = None
                        if resolved:
                            encoded = _encode(resolved)
                            new_parts.append(f"{encoded} {descriptor}" if descriptor else encoded)
                            continue
                except Exception:
                    pass

            local_path = self.network.get_resource(url, base)
            if local_path and local_path != url:
                encoded = _encode(local_path)
                new_parts.append(f"{encoded} {descriptor}" if descriptor else encoded)
            else:
                encoded = _encode(part) if ' ' in url else part
                if descriptor and ' ' in url:
                    encoded = f"{_encode(url)} {descriptor}"
                new_parts.append(encoded)

        return ', '.join(new_parts) if new_parts else ''

    def _process_images(self, soup):
        """Localize src, srcset, data-src, poster attributes on media elements."""
        self.log("Processando imagens...")
        for elem in soup.find_all(['img', 'source', 'video', 'audio', 'picture', 'input']):
            for attr in ['data-src', 'data-original', 'data-lazy-src', 'data-url', 'data-image', 'data-bg']:
                if elem.get(attr):
                    lazy_src = elem[attr]
                    local_path = self.network.get_resource(lazy_src)
                    if local_path and local_path != lazy_src:
                        elem['src'] = local_path
                        del elem[attr]
                    break

            src = elem.get('src')
            if src and not src.startswith('data:'):
                if '/_next/image' in src and 'url=' in src:
                    from urllib.parse import parse_qs, urlparse, unquote
                    try:
                        parsed = urlparse(src)
                        query_params = parse_qs(parsed.query)
                        if 'url' in query_params:
                            original_url = unquote(query_params['url'][0])
                            full_url = urljoin(self.base_url, src)
                            local_path = self.network.get_resource(full_url)
                            if local_path == full_url:
                                local_path = None
                            if not local_path:
                                local_path = self.network.get_resource(original_url)
                                if local_path == original_url:
                                    local_path = None
                            if local_path:
                                elem['src'] = local_path
                            continue
                    except Exception:
                        pass
                local_path = self.network.get_resource(src)
                if local_path and local_path != src:
                    elem['src'] = local_path

            srcset = elem.get('srcset')
            if srcset:
                elem['srcset'] = self._process_srcset(srcset)

            data_srcset = elem.get('data-srcset')
            if data_srcset:
                elem['data-srcset'] = self._process_srcset(data_srcset)

            if elem.name == 'video' and elem.get('poster'):
                poster = elem['poster']
                local_path = self.network.get_resource(poster)
                if local_path and local_path != poster:
                    elem['poster'] = local_path

    def _process_inline_style_attrs(self, soup):
        """Rewrite url() inside inline style='...' attributes."""
        self.log("Processando atributos de estilo inline...")
        for elem in soup.find_all(attrs={'style': True}):
            style = elem['style']
            if 'url(' in style:
                elem['style'] = rewrite_css_urls(style, self.base_url, self.network)

    def _process_favicons(self, soup):
        """Localize favicon and apple-touch-icon link tags."""
        for link in soup.find_all('link'):
            if link.get('href') and link.get('rel'):
                rel = link['rel']
                if isinstance(rel, list):
                    rel = ' '.join(rel)
                if any(x in rel.lower() for x in ['icon', 'apple-touch', 'manifest']):
                    href = link['href']
                    if not href.startswith('data:'):
                        local_path = self.network.get_resource(href)
                        if local_path and local_path != href:
                            link['href'] = local_path

    def _process_meta_images(self, soup):
        """Localize og:image and similar meta tag URLs."""
        for meta in soup.find_all('meta', attrs={'content': True}):
            prop = meta.get('property', '') or meta.get('name', '')
            if 'image' in prop.lower():
                content = meta['content']
                if content and not content.startswith('data:') and ('http' in content or content.startswith('/')):
                    local_path = self.network.get_resource(content)
                    if local_path and local_path != content:
                        meta['content'] = local_path

    def _process_background_attrs(self, soup):
        """Localize data-background attribute values."""
        for elem in soup.find_all(attrs={'data-background': True}):
            bg = elem['data-background']
            if bg and not bg.startswith('data:'):
                local_path = self.network.get_resource(bg)
                if local_path and local_path != bg:
                    elem['data-background'] = local_path

    def _fix_navigation_links(self, soup):
        """Replace internal absolute links with # (they won't work offline)."""
        self.log("Corrigindo links de navegação...")
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href == '/' or (href.startswith('/') and not href.startswith('//')):
                a['href'] = '#'

    def _detect_nextjs(self, soup):
        """Heuristic detection of Next.js pages."""
        for script in soup.find_all('script'):
            text = script.string or ''
            if '__NEXT_DATA__' in script.get('id', '') or '__NEXT_DATA__' in text:
                return True
            if 'self.__next' in text:
                return True
        for script in soup.find_all('script', src=True):
            src = script['src']
            if '_next/' in src or 'webpack' in src.lower():
                return True
        for link in soup.find_all('link'):
            if '_next/' in link.get('href', ''):
                return True
        return False

    def _is_ssr_framework(self, soup):
        """Detect SSR/SPA frameworks whose runtime mutates the DOM heavily."""
        return any([
            soup.find(id='___gatsby') is not None,
            soup.find(id='__nuxt') is not None,
            soup.find(id='__next') is not None,
            self._detect_nextjs(soup),
        ])

    def _handle_spa_frameworks(self, soup):
        """Preserve framework hydration/runtime scripts for offline execution."""
        is_gatsby = soup.find(id='___gatsby') is not None
        is_nextjs = soup.find(id='__next') is not None or self._detect_nextjs(soup)
        is_nuxt = soup.find(id='__nuxt') is not None

        if not (is_gatsby or is_nextjs or is_nuxt):
            return

        framework = 'Gatsby' if is_gatsby else ('Next.js' if is_nextjs else 'Nuxt')
        self.log(f"🛡️ Detectado {framework} - preservando scripts de hydration/runtime")

    def _remove_preconnects(self, soup):
        """Remove preconnect and dns-prefetch links (useless offline)."""
        removed = 0
        for link in soup.find_all('link', rel=lambda r: r and any(x in r for x in ['preconnect', 'dns-prefetch'])):
            link.decompose()
            removed += 1
        if removed:
            self.log(f"   Removidos {removed} preconnects/dns-prefetch")

    def _process_preloads(self, soup):
        """Localize preload/prefetch/modulepreload href attributes."""
        self.log("Processando preloads...")
        processed = 0
        for link in soup.find_all('link', rel=lambda r: r and any(x in r for x in ['preload', 'prefetch', 'modulepreload'])):
            href = link.get('href')
            if href and not href.startswith(('data:', 'blob:', 'assets/')):
                local_path = self.network.get_resource(href)
                if local_path and local_path != href:
                    link['href'] = self._prefer_original_root_path(href, local_path)
                    processed += 1
        if processed:
            self.log(f"   {processed} preloads reescritos")

    def _remove_tracking_scripts(self, soup):
        """Remove analytics/tracking script tags."""
        self.log("🛡️ Removendo scripts de tracking...")
        removed = 0
        for script in soup.find_all('script'):
            src = (script.get('src', '') or '').lower()
            text = (script.get_text() or '').lower()
            attr_values = []
            if isinstance(getattr(script, 'attrs', None), dict):
                for attr_value in script.attrs.values():
                    if isinstance(attr_value, list):
                        attr_values.extend(str(item).lower() for item in attr_value)
                    else:
                        attr_values.append(str(attr_value).lower())
            haystack = f"{src}\n{text}\n" + '\n'.join(attr_values)
            if any(pattern in haystack for pattern in TRACKING_SCRIPTS):
                script.decompose()
                removed += 1
        if removed:
            self.log(f"   Removidos {removed} scripts de tracking")

    def _remove_tracking_widgets(self, soup):
        """Remove runtime DOM widgets from tracking/marketing vendors."""
        removed = 0
        widget_markers = {
            'klaviyo',
            'kl-private-reset-css',
            'cookiebot',
            'cybotcookiebotdialog',
            'web-pixels',
            'web-pixel',
            'shopify-privacy',
            'hotjar',
            'intercom',
            'drift',
            'crisp',
            'zendesk',
            'tawk',
            'livechat',
            'freshchat',
        }

        for element in list(soup.find_all(True)):
            if element.name in {'html', 'head', 'body', 'meta'}:
                continue
            if element.parent is None:
                continue
            if not isinstance(getattr(element, 'attrs', None), dict):
                continue

            marker_values = []
            for attr_name, attr_value in element.attrs.items():
                if isinstance(attr_value, list):
                    marker_values.extend(str(item).lower() for item in attr_value)
                else:
                    marker_values.append(str(attr_value).lower())

            if element.name in {'style', 'noscript'}:
                marker_values.append((element.get_text() or '').lower())

            if not marker_values:
                continue

            if any(marker in value for value in marker_values for marker in widget_markers):
                element.decompose()
                removed += 1

        if removed:
            self.log(f"   Removidos {removed} widgets de tracking/marketing")

    def _inject_external_preload_bootstrap(self, soup):
        """
        Materialize external SDK preloads into executable script tags offline.

        Some frameworks preload third-party SDKs but insert the <script> tag later at
        runtime. Offline, that second step may never happen again, so expose the
        local captured asset as a real <script src=...> tag during initial parse.
        """
        resource_map = self.network.get_resource_map()
        if not resource_map:
            return

        site_host = urlparse(self.base_url).netloc.lower()
        original_script_urls = set(self._get_original_script_urls())
        reverse_map = {}
        for remote_url, local_path in resource_map.items():
            reverse_map.setdefault(local_path, []).append(remote_url)

        candidates = []
        seen = set()

        for link in soup.find_all('link', rel=lambda r: r and any(x in r for x in ['preload', 'modulepreload'])):
            href = link.get('href')
            if not href:
                continue

            as_value = (link.get('as') or '').strip().lower()
            rel_values = link.get('rel') or []
            is_module = any(value == 'modulepreload' for value in rel_values)
            if as_value != 'script' and not is_module:
                continue

            remote_matches = reverse_map.get(href, [])
            remote_url = next(
                (
                    remote for remote in remote_matches
                    if urlparse(remote).scheme in {'http', 'https'}
                    and urlparse(remote).netloc.lower() != site_host
                    and remote not in original_script_urls
                ),
                None,
            )
            if not remote_url:
                continue

            key = (href, is_module)
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                'local': href,
                'remote': remote_url,
                'module': is_module,
            })

        if not candidates:
            return

        head = soup.find('head')
        if not head:
            return

        injected = 0
        existing_script_srcs = {
            script.get('src')
            for script in soup.find_all('script', src=True)
            if script.get('src')
        }
        inline_script_blob = '\n'.join(
            script.get_text() or ''
            for script in soup.find_all('script')
            if not script.get('src') and not script.has_attr('data-fetch-interceptor')
        )

        for candidate in candidates:
            local_src = self._prefer_original_root_path(candidate['remote'], candidate['local'])
            local_src = self._to_browser_url(local_src)
            if local_src in existing_script_srcs:
                continue
            if candidate['remote'] in inline_script_blob or local_src in inline_script_blob:
                continue

            script_tag = soup.new_tag('script')
            script_tag['src'] = local_src
            script_tag['data-external-preload-bootstrap'] = 'true'
            if candidate['module']:
                script_tag['type'] = 'module'

            first_script = head.find('script')
            if first_script:
                first_script.insert_before(script_tag)
            else:
                head.append(script_tag)
            existing_script_srcs.add(local_src)
            injected += 1

        if injected:
            self.log(f"   Materializados {injected} script(s) externos a partir de preload")

    def _is_shopify_document(self, soup):
        """Detect Shopify storefront documents that expect a global Shopify bootstrap."""
        if soup.find('meta', attrs={'name': 'shopify-checkout-api-token'}):
            return True
        if soup.find('meta', attrs={'id': 'shopify-digital-wallet'}):
            return True

        html_blob = str(soup)[:250000]
        return 'Shopify.designMode' in html_blob or '/cdn/shop/t/' in html_blob

    def _inject_shopify_bootstrap(self, soup):
        """Provide a minimal Shopify global before inline theme scripts execute offline."""
        if not self._is_shopify_document(soup):
            return

        head = soup.find('head')
        if not head:
            return

        existing_bootstrap = head.find(
            'script',
            attrs={'data-generated-shopify-bootstrap': 'true'},
        )
        if existing_bootstrap:
            return

        script_tag = soup.new_tag('script')
        script_tag['data-generated-shopify-bootstrap'] = 'true'
        script_tag.string = (
            "window.Shopify = window.Shopify || {};"
            "if (typeof window.Shopify.designMode === 'undefined') {"
            "window.Shopify.designMode = false;"
            "}"
        )

        first_script = head.find('script')
        if first_script:
            first_script.insert_before(script_tag)
        else:
            head.insert(0, script_tag)

    def _build_import_map(self):
        """Map absolute JS module specifiers to local offline assets."""
        resource_map = self.network.get_resource_map()
        if not resource_map:
            return {}

        imports = {}
        for remote_url, local_path in resource_map.items():
            if not local_path.endswith(('.js', '.mjs')):
                continue

            parsed = urlparse(remote_url)
            if parsed.scheme not in {'http', 'https'}:
                continue

            local_specifier = self._prefer_original_root_path(remote_url, local_path)
            local_specifier = self._to_browser_url(local_specifier)
            imports[remote_url] = local_specifier

            if parsed.scheme == 'https':
                imports[f"http://{parsed.netloc}{parsed.path}"] = local_specifier
            elif parsed.scheme == 'http':
                imports[f"https://{parsed.netloc}{parsed.path}"] = local_specifier

        return imports

    def _inject_import_map(self, soup):
        """Inject an import map for absolute dynamic imports before scripts execute."""
        imports = self._build_import_map()
        if not imports:
            return

        head = soup.find('head')
        if not head:
            return

        script_tag = soup.new_tag('script')
        script_tag['type'] = 'importmap'
        script_tag['data-generated-importmap'] = 'true'
        script_tag.string = json.dumps({'imports': imports}, ensure_ascii=False)

        first_script = head.find('script')
        if first_script:
            first_script.insert_before(script_tag)
        else:
            head.insert(0, script_tag)

    def _inject_fetch_interceptor(self, soup):
        """Read the JS template, inject resource map, and prepend to <head>."""
        self.log("💉 Injetando fetch interceptor aprimorado...")

        resource_map = self.network.get_resource_map()
        if not resource_map:
            self.log("   Resource map vazio, interceptor não injetado")
            return

        # Load JS template from external file
        try:
            with open(self._interceptor_js_path, 'r', encoding='utf-8') as f:
                js_template = f.read()
        except OSError as e:
            self.log(f"   Erro ao ler fetch_interceptor.js: {e}")
            return

        # Build resource map loading code
        if len(resource_map) > 500:
            map_filename = 'resource-map.json'
            map_path = os.path.join(self.output_dir, 'assets', map_filename)
            with open(map_path, 'w', encoding='utf-8') as f:
                json.dump(resource_map, f)
            map_load_code = f"const response = await fetch('assets/{map_filename}');\n    const resourceMap = await response.json();"
        else:
            map_load_code = f"const resourceMap = {json.dumps(resource_map, ensure_ascii=False)};"

        # Replace placeholder in template
        interceptor_script = js_template.replace('/* __RESOURCE_MAP_CODE__ */', map_load_code)

        head = soup.find('head')
        if head:
            script_tag = soup.new_tag('script')
            script_tag['data-fetch-interceptor'] = 'true'
            script_tag.append(NavigableString(interceptor_script))
            import_maps = head.find_all('script', attrs={'type': 'importmap'})
            if import_maps:
                import_maps[-1].insert_after(script_tag)
            elif head.contents:
                head.insert(0, script_tag)
            else:
                head.append(script_tag)
            self.log(f"   Fetch interceptor injetado ({len(resource_map)} mapeamentos)")
        else:
            self.log("   <head> não encontrado, interceptor não injetado")
