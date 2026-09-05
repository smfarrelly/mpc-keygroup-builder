import gzip
import tempfile
import unittest
import wave
from pathlib import Path

from mpc_keygroup_builder import ableton_drum, drum_builder


DRUM_XML = b'''<Ableton><GroupDevicePreset><Device><DrumGroupDevice>
  <UserName Value="Source Kit" /><Branches>
    <DrumBranchPreset><Name Value="Kick Pad" />
      <DevicePresets><InstrumentBranchPreset><Device><OriginalSimpler>
        <MultiSamplePart><Name Value="Kick" /><IsActive Value="true" />
          <VelocityRange><Min Value="1" /><Max Value="127" /></VelocityRange>
          <SampleRef><FileRef><RelativePath><RelativePathElement Dir="WAV" />
          </RelativePath><Name Value="Kick.wav" /></FileRef></SampleRef>
        </MultiSamplePart>
      </OriginalSimpler></Device></InstrumentBranchPreset></DevicePresets>
      <ZoneSettings><ReceivingNote Value="60" /><SendingNote Value="36" />
        <ChokeGroup Value="0" /></ZoneSettings>
    </DrumBranchPreset>
    <DrumBranchPreset><Name Value="Hat Pad" />
      <DevicePresets><InstrumentBranchPreset><Device><OriginalSimpler>
        <MultiSamplePart><Name Value="Hat" /><IsActive Value="true" />
          <VelocityRange><Min Value="1" /><Max Value="127" /></VelocityRange>
          <SampleRef><FileRef><RelativePath><RelativePathElement Dir="WAV" />
          </RelativePath><Name Value="Hat.wav" /></FileRef></SampleRef>
        </MultiSamplePart>
      </OriginalSimpler></Device></InstrumentBranchPreset></DevicePresets>
      <ZoneSettings><ReceivingNote Value="59" /><SendingNote Value="36" />
        <ChokeGroup Value="3" /></ZoneSettings>
    </DrumBranchPreset>
  </Branches>
</DrumGroupDevice></Device></GroupDevicePreset></Ableton>'''


class AbletonDrumTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path]:
        pack = root / "Pack"
        samples = pack / "WAV"
        samples.mkdir(parents=True)
        for name in ("Kick.wav", "Hat.wav"):
            with wave.open(str(samples / name), "wb") as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(44100)
                stream.writeframes(b"\0\0" * 20)
        preset = pack / "Kit.adg"
        with gzip.open(preset, "wb") as stream:
            stream.write(DRUM_XML)
        return pack, preset

    def test_plans_document_order_and_preserves_choke_group(self):
        with tempfile.TemporaryDirectory() as directory:
            pack, preset = self.fixture(Path(directory))
            plan = ableton_drum.plan_conversion(preset, pack, name="MPC Kit")
            self.assertEqual(plan.receiving_notes, (60, 59))
            self.assertEqual(
                plan.manifest.pads,
                (
                    drum_builder.PadSpec(pad=1, sample="Kick.wav"),
                    drum_builder.PadSpec(pad=2, sample="Hat.wav", mute_group=3),
                ),
            )
            self.assertEqual(set(plan.samples), {"Kick.wav", "Hat.wav"})

    def test_rendered_manifest_round_trips_through_drum_builder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack, preset = self.fixture(root)
            plan = ableton_drum.plan_conversion(preset, pack, name="MPC Kit")
            manifest_path = root / "manifest.toml"
            manifest_path.write_text(ableton_drum.render_manifest(plan), encoding="utf-8")
            self.assertEqual(drum_builder.load_manifest(manifest_path), plan.manifest)

    def test_missing_referenced_sample_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pack, preset = self.fixture(root)
            (pack / "WAV/Hat.wav").unlink()
            with self.assertRaises(FileNotFoundError):
                ableton_drum.plan_conversion(preset, pack)

    def test_batch_recipe_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe = root / "recipe.toml"
            recipe.write_text(
                'name="Bad"\n[[programs]]\nid="bad"\nname="Bad"\ncollection="Bad"\n'
                'preset="../outside.adg"\npack_root="Pack"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "escapes"):
                ableton_drum.load_recipe(recipe, root)

    def test_batch_recipe_rejects_non_table_entries_as_validation_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recipe = root / "recipe.toml"
            recipe.write_text('name="Bad"\nprograms=[1]\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "entry 1 is not a table"):
                ableton_drum.load_recipe(recipe, root)

    def test_batch_plan_retains_translation_warning_field(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            recipe = root / "recipe.toml"
            recipe.write_text(
                'name="Wave"\n[[programs]]\nid="kit"\nname="MPC Kit"\n'
                'collection="Tests"\npreset="Pack/Kit.adg"\npack_root="Pack"\n',
                encoding="utf-8",
            )
            report = ableton_drum.plan_batch(recipe, root)
            self.assertEqual(len(report["programs"]), 1)
            self.assertIn("translation_warnings", report["programs"][0])


if __name__ == "__main__":
    unittest.main()
