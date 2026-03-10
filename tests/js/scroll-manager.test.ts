import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  calculateScrollTop,
  getCurrentScrollPosition,
  getTargetScrollPosition,
  performScroll,
  getUpperViewportY,
} from "../../static/scroll-manager";

describe("ScrollManager - helpers", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "getComputedStyle",
      (_el: Element) => ({ paddingTop: "20px" } as CSSStyleDeclaration)
    );
  });

  it("calculateScrollTop should compute correct target scroll position", () => {
    const container = document.createElement("div");
    Object.defineProperty(container, "clientHeight", { value: 800, writable: true });
    const target = document.createElement("div");
    Object.defineProperty(target, "offsetTop", { value: 500, writable: true });

    const result = calculateScrollTop(container, target, 300);
    expect(typeof result).toBe("number");
    expect(result).toBeGreaterThanOrEqual(0);
  });

  it("getCurrentScrollPosition should return correct page and position", () => {
    const container = document.createElement("div");
    Object.defineProperty(container, "clientHeight", { value: 800, writable: true });
    Object.defineProperty(container, "scrollTop", { value: 450, writable: true });

    const pageElements: { [key: number]: HTMLElement } = {
      1: document.createElement("div"),
      2: document.createElement("div"),
    };
    Object.defineProperty(pageElements[1], "offsetTop", { value: 0, writable: true });
    Object.defineProperty(pageElements[2], "offsetTop", { value: 800, writable: true });

    const result = getCurrentScrollPosition(container, pageElements);
    expect(result).not.toBeNull();
    expect(result).toHaveProperty("page");
    expect(result).toHaveProperty("y");
    expect(result).toHaveProperty("pixels");
  });

  it("getTargetScrollPosition should calculate target position for a page", () => {
    const container = document.createElement("div");
    Object.defineProperty(container, "clientHeight", { value: 800, writable: true });

    const pageElements: { [key: number]: HTMLElement } = {
      2: document.createElement("div"),
    };
    Object.defineProperty(pageElements[2], "offsetTop", { value: 800, writable: true });

    const result = getTargetScrollPosition(container, pageElements, 2, 300);
    expect(result).not.toBeNull();
    expect(result?.page).toBe(2);
  });

  it("performScroll should call scrollTo on container", () => {
    const container = document.createElement("div");
    let scrollToCalled = false;
    let scrollToArgs: { top?: number; left?: number; behavior?: ScrollBehavior } = {};
    container.scrollTo = function (options?: ScrollToOptions | number, y?: number) {
      scrollToCalled = true;
      if (typeof options === "object" && options !== null) {
        scrollToArgs = options;
      }
    };

    performScroll(container, 300, "auto");
    expect(scrollToCalled).toBe(true);
  });

  it("getUpperViewportY should return 1/4 viewport when above lower bound", () => {
    const container = document.createElement("div");
    Object.defineProperty(container, "clientHeight", { value: 800, writable: true });

    const result = getUpperViewportY(container);
    expect(result).toBe(200); // 800/4 = 200, which is > 100
  });

  it("getUpperViewportY should use 1/4 viewport when above lower bound", () => {
    const container = document.createElement("div");
    Object.defineProperty(container, "clientHeight", { value: 600, writable: true });

    const result = getUpperViewportY(container);
    expect(result).toBe(150);
  });
});
