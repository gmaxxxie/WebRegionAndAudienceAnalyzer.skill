#!/usr/bin/env python3
"""
Test script for smart crawl functionality.
Run without AI credentials to test heuristic fallback.
"""
import json
import sys
import os

# Add the script directory to the path
script_dir = os.path.join(os.path.dirname(__file__), 'web-region-audience-analyzer', 'scripts')
sys.path.insert(0, script_dir)

from analyze_webpage import (
    extract_links_with_metadata,
    select_pages_heuristically,
    _normalize_url,
)

def test_link_extraction():
    """Test link extraction with metadata."""
    print("=" * 60)
    print("Test 1: Link Extraction with Metadata")
    print("=" * 60)

    html = """
    <html>
    <body>
        <a href="/products">Products</a>
        <a href="/about-us" title="About Us">About</a>
        <a href="/contact">Contact Us</a>
        <a href="/blog/post-123">Latest Post</a>
        <a href="/privacy">Privacy Policy</a>
        <a href="https://example.com">Home</a>
    </body>
    </html>
    """

    links = extract_links_with_metadata(html, "https://example.com")

    print(f"Extracted {len(links)} links:")
    for link in links[:5]:
        print(f"  - {link['path']}: {link['text'] or link['title']}")

    assert len(links) > 0, "Should extract at least one link"
    assert any('/products' in link['path'] for link in links), "Should include /products"
    print("✓ Link extraction test passed\n")


def test_heuristic_selection():
    """Test heuristic page selection."""
    print("=" * 60)
    print("Test 2: Heuristic Page Selection")
    print("=" * 60)

    links = [
        {'url': 'https://example.com/', 'text': 'Home', 'title': '', 'path': '/'},
        {'url': 'https://example.com/products', 'text': 'Products', 'title': '', 'path': '/products'},
        {'url': 'https://example.com/about', 'text': 'About', 'title': '', 'path': '/about'},
        {'url': 'https://example.com/contact', 'text': 'Contact', 'title': '', 'path': '/contact'},
        {'url': 'https://example.com/privacy', 'text': 'Privacy', 'title': '', 'path': '/privacy'},
        {'url': 'https://example.com/terms', 'text': 'Terms', 'title': '', 'path': '/terms'},
        {'url': 'https://example.com/blog/post-1', 'text': 'Post 1', 'title': '', 'path': '/blog/post-1'},
        {'url': 'https://example.com/blog/post-2', 'text': 'Post 2', 'title': '', 'path': '/blog/post-2'},
        {'url': 'https://example.com/help/faq', 'text': 'FAQ', 'title': '', 'path': '/help/faq'},
        {'url': 'https://example.com/pricing', 'text': 'Pricing', 'title': '', 'path': '/pricing'},
    ]

    selected = select_pages_heuristically(links, max_pages=5)

    print(f"Selected {len(selected)} pages out of {len(links)}:")
    for url in selected:
        print(f"  - {url}")

    assert len(selected) == 5, "Should select exactly 5 pages"
    assert 'https://example.com/' in selected, "Should include home page"
    assert 'https://example.com/products' in selected, "Should include products"
    assert 'https://example.com/privacy' not in selected, "Should NOT include privacy policy"
    print("✓ Heuristic selection test passed\n")


def test_url_normalization():
    """Test URL normalization."""
    print("=" * 60)
    print("Test 3: URL Normalization")
    print("=" * 60)

    test_cases = [
        ("https://example.com/path/", "https://example.com/path"),
        ("https://example.com/path#section", "https://example.com/path"),
        ("https://example.com/", "https://example.com/"),
    ]

    for input_url, expected in test_cases:
        result = _normalize_url(input_url)
        status = "✓" if result == expected else "✗"
        print(f"{status} {input_url} → {result}")
        assert result == expected, f"Expected {expected}, got {result}"

    print("✓ URL normalization test passed\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Smart Crawl Functionality Tests")
    print("=" * 60 + "\n")

    try:
        test_link_extraction()
        test_heuristic_selection()
        test_url_normalization()

        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
