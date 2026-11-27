
(type) => {
  const actionable = Array.from(document.querySelectorAll(selector));
  const active = actionable.filter(enabled)

  const clickableElements = active
    .filter(isClick)
    .filter(clickable)
    .map(describe)
  const fillable = active
    .filter(isFill)
    .map(describe)
  const toggleable = active
    .filter(isToggle)
    .map(describe)
  const navigatable = active
    .filter(isNavigate)
    .map(describe)
  const selectable = active
    .filter(isSelect)
    .map(describe)


  let result = {}
  result.click = clickableElements
  result.fill = fillable
  result.toggle = toggleable
  result.navigate = navigatable
  result.select = selectable
  return type == "all" ?
    JSON.stringify(result, null, 2)
    : JSON.stringify(result[type], null, 2)
}

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

const pwVisible = el => {
  const r = el.getBoundingClientRect();
  if (r.width <= 0 || r.height <= 0) return false;
  const v = getComputedStyle(el).visibility;
  return v !== 'hidden' && v !== 'collapse';
};

const clickable = el => {
  if (!pwVisible(el)) return false;
  const cs = getComputedStyle(el);
  if (cs.opacity === '0' || cs.pointerEvents === 'none') return false;
  if (el.closest('[inert]')) return false;
  // is the point actually ours, or is something on top?
  const r = el.getBoundingClientRect();
  const hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
  return !!hit && (el === hit || el.contains(hit));
};
const OK_SCHEME = /^(https?|mailto|tel):$/i;

const hrefOf = el => {
  let target = null;
  for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
    if (n.matches('a[href], area[href]')) { target = n; break; }
  }
  if (!target) {
    const inner = el.querySelectorAll?.('a[href]') || [];
    if (inner.length === 1) target = inner[0];
  }
  if (!target) return null;

  const raw = target.getAttribute('href');
  if (!raw || raw.startsWith('#')) return null;      // skip in-page anchors

  try {
    const u = new URL(target.href, document.baseURI);
    if (!OK_SCHEME.test(u.protocol)) return null;    // drops javascript:, blob:, data:
    return u.href;
  } catch { return null; }
};

const describe = el => ({
  context: context(el),
  type: el.type,
  selector: toSelector(el),
  href: hrefOf(el)
});

const enabled = el => {
  if (el.matches(':disabled')) return false;          // includes fieldset[disabled]
  if (el.getAttribute('aria-disabled') === 'true') return false;
  if (el.closest('fieldset[disabled], [inert]')) return false;
  return true;
};

const ROLE = el => (el.getAttribute('role') || '').toLowerCase();
const TYPE = el => (el.getAttribute('type') || '').toLowerCase();

const NON_TEXT = new Set(['checkbox', 'radio', 'submit', 'button', 'reset', 'image', 'file', 'hidden', 'range', 'color']);

const isNavigate = el => !!hrefOf(el);
const isSelect = el => el.tagName === 'SELECT' || ['listbox', 'combobox'].includes(ROLE(el));
const isFill = el => el.tagName === 'TEXTAREA' || el.isContentEditable
  || ['textbox', 'searchbox'].includes(ROLE(el))
  || (el.tagName === 'INPUT' && !NON_TEXT.has(TYPE(el)));
const isToggle = el => el.matches('input[type=checkbox],input[type=radio]')
  || ['checkbox', 'radio', 'switch', 'option'].includes(ROLE(el));
const isClick = el => !isNavigate(el) && (
  el.tagName === 'BUTTON' || el.tagName === 'SUMMARY'
  || ROLE(el) === 'button' || el.hasAttribute('onclick')
  || el.tabIndex >= 0 || el.isContentEditable === false && ROLE(el) === 'menuitem');
