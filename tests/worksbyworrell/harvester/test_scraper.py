from unittest.mock import patch

from src.worksbyworrell.harvester.scraper import get_page_text


@patch("src.worksbyworrell.harvester.scraper.requests.get")
def test_get_page_text_success(mock_get):
    """Test that HTML is successfully fetched and stripped of tags."""
    # Mocking the response object
    mock_get.return_value.text = "<html><body><h1>Test Job</h1><p>Requirements: Python</p></body></html>"
    
    result = get_page_text("http://fake-job-board.com/123")
    
    assert "Test Job" in result
    assert "Requirements: Python" in result
    assert "<h1>" not in result  # Tags should be stripped by BeautifulSoup
    assert mock_get.called

@patch("src.worksbyworrell.harvester.scraper.requests.get")
def test_get_page_text_failure(mock_get):
    """Test that a failure returns an empty string."""
    mock_get.side_effect = Exception("Connection Refused")
    
    result = get_page_text("http://fake-job-board.com/error")
    
    assert result == ""
