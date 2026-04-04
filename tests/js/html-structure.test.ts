import { describe, it, expect, beforeEach } from "vitest";
import { readFileSync } from "fs";
import { join } from "path";

/**
 * HTML Structure Validation Tests
 * 
 * Verifies that static HTML files contain required UI components.
 * These tests catch accidental deletions or structural changes that
 * would break the TypeScript viewer code which depends on these elements.
 */
describe("HTML Structure Validation", () => {
  const staticDir = join(__dirname, "../../static");
  
  describe("viewer.html", () => {
    let doc: Document;
    
    beforeEach(() => {
      const html = readFileSync(join(staticDir, "viewer.html"), "utf-8");
      doc = new DOMParser().parseFromString(html, "text/html");
    });
    
    it("should have error banner element", () => {
      expect(doc.getElementById("error-banner")).not.toBeNull();
    });
    
    it("should have status indicator element", () => {
      expect(doc.getElementById("status")).not.toBeNull();
    });
    
    it("should have no-pdf message with proper structure", () => {
      const noPdfMsg = doc.getElementById("no-pdf-message");
      expect(noPdfMsg).not.toBeNull();
      expect(noPdfMsg!.querySelector("h2")).not.toBeNull();
      expect(noPdfMsg!.querySelector("p")).not.toBeNull();
    });
    
    it("should have viewer container with tabindex", () => {
      const container = doc.getElementById("viewer-container");
      expect(container).not.toBeNull();
      expect(container!.getAttribute("tabindex")).toBe("0");
    });
    
    it("should have connection status indicator", () => {
      const status = doc.getElementById("connection-status");
      expect(status).not.toBeNull();
      expect(status!.querySelector(".status-dot")).not.toBeNull();
      expect(status!.querySelector(".status-text")).not.toBeNull();
    });
    
    it("should have connection details panel with 3 rows", () => {
      const panel = doc.getElementById("connection-details");
      expect(panel).not.toBeNull();
      
      const rows = panel!.querySelectorAll(".detail-row");
      expect(rows.length).toBe(3);
    });
    
    it("should have correct connection detail labels", () => {
      const panel = doc.getElementById("connection-details");
      const labels = panel!.querySelectorAll(".detail-label");
      const labelTexts = Array.from(labels).map(l => l.textContent?.trim());
      
      expect(labelTexts).toContain("Status");
      expect(labelTexts).toContain("PDF File");
      expect(labelTexts).toContain("PDF Modified");
    });
    
    it("should have detail value elements referenced by TypeScript", () => {
      expect(doc.getElementById("detail-status")).not.toBeNull();
      expect(doc.getElementById("detail-filename")).not.toBeNull();
      expect(doc.getElementById("detail-modified")).not.toBeNull();
    });
    
    it("should load viewer.js as ES module", () => {
      const scripts = doc.querySelectorAll('script[type="module"]');
      const viewerScript = Array.from(scripts).find(s => 
        s.getAttribute("src")?.includes("viewer.js")
      );
      expect(viewerScript).not.toBeUndefined();
    });
  });
  
  describe("token_form.html", () => {
    let doc: Document;
    
    beforeEach(() => {
      const html = readFileSync(join(staticDir, "token_form.html"), "utf-8");
      doc = new DOMParser().parseFromString(html, "text/html");
    });
    
    it("should have authentication container", () => {
      expect(doc.querySelector(".auth-container")).not.toBeNull();
    });
    
    it("should have form with POST method to /auth", () => {
      const form = doc.querySelector('form[method="post"][action="/auth"]');
      expect(form).not.toBeNull();
    });
    
    it("should have token input field", () => {
      const input = doc.querySelector('input[name="token"]');
      expect(input).not.toBeNull();
      expect(input!.getAttribute("required")).not.toBeNull();
    });
    
    it("should have submit button", () => {
      const button = doc.querySelector('button[type="submit"]');
      expect(button).not.toBeNull();
    });
  });
});
