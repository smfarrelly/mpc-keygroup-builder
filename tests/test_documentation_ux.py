import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")
ONBOARDING_DOCUMENTS = (
    "README.md",
    "CONTRIBUTING.md",
    "docs/index.md",
    "docs/getting-started.md",
    "docs/cli-reference.md",
    "docs/troubleshooting.md",
    "docs/keygroup-building.md",
    "docs/browser-demo.md",
    "docs/sample-sources.md",
    "docs/vendor-documents.md",
)


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attributes):
        if tag == "a":
            href = dict(attributes).get("href")
            if href:
                self.hrefs.append(href)


class DocumentationUxTests(unittest.TestCase):
    def test_readme_is_a_front_door_and_local_onboarding_links_resolve(self):
        root = Path(__file__).resolve().parents[1]
        readme = root / "README.md"
        self.assertLess(len(readme.read_text(encoding="utf-8").splitlines()), 220)
        for relative in ONBOARDING_DOCUMENTS:
            document = root / relative
            self.assertTrue(document.is_file(), relative)
            for target in MARKDOWN_LINK.findall(document.read_text(encoding="utf-8")):
                if target.startswith(("https://", "http://", "#")):
                    continue
                target = target.split("#", 1)[0]
                self.assertTrue((document.parent / target).resolve().is_file(), f"{relative}: {target}")

    def test_offline_landing_page_links_to_existing_local_assets(self):
        root = Path(__file__).resolve().parents[1]
        page = root / "site/index.html"
        parser = _Links()
        parser.feed(page.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(parser.hrefs), 2)
        for href in parser.hrefs:
            self.assertFalse(href.startswith(("http://", "https://")))
            self.assertTrue((page.parent / href).resolve().is_file(), href)


if __name__ == "__main__":
    unittest.main()
