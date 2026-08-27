import gzip
import tempfile
import unittest
from pathlib import Path

from mpc_keygroup_builder import ableton


ABLETON_XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<Ableton MajorVersion="5" MinorVersion="11.3" Creator="Ableton Live 11">
  <GroupDevicePreset><Device><InstrumentGroupDevice>
    <UserName Value="Dust Rack" />
    <MacroDisplayNames.0 Value="Tone" />
    <MacroDisplayNames.1 Value="Macro 2" />
    <Branches><InstrumentBranchPreset><Name Value="Main" />
      <Device><OriginalSimpler><UserName Value="Sampler" />
        <MultiSamplePart>
          <Name Value="Kick Zone" /><RootKey Value="36" />
          <KeyRange><Min Value="36" /><Max Value="36" /></KeyRange>
          <VelocityRange><Min Value="1" /><Max Value="127" /></VelocityRange>
          <SampleStart Value="10" /><SampleEnd Value="1000" />
          <SustainLoop><Mode Value="1" /><Start Value="100" /><End Value="900" /></SustainLoop>
          <SampleRef><FileRef><RelativePath>
            <RelativePathElement Dir="Samples" />
          </RelativePath><Name Value="Kick.wav" /><FileSize Value="1234" /></FileRef></SampleRef>
          <SampleWarpProperties><IsWarped Value="false" /></SampleWarpProperties>
        </MultiSamplePart>
      </OriginalSimpler></Device>
    </InstrumentBranchPreset></Branches>
  </InstrumentGroupDevice></Device></GroupDevicePreset>
</Ableton>'''


class AbletonInspectorTests(unittest.TestCase):
    def write(self, path: Path, content: bytes = ABLETON_XML, compressed: bool = True) -> None:
        if compressed:
            with gzip.open(path, "wb") as stream:
                stream.write(content)
        else:
            path.write_bytes(content)

    def test_inspects_gzip_rack_intent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Dust Rack.adg"
            self.write(path)
            report = ableton.inspect(path)
            self.assertEqual(report["name"], "Dust Rack")
            self.assertEqual(report["device_types"], {"InstrumentGroupDevice": 1, "OriginalSimpler": 1})
            self.assertEqual(report["macros"], [{"index": 1, "name": "Tone"}])
            self.assertEqual(report["summary"]["zones"], 1)
            zone = report["zones"][0]
            self.assertEqual(zone["rootkey"], 36)
            self.assertEqual(zone["sample"]["relative_path"], "Samples/Kick.wav")
            self.assertEqual(zone["sustain_loop"]["mode"], 1)
            self.assertEqual(report["suggested_fidelity"]["grade"], "B")

    def test_reads_uncompressed_als_and_direct_fidelity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Simple.als"
            xml = ABLETON_XML.replace(b'<MacroDisplayNames.0 Value="Tone" />', b"")
            self.write(path, xml, compressed=False)
            report = ableton.inspect(path)
            self.assertEqual(report["kind"], "als")
            self.assertEqual(report["suggested_fidelity"]["grade"], "A")

    def test_inventory_skips_macos_metadata_and_reports_bad_xml(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root / "Good.adg")
            self.write(root / "._Good.adg", b"metadata", compressed=False)
            (root / "Bad.adg").write_bytes(b"not xml")
            report = ableton.inventory(root)
            self.assertEqual(report["count"], 1)
            self.assertEqual(len(report["issues"]), 1)
            self.assertEqual(report["fidelity_grades"], {"B": 1})

    def test_plugin_device_is_reference_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Plugin.adg"
            xml = b'<Ableton><Device><PluginDevice><UserName Value="Third Party" /></PluginDevice></Device></Ableton>'
            self.write(path, xml)
            report = ableton.inspect(path)
            self.assertEqual(report["suggested_fidelity"]["grade"], "D")
            self.assertEqual(report["suggested_fidelity"]["label"], "reference-only")

    def test_finds_live_set_devices_stored_directly_in_devices_container(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Set.als"
            xml = b'''<Ableton><LiveSet><Tracks><MidiTrack><DeviceChain>
                <Devices><DrumGroupDevice><UserName Value="Kit" /></DrumGroupDevice>
                <Compressor2><UserName Value="Glue" /></Compressor2></Devices>
                </DeviceChain></MidiTrack></Tracks></LiveSet></Ableton>'''
            self.write(path, xml)
            report = ableton.inspect(path)
            self.assertEqual(report["device_types"], {"Compressor2": 1, "DrumGroupDevice": 1})


if __name__ == "__main__":
    unittest.main()
