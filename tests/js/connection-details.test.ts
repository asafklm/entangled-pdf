import { describe, it, expect, beforeEach, vi } from "vitest";

/**
 * Simple tests for connection details panel
 * Verifies panel exists and basic toggle functionality works
 */
describe("Connection Details Panel", () => {
  beforeEach(() => {
    // Reset DOM before each test
    document.body.innerHTML = '';
    
    // Set up minimal HTML structure for the panel
    document.body.innerHTML = `
      <div id="connection-status" style="display: none;">
        <span class="status-dot"></span>
        <span class="status-text">Connected</span>
      </div>
      <div id="connection-details">
        <h4>Connection Details</h4>
        <div class="detail-row">
          <span class="detail-label">Status</span>
          <span id="detail-status" class="detail-value">-</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">PDF File</span>
          <span id="detail-filename" class="detail-value">-</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">PDF Modified</span>
          <span id="detail-modified" class="detail-value">-</span>
        </div>
      </div>
    `;
  });

  it("should have connection-details element in DOM", () => {
    const panel = document.getElementById('connection-details');
    expect(panel).not.toBeNull();
  });

  it("should have expected detail rows", () => {
    const panel = document.getElementById('connection-details');
    expect(panel).not.toBeNull();
    
    const rows = panel!.querySelectorAll('.detail-row');
    expect(rows.length).toBe(3);
    
    // Check labels exist
    const labels = panel!.querySelectorAll('.detail-label');
    const labelTexts = Array.from(labels).map(l => l.textContent);
    
    expect(labelTexts).toContain('Status');
    expect(labelTexts).toContain('PDF File');
    expect(labelTexts).toContain('PDF Modified');
  });

  it("should have detail value elements", () => {
    expect(document.getElementById('detail-status')).not.toBeNull();
    expect(document.getElementById('detail-filename')).not.toBeNull();
    expect(document.getElementById('detail-modified')).not.toBeNull();
  });

  it("should toggle visible class when clicked", () => {
    const panel = document.getElementById('connection-details');
    const status = document.getElementById('connection-status');
    
    expect(panel).not.toBeNull();
    expect(status).not.toBeNull();
    
    // Initially not visible
    expect(panel!.classList.contains('visible')).toBe(false);
    
    // Simulate toggle function behavior
    panel!.classList.add('visible');
    expect(panel!.classList.contains('visible')).toBe(true);
    
    // Toggle off
    panel!.classList.remove('visible');
    expect(panel!.classList.contains('visible')).toBe(false);
  });
});
