import json
import tempfile
import unittest
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

from mpc_keygroup_builder import drum_audit, drum_builder, drum_compose


class DrumComposeTests(unittest.TestCase):
    def test_repository_recipe_fills_all_eight_banks(self):
        root = Path(__file__).parents[1]
        recipe = drum_compose.load_recipe(root / "inventory/fg-vinyl-kit-banks.toml")
        self.assertEqual(recipe.name, "FG Vinyl Kit Banks 01")
        self.assertEqual([bank.target for bank in recipe.banks], list("ABCDEFGH"))

    def write_template(self, path: Path) -> None:
        pads = {f"value{index}": 0 for index in range(128)}
        root = ET.Element("MPCVObject")
        program = ET.SubElement(root, "Program", type="Drum")
        ET.SubElement(program, "ProgramName").text = "Template"
        ET.SubElement(program, "ProgramPads").text = json.dumps(
            {"ProgramPads": {"Universal": {"value0": True}, "Type": {"value0": 1}, "pads": pads}}
        )
        instruments = ET.SubElement(program, "Instruments")
        for number in range(1, 129):
            instrument = ET.SubElement(instruments, "Instrument", number=str(number))
            ET.SubElement(instrument, "Mono").text = "False"
            ET.SubElement(instrument, "Polyphony").text = "4"
            ET.SubElement(instrument, "MuteGroup").text = "0"
            ET.SubElement(instrument, "OneShot").text = "False"
            layers = ET.SubElement(instrument, "Layers")
            layer = ET.SubElement(layers, "Layer", number="1")
            for name in ("SampleName", "SampleFile", "SampleStart", "SampleEnd", "SliceStart", "SliceEnd"):
                ET.SubElement(layer, name).text = ""
        ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)

    def write_wav(self, path: Path) -> None:
        with wave.open(str(path), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(44100)
            stream.writeframes(b"\0\0" * 20)

    def build_source(self, root: Path) -> tuple[Path, Path]:
        template = root / "template.xpm"
        audio = root / "audio"
        source = root / "source"
        audio.mkdir()
        self.write_template(template)
        pads = []
        for bank_offset, prefix, source_group in ((0, "A", 7), (32, "C", 11)):
            for position in range(1, 17):
                if position == 5:
                    filename = f"CH {prefix} Hat.wav"
                elif position == 6:
                    filename = f"OH {prefix} Hat.wav"
                elif position <= 2:
                    filename = f"BD {prefix} {position}.wav"
                elif position <= 4:
                    filename = f"SD {prefix} {position}.wav"
                else:
                    filename = f"Perc {prefix} {position}.wav"
                self.write_wav(audio / filename)
                pads.append(
                    drum_builder.PadSpec(
                        bank_offset + position,
                        filename,
                        source_group if position in {5, 6} else 0,
                    )
                )
        drum_builder.build_drum_program(
            drum_builder.DrumManifest("Source", tuple(pads)), template, audio, source
        )
        return template, source

    def test_composes_and_rebases_complete_banks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template, source = self.build_source(root)
            recipe_path = root / "recipe.toml"
            recipe_path.write_text(
                'name = "Combined"\n'
                '[[banks]]\ntarget="A"\nsource="Source.xpm"\nbank="A"\nlabel="First"\n'
                '[[banks]]\ntarget="H"\nsource="Source.xpm"\nbank="C"\nlabel="Last"\n',
                encoding="utf-8",
            )
            recipe = drum_compose.load_recipe(recipe_path)
            manifest = drum_compose.compose_recipe(recipe, source)
            self.assertEqual(len(manifest.pads), 32)
            self.assertEqual([spec.pad for spec in manifest.pads[:16]], list(range(1, 17)))
            self.assertEqual([spec.pad for spec in manifest.pads[16:]], list(range(113, 129)))
            self.assertEqual(manifest.pads[4].mute_group, 1)
            self.assertEqual(manifest.pads[5].mute_group, 1)
            self.assertEqual(manifest.pads[20].mute_group, 8)
            self.assertEqual(manifest.pads[21].mute_group, 8)
            self.assertTrue(manifest.pads[4].sample.endswith(".wav"))

            rendered_path = root / "combined.toml"
            rendered_path.write_text(
                drum_compose.render_manifest(recipe, manifest), encoding="utf-8"
            )
            self.assertEqual(drum_builder.load_manifest(rendered_path), manifest)

            package = root / "package"
            destination = drum_builder.build_drum_program(manifest, template, source, package)
            report = drum_audit.audit_drum_program(destination)
            self.assertEqual(report["verdict"], "pass")
            self.assertEqual(report["populated_pads"], 32)
            self.assertEqual(report["mute_groups"], {"1": [5, 6], "8": [117, 118]})

    def test_rejects_duplicate_target_bank(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recipe.toml"
            path.write_text(
                'name="Bad"\n'
                '[[banks]]\ntarget="A"\nsource="One.xpm"\nbank="A"\nlabel="One"\n'
                '[[banks]]\ntarget="a"\nsource="Two.xpm"\nbank="B"\nlabel="Two"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate target bank A"):
                drum_compose.load_recipe(path)

    def test_rejects_incomplete_source_bank(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, source = self.build_source(root)
            recipe_path = root / "recipe.toml"
            recipe_path.write_text(
                'name="Bad"\n'
                '[[banks]]\ntarget="A"\nsource="Source.xpm"\nbank="B"\nlabel="Empty"\n',
                encoding="utf-8",
            )
            recipe = drum_compose.load_recipe(recipe_path)
            with self.assertRaisesRegex(ValueError, "must contain exactly pads 1 through 16"):
                drum_compose.compose_recipe(recipe, source)


if __name__ == "__main__":
    unittest.main()
