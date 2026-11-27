const selector = [
  // intrinsic tags
  'a[href]', 'button', 'input', 'select', 'textarea',
  'summary', 'details', 'option', 'label[for]', 'iframe', '[controls]',
  // ARIA roles
  '[role="button"]', '[role="link"]', '[role="textbox"]', '[role="checkbox"]',
  '[role="radio"]', '[role="switch"]', '[role="tab"]', '[role="menuitem"]',
  '[role="option"]', '[role="combobox"]', '[role="slider"]', '[role="searchbox"]',
  // interactivity attributes
  '[tabindex]', '[contenteditable]', '[onclick]'
];

const actionable = Array.from(document.querySelectorAll(selector));
const resolveIds = ids =>
  ids.split(/\s+/)
     .map(id => document.getElementById(id)?.textContent?.trim())
     .filter(Boolean).join(' ') || null;

const context = el =>
  resolveIds(el.getAttribute('aria-labelledby') || '') ||
  el.getAttribute('aria-label') ||
  el.labels?.[0]?.textContent?.trim() ||
  (el.tagName === 'INPUT' && ['button', 'submit', 'reset'].includes(el.type) ? el.value : null) ||
  el.getAttribute('placeholder') ||
  el.getAttribute('title') ||
  el.getAttribute('alt') ||
  (el.textContent || '').trim().slice(0, 80) ||
  (el.name ? `[name=${el.name}]` : null);

const esc = s => (window.CSS?.escape ? CSS.escape(s) : s.replace(/[^a-zA-Z0-9_-]/g, c => '\\' + c));
const unique = sel => { try { return document.querySelectorAll(sel).length === 1; } catch { return false; } };

const toSelector = el => {
  // 1. unique id wins outright
  if (el.id && unique('#' + esc(el.id))) return '#' + esc(el.id);

  // 2. otherwise climb, adding :nth-of-type only where siblings are ambiguous
  const parts = [];
  let node = el;
  while (node && node.nodeType === 1 && node !== document.documentElement) {
    if (node !== el && node.id && unique('#' + esc(node.id))) {
      parts.unshift('#' + esc(node.id));
      break;                                   // anchor at a stable ancestor
    }
    let part = node.tagName.toLowerCase();
    const parent = node.parentElement;
    if (parent) {
      const sib = Array.from(parent.children).filter(c => c.tagName === node.tagName);
      if (sib.length > 1) part += `:nth-of-type(${sib.indexOf(node) + 1})`;
    }
    parts.unshift(part);
    node = parent;
  }
  return parts.join(' > ');
};

const describe = el => ({
    context: context(el),
    type: el.type,
    selector: toSelector(el)
});


actionable.map(e => `${JSON.stringify(describe(e), null, 2)}\n\n`).toString()
