"""Offline browser fixture and CLI contract for the bundled parameter page."""

from html.parser import HTMLParser
import json
from pathlib import Path
import unittest

from mpc_keygroup_builder import plugin_map, plugin_params


ROOT = Path(__file__).resolve().parents[1]


class Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.data_script = False
        self.data = ""
        self.sources = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "script":
            self.data_script = attrs.get("id") == "bundled-dump"
            if "src" in attrs:
                self.sources.append(attrs["src"])

    def handle_data(self, data):
        if self.data_script:
            self.data += data

    def handle_endtag(self, tag):
        if tag == "script":
            self.data_script = False


class SDKBrowserTests(unittest.TestCase):
    def test_page_starts_with_current_plugin_metadata(self):
        path = ROOT / "site/sdk-mapping.html"
        parser = Scripts()
        parser.feed(path.read_text(encoding="utf-8"))
        reference = ROOT / "plugins/LoopThrow/params.reference.json"
        self.assertEqual(json.loads(parser.data), json.loads(reference.read_text()))
        self.assertEqual(parser.sources, ["sdk-mapping.js"])
        self.assertTrue(path.with_name(parser.sources[0]).is_file())
        profile = plugin_map.load_profile(ROOT / "midi/sdk-examples/loop-throw.toml")
        self.assertFalse(plugin_map.validate_profile(profile, plugin_params.catalog(reference))["errors"])
