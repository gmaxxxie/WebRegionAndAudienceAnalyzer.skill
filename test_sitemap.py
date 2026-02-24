#!/usr/bin/env python3
"""
Test script for sitemap discovery functionality.
"""
import json
import sys
import os

# Add the script directory to the path
script_dir = os.path.join(os.path.dirname(__file__), 'web-region-audience-analyzer', 'scripts')
sys.path.insert(0, script_dir)

from analyze_webpage import (
    discover_sitemap,
    extract_navigation_links,
)


def test_sitemap_discovery():
    """Test sitemap discovery on real sites."""
    print("=" * 60)
    print("Test 1: Sitemap Discovery")
    print("=" * 60)

    # Test sites known to have sitemaps
    test_sites = [
        'https://www.example.com',
        'https://github.com',
    ]

    for site in test_sites:
        print(f"\nTesting: {site}")
        result = discover_sitemap(site, max_pages=10)

        print(f"  Sitemap URL: {result['sitemap_url']}")
        print(f"  Source: {result['source']}")
        print(f"  URLs found: {len(result['urls'])}")

        if result['urls']:
            print(f"  Sample URLs:")
            for url in result['urls'][:3]:
                print(f"    - {url}")

    print("\n✓ Sitemap discovery test completed\n")


def test_navigation_extraction():
    """Test navigation link extraction."""
    print("=" * 60)
    print("Test 2: Navigation Link Extraction")
    print("=" * 60)

    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Site</title></head>
    <body>
        <header>
            <nav>
                <a href="/">Home</a>
                <a href="/products">Products</a>
                <a href="/about">About</a>
                <a href="/contact">Contact</a>
            </nav>
        </header>
        <main>
            <a href="/blog/post-1">Blog Post 1</a>
            <a href="/blog/post-2">Blog Post 2</a>
        </main>
    </body>
    </html>
    """

    nav_links = extract_navigation_links(html, "https://example.com")

    print(f"Extracted {len(nav_links)} navigation links:")
    for link in nav_links:
        print(f"  - {link['path']}: {link['text']} (source: {link['source']})")

    assert len(nav_links) >= 4, "Should extract at least 4 navigation links"
    assert any('/products' in link['path'] for link in nav_links), "Should include products link"
    assert all(link['source'] == 'navigation' for link in nav_links), "All links should be from navigation"

    print("✓ Navigation extraction test passed\n")


def test_navigation_fallback():
    """Test fallback to regular links when no navigation found."""
    print("=" * 60)
    print("Test 3: Navigation Fallback")
    print("=" * 60)

    html = """
    <!DOCTYPE html>
    <html>
    <body>
        <a href="/">Home</a>
        <a href="/page1">Page 1</a>
        <a href="/page2">Page 2</a>
    </body>
    </html>
    """

    nav_links = extract_navigation_links(html, "https://example.com")

    print(f"Extracted {len(nav_links)} navigation links:")
    for link in nav_links:
        print(f"  - {link['path']}: {link['text']}")

    # Should find some links even without proper navigation structure
    # (depends on implementation)
    print("✓ Navigation fallback test completed\n")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Sitemap & Navigation Tests")
    print("=" * 60 + "\n")

    try:
        test_navigation_extraction()
        test_navigation_fallback()

        print("=" * 60)
        print("Running sitemap discovery test...")
        print("(This may take a moment as it fetches real sites)")
        print("=" * 60)
        test_sitemap_discovery()

        print("=" * 60)
        print("All tests completed! ✓")
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
