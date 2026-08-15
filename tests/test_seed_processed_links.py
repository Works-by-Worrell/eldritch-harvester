from scripts.seed_processed_links_from_youtrack import (
    extract_source_url,
    load_existing_processed_links,
    save_processed_links,
)


def test_extract_source_url_formatted():
    description = """
**Source URL:** https://builtin.com/job/senior-principal-engineer/10170358

**Scores:**
- Autonomy: 9/10
"""
    urls = extract_source_url(description)
    assert len(urls) == 1
    assert urls[0] == "https://builtin.com/job/senior-principal-engineer/10170358"


test_extract_source_url_raw = """
Check out this job: https://example.com/careers/12345 for details.
"""


def test_extract_source_url_raw_link():
    urls = extract_source_url(test_extract_source_url_raw)
    assert len(urls) == 1
    assert "https://example.com/careers/12345" in urls[0]


def test_save_and_load_processed_links(tmp_path):
    filepath = str(tmp_path / "processed_links.txt")
    test_links = {"https://example.com/1", "https://example.com/2"}

    save_processed_links(filepath, test_links)
    loaded = load_existing_processed_links(filepath)

    assert loaded == test_links
