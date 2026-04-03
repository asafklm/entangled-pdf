"""Tests for state management."""

import time
from pathlib import Path

from pdfserver.state import PDFState, pdf_state


class TestPDFState:
    """Test suite for PDFState."""
    
    def test_default_values(self):
        """Test default state values."""
        state = PDFState()
        
        assert state.current_page == 1
        assert state.current_y is None
        assert state.last_sync_time > 0
    
    def test_update_changes_values(self):
        """Test that update changes state values."""
        import time
        
        state = PDFState()
        old_timestamp = state.last_sync_time
        
        # Small delay to ensure timestamp changes
        time.sleep(0.01)
        
        state.update(page=5, y=100.5)
        
        assert state.current_page == 5
        assert state.current_y == 100.5
        assert state.last_sync_time >= old_timestamp
    
    def test_update_without_y(self):
        """Test update with only page number."""
        state = PDFState()
        
        state.update(page=3)
        
        assert state.current_page == 3
        assert state.current_y is None
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        state = PDFState()
        state.update(page=2, y=50.0)
        
        result = state.to_dict()
        
        assert result["page"] == 2
        assert result["y"] == 50.0
        assert "last_sync_time" in result

    def test_to_dict_includes_pdf_mtime(self):
        """Test that to_dict includes pdf_mtime field."""
        state = PDFState()
        state.pdf_mtime = 1234567890.5
        
        result = state.to_dict()
        
        assert "pdf_mtime" in result
        assert result["pdf_mtime"] == 1234567890.5

    def test_to_dict_includes_pdf_file(self):
        """Test that to_dict includes pdf_file field (full path)."""
        state = PDFState()
        state.pdf_file = Path("/path/to/test.pdf")
        
        result = state.to_dict()
        
        assert "pdf_file" in result
        assert result["pdf_file"] == "/path/to/test.pdf"

    def test_to_dict_includes_pdf_basename(self):
        """Test that to_dict includes pdf_basename field."""
        state = PDFState()
        state.pdf_file = Path("/path/to/test.pdf")
        
        result = state.to_dict()
        
        assert "pdf_basename" in result
        assert result["pdf_basename"] == "test.pdf"

    def test_to_dict_pdf_basename_none_when_no_file(self):
        """Test that pdf_basename is None when no PDF file is set."""
        state = PDFState()
        state.pdf_file = None
        
        result = state.to_dict()
        
        assert "pdf_basename" in result
        assert result["pdf_basename"] is None

    def test_to_dict_includes_pdf_loaded(self):
        """Test that to_dict includes pdf_loaded field."""
        state = PDFState()
        state.pdf_file = Path("/path/to/test.pdf")
        
        result = state.to_dict()
        
        assert "pdf_loaded" in result
        assert result["pdf_loaded"] is True

    def test_to_dict_pdf_loaded_false_when_no_file(self):
        """Test that pdf_loaded is False when no PDF file is set."""
        state = PDFState()
        state.pdf_file = None
        
        result = state.to_dict()
        
        assert "pdf_loaded" in result
        assert result["pdf_loaded"] is False


class TestPDFStateUpdatePdf:
    """Test suite for PDFState.update_pdf() method."""
    
    def test_update_pdf_detects_new_file(self, tmp_path):
        """Test that update_pdf detects a new PDF file."""
        state = PDFState()
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"PDF content")
        
        result = state.update_pdf(pdf_path)
        
        assert result is True
        assert state.pdf_file == pdf_path
        assert state.pdf_mtime is not None
    
    def test_update_pdf_detects_same_file_no_change(self, tmp_path):
        """Test that update_pdf returns False when same file, no changes."""
        state = PDFState()
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"PDF content")
        
        # First update
        state.update_pdf(pdf_path)
        
        # Second update with same file
        result = state.update_pdf(pdf_path)
        
        assert result is False
    
    def test_update_pdf_detects_different_file(self, tmp_path):
        """Test that update_pdf detects different PDF file."""
        state = PDFState()
        
        # Create first PDF
        pdf1 = tmp_path / "first.pdf"
        pdf1.write_bytes(b"PDF 1")
        state.update_pdf(pdf1)
        
        # Create second PDF
        pdf2 = tmp_path / "second.pdf"
        pdf2.write_bytes(b"PDF 2")
        
        result = state.update_pdf(pdf2)
        
        assert result is True
        assert state.pdf_file == pdf2
    
    def test_update_pdf_detects_mtime_change(self, tmp_path):
        """Test that update_pdf detects file modification (mtime change)."""
        state = PDFState()
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"Original content")
        
        # First update
        state.update_pdf(pdf_path)
        old_mtime = state.pdf_mtime
        
        # Wait and modify file
        time.sleep(0.1)
        pdf_path.write_bytes(b"Modified content")
        
        # Second update
        result = state.update_pdf(pdf_path)
        
        assert result is True
        assert state.pdf_mtime > old_mtime
    
    def test_update_pdf_handles_nonexistent_file(self, tmp_path):
        """Test that update_pdf handles non-existent file gracefully."""
        state = PDFState()
        nonexistent = tmp_path / "nonexistent.pdf"
        
        result = state.update_pdf(nonexistent)
        
        assert result is True  # Path changed (from None to something)
        assert state.pdf_file == nonexistent
        assert state.pdf_mtime is None  # Can't stat non-existent file


class TestGlobalState:
    """Test suite for global state instance."""
    
    def test_global_state_exists(self):
        """Test that global state instance exists."""
        assert pdf_state is not None
        assert isinstance(pdf_state, PDFState)
