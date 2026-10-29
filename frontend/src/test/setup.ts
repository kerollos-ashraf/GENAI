import "@testing-library/jest-dom/vitest";

// jsdom has no layout, so it doesn't implement scrolling; the app only needs the call to exist.
if (!("scrollTo" in Element.prototype)) {
  Object.defineProperty(Element.prototype, "scrollTo", { value: () => undefined, writable: true });
}
