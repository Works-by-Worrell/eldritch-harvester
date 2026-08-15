from unittest.mock import patch

from src.worksbyworrell.harvester.scraper import fetch_job_links, get_page_text


@patch("src.worksbyworrell.harvester.scraper.requests.get")
def test_get_page_text_success(mock_get):
    """Test that HTML is successfully fetched and stripped of tags."""
    mock_get.return_value.text = (
        "<html><body><h1>Test Job</h1><p>Requirements: Python</p></body></html>"
    )

    result = get_page_text("http://fake-job-board.com/123")

    assert "Test Job" in result
    assert "Requirements: Python" in result
    assert "<h1>" not in result
    assert mock_get.called


@patch("src.worksbyworrell.harvester.scraper.requests.get")
def test_get_page_text_failure(mock_get):
    """Test that a failure returns an empty string."""
    mock_get.side_effect = Exception("Connection Refused")

    result = get_page_text("http://fake-job-board.com/error")

    assert result == ""


@patch("src.worksbyworrell.harvester.scraper.requests.get")
def test_fetch_job_links_filters_location_and_category_hubs(mock_get):
    """Test that fetch_job_links collects valid JD links and excludes region/category hubs."""
    html_content = """
    <html>
        <body>
            <a href="https://builtin.com/jobs/operations">Operations Hub</a>
            <a href="https://builtin.com/jobs/miami">Miami Jobs</a>
            <a href="https://builtin.com/jobs/sales/account-executive">Sales Hub</a>
            <a href="https://builtin.com/job/senior-principal-engineer/10170358">Valid JD 1</a>
            <a href="/job/staff-software-engineer/9857802">Valid JD 2 (relative)</a>
        </body>
    </html>
    """
    mock_get.return_value.text = html_content

    links = fetch_job_links("https://builtin.com/jobs?search=engineer")

    assert len(links) == 2
    assert "https://builtin.com/job/senior-principal-engineer/10170358" in links
    assert "https://builtin.com/job/staff-software-engineer/9857802" in links
    assert "https://builtin.com/jobs/operations" not in links
    assert "https://builtin.com/jobs/miami" not in links
