/* Building DOM without innerHTML. Everything on this page that came from
 * GitHub — titles, bodies, label names — is someone else's text, so it only
 * ever goes in through textContent. */

type Child = Node | string | number | null | undefined | false;
type Attrs = Record<string, string | number | boolean | null | undefined | EventListener>;

export function h<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs: Attrs | null = null,
  ...children: (Child | Child[])[]
): HTMLElementTagNameMap[K] {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs ?? {})) {
    if (value === null || value === undefined || value === false) continue;
    if (typeof value === "function") {
      el.addEventListener(key.replace(/^on/, ""), value);
    } else if (key === "class") {
      el.className = String(value);
    } else if (key === "style") {
      el.setAttribute("style", String(value));
    } else if (value === true) {
      el.setAttribute(key, "");
    } else {
      el.setAttribute(key, String(value));
    }
  }
  append(el, children);
  return el;
}

function append(el: Element, children: (Child | Child[])[]): void {
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
}

export function byId<T extends Element = HTMLElement>(id: string): T {
  const el = document.querySelector<T>(`#${id}`);
  if (!el) throw new Error(`#${id} is missing from index.html`);
  return el;
}

export function fill(el: Element, ...children: (Child | Child[])[]): void {
  el.replaceChildren();
  append(el, children);
}
