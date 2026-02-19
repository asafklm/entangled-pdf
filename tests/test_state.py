"""Tests for state management."""

from src.state import PDFState, pdf_state


class TestPDFState:
    """Test suite for PDFState."""
    
    def test_default_values(self):
        """Test default state values."""
        state = PDFState()
        
        assert state.current_page == 1
        assert state.current_y is None
        assert state.last_update_time > 0
    
    def test_update_changes_values(self):
        """Test that update changes state values."""
        import time
        
        state = PDFState()
        old_timestamp = state.last_update_time
        
        # Small delay to ensure timestamp changes
        time.sleep(0.01)
        
        state.update(page=5, y=100.5)
        
        assert state.current_page == 5
        assert state.current_y == 100.5
        assert state.last_update_time >= old_timestamp
    
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
        assert "last_update_time" in result


class TestGlobalState:
    """Test suite for global state instance."""
    
    def test_global_state_exists(self):
        """Test that global state instance exists."""
        assert pdf_state is not None
        assert isinstance(pdf_state, PDFState)
