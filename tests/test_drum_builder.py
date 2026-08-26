import json
import tempfile
import unittest
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

from mpc_keygroup_builder import drum_builder


class DrumBuilderTests(unittest.TestCase):
    def write_template(self, path: Path) -> None:
        pads = {f"value{index}": 123 for index in range(128)}
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
            ET.SubElement(instrument, "MuteGroup").text = "7"
            ET.SubElement(instrument, "OneShot").text = "False"
            layers = ET.SubElement(instrument, "Layers")
            for layer_number in range(1, 3):
                layer = ET.SubElement(layers, "Layer", number=str(layer_number))
                ET.SubElement(layer, "SampleName").text = "Old"
                ET.SubElement(layer, "SampleFile").text = "Old.wav"
                ET.SubElement(layer, "SampleStart").text = "0"
                ET.SubElement(layer, "SampleEnd").text = "99"
                ET.SubElement(layer, "SliceStart").text = "0"
                ET.SubElement(layer, "SliceEnd").text = "99"
        ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)

    def write_wav(self, path: Path, frames: int = 20) -> None:
        with wave.open(str(path), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(44100)
            stream.writeframes(b"\0\0" * frames)

    def test_builds_self_contained_colored_one_shot_program(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "template.xpm"
            source = root / "samples"
            output = root / "output"
            source.mkdir()
            self.write_template(template)
            self.write_wav(source / "Bongo Test.wav")
            self.write_wav(source / "FX Test.wav", 30)
            manifest_path = root / "manifest.toml"
            manifest_path.write_text(
                'name = "FG Shots"\n'
                '[[pads]]\npad = 1\nsample = "Bongo Test.wav"\n'
                '[[pads]]\npad = 17\nsample = "FX Test.wav"\n',
                encoding="utf-8",
            )
            manifest = drum_builder.load_manifest(manifest_path)
            destination = drum_builder.build_drum_program(manifest, template, source, output)
            self.assertTrue((output / "Bongo Test.wav").is_file())
            self.assertTrue((output / "FX Test.wav").is_file())
            program = ET.parse(destination).getroot().find("Program")
            self.assertEqual(program.findtext("ProgramName"), "FG Shots")
            first = program.find('./Instruments/Instrument[@number="1"]')
            second = program.find('./Instruments/Instrument[@number="2"]')
            seventeenth = program.find('./Instruments/Instrument[@number="17"]')
            self.assertEqual(first.findtext("./Layers/Layer/SampleFile"), "Bongo Test.wav")
            self.assertEqual(first.findtext("./Layers/Layer/SliceEnd"), "19")
            self.assertEqual(first.findtext("OneShot"), "True")
            self.assertEqual(second.findtext("./Layers/Layer/SampleFile"), "")
            self.assertEqual(seventeenth.findtext("./Layers/Layer/SliceEnd"), "29")
            settings = json.loads(program.findtext("ProgramPads"))["ProgramPads"]
            self.assertFalse(settings["Universal"]["value0"])
            self.assertEqual(settings["Type"]["value0"], 2)
            self.assertEqual(settings["pads"]["value0"], 0x00A080)
            self.assertEqual(settings["pads"]["value1"], 0)
            self.assertEqual(settings["pads"]["value16"], 0x8000FF)

    def test_rejects_duplicate_pads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.toml"
            path.write_text(
                'name="Bad"\n[[pads]]\npad=1\nsample="A.wav"\n'
                '[[pads]]\npad=1\nsample="B.wav"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate pad 1"):
                drum_builder.load_manifest(path)

    def test_refuses_nonempty_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "template.xpm"
            source = root / "samples"
            output = root / "output"
            source.mkdir()
            output.mkdir()
            (output / "keep.txt").write_text("user data", encoding="utf-8")
            self.write_template(template)
            self.write_wav(source / "Bongo Test.wav")
            manifest = drum_builder.DrumManifest(
                name="FG Shots",
                pads=(drum_builder.PadSpec(pad=1, sample="Bongo Test.wav"),),
            )
            with self.assertRaisesRegex(FileExistsError, "not empty"):
                drum_builder.build_drum_program(manifest, template, source, output)
            self.assertEqual((output / "keep.txt").read_text(), "user data")


if __name__ == "__main__":
    unittest.main()
