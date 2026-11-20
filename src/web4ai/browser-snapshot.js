
(opts) => {
  const maxElements = (opts && opts.maxElements) || 250;
  const maxName = 80;
  const ATTR = "data-web4ai-ref";

  for (const el of document.querySelectorAll("[" + ATTR + "]")) el.removeAttribute(ATTR);

  const selector = [
    "a[href]", "button", "input:not([type='hidden'])", "select", "textarea",
    "summary", "label", "[role]", "[onclick]",
    "[contenteditable='']", "[contenteditable='true']",
    "[tabindex]:not([tabindex='-1'])", "h1", "h2", "h3"
  ].join(",");

  const isVisible = (el) => {
    if (el.closest("[aria-hidden='true']") || el.closest("[hidden]")) return false;
    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) return false;
    const style = getComputedStyle(el);
    return style.visibility !== "hidden" && style.display !== "none" && style.opacity !== "0";
  };

  const roleOf = (el) => {
    const explicit = el.getAttribute("role");
    if (explicit) return explicit.trim().split(/\s+/)[0];
    const tag = el.tagName.toLowerCase();
    if (tag === "a") return "link";
    if (tag === "button") return "button";
    if (tag === "select") return el.multiple ? "listbox" : "combobox";
    if (tag === "textarea") return "textbox";
    if (tag === "label") return "label";
    if (tag === "summary") return "button";
    if (tag === "h1" || tag === "h2" || tag === "h3") return "heading";
    if (tag === "input") {
      const type = (el.getAttribute("type") || "text").toLowerCase();
      if (["button", "submit", "reset", "image", "file"].includes(type)) return "button";
      if (type === "checkbox" || type === "radio") return type;
      if (type === "range") return "slider";
      if (type === "search") return "searchbox";
      return "textbox";
    }
    return "generic";
  };

  const clean = (value) => String(value == null ? "" : value).replace(/\s+/g, " ").trim();

  const nameOf = (el) => {
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute("type") || "").toLowerCase();
    const candidates = [
      el.getAttribute("aria-label"),
      el.getAttribute("placeholder"),
      el.getAttribute("alt"),
      el.getAttribute("title"),
      tag === "input" && ["button", "submit", "reset"].includes(type) ? el.value : "",
      el.innerText,
      el.textContent
    ];
    for (const candidate of candidates) {
      const text = clean(candidate);
      if (text) return text.slice(0, maxName);
    }
    return "";
  };

  const stateOf = (el) => {
    const out = [];
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute("type") || "").toLowerCase();
    if (el.disabled) out.push("disabled");
    if (el.checked) out.push("checked");
    if (el.required) out.push("required");
    const expanded = el.getAttribute("aria-expanded");
    if (expanded) out.push("expanded=" + expanded);
    if (el === document.activeElement) out.push("focused");
    if (
      ["input", "textarea", "select"].includes(tag) &&
      !["checkbox", "radio", "file", "button", "submit", "reset"].includes(type)
    ) {
      const value = clean(el.value);
      if (value) out.push('value="' + value.slice(0, 60) + '"');
    }
    if (tag === "a") {
      const href = el.getAttribute("href");
      if (href) out.push('href="' + href.slice(0, 80) + '"');
    }
    return out.length ? " [" + out.join(", ") + "]" : "";
  };

  const elements = [];
  for (const el of document.querySelectorAll(selector)) {
    if (elements.length >= maxElements) break;
    if (isVisible(el)) elements.push(el);
  }

  const visibleSet = new Set(elements);
  const depthOf = (el) => {
    let depth = 0;
    let node = el.parentElement;
    while (node && depth < 5) {
      if (visibleSet.has(node)) depth += 1;
      node = node.parentElement;
    }
    return depth;
  };

  const lines = [];
  elements.forEach((el, index) => {
    const ref = "e" + (index + 1);
    el.setAttribute(ATTR, ref);
    const name = nameOf(el);
    lines.push(
      "  ".repeat(depthOf(el)) +
        "- " + roleOf(el) +
        (name ? ' "' + name + '"' : "") +
        " [ref=" + ref + "]" +
        stateOf(el)
    );
  });

  return {
    title: document.title,
    url: location.href,
    scroll: window.scrollY + "px of " + document.documentElement.scrollHeight + "px",
    count: elements.length,
    truncated: elements.length >= maxElements,
    lines: lines
  };
}
