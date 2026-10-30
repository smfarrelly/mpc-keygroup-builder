import json
import tempfile
import unittest
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

from mpc_keygroup_builder import drum_builder
from mpc_keygroup_builder import model


class DrumBuilderTests(unittest.TestCase):
    def test_program_name_cannot_escape_output_or_use_reserved_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'recipe.toml'
            for name in ('../outside', '/tmp/outside', 'C:\\outside', 'Kit/Child', 'bad\nname', 'NUL', 'COM1.test'):
                with self.subTest(name=name):
                    path.write_text('name='+json.dumps(name)+'\n[[pads]]\npad=1\nsample="Hit.wav"\n')
                    with self.assertRaisesRegex(ValueError, 'portable filename'):
                        drum_builder.load_manifest(path)
                    manifest = drum_builder.DrumManifest(name, (drum_builder.PadSpec(1,'Hit.wav'),))
                    with self.assertRaisesRegex(ValueError, 'portable filename'):
                        drum_builder.build_drum_program(manifest, root/'not-read.xpm', root, root/'out')
                    self.assertFalse((root/'out').exists())
            for name in ("Fisherman'sFriend", 'Mécanique 01', 'Drums (Warm)'):
                self.assertEqual(drum_builder.validate_program_name(name), name)

    def test_sample_cannot_be_overwritten_by_generated_program(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = drum_builder.DrumManifest('Kit', (drum_builder.PadSpec(1, 'KIT.XPM'),))
            with self.assertRaisesRegex(ValueError, 'collides with output program'):
                drum_builder.build_drum_program(manifest, root/'not-read.xpm', root, root/'out')
            self.assertFalse((root/'out').exists())

    def test_source_map_packages_distinct_same_basename_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source'
            for subfolder, frames in [('Clean', 20), ('Tube', 30)]:
                (source/subfolder).mkdir(parents=True)
                self.write_wav(source/subfolder/'tone.wav', frames)
            path = root/'recipe.toml'
            path.write_text('name="Mapped"\n[sources]\n"Clean.wav"="Clean/tone.wav"\n'
                            '"Tube.wav"="Tube/tone.wav"\n[[pads]]\npad=1\ncolor_category="fx"\n'
                            'layers=[{sample="Clean.wav",velocity_start=0,velocity_end=63},'
                            '{sample="Tube.wav",velocity_start=64,velocity_end=127}]\n')
            manifest = drum_builder.load_manifest(path)
            template = root/'template.xpm'
            self.write_template(template)
            destination = drum_builder.build_drum_program(manifest, template, source, root/'out')
            for alias, relative in manifest.sources.items():
                self.assertEqual((destination.parent/alias).read_bytes(), (source/relative).read_bytes())
            generated = model.from_xpm(destination)
            self.assertEqual([x.sample for x in generated.zones[0].layers], ['Clean.wav','Tube.wav'])
            self.assertEqual([x.sample_end for x in generated.zones[0].layers], [19,29])
            self.assertEqual(model.from_drum_manifest(path, source).zones[0].color, 0x8000FF)

    def test_source_map_rejects_escape_paths_and_case_collisions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'recipe.toml'
            for relative in ('../outside.wav', '/outside.wav', 'C:\\outside.wav', '.'):
                path.write_text('name="Unsafe"\n[sources]\n"A.wav"='+json.dumps(relative)+'\n'
                                '[[pads]]\npad=1\nsample="A.wav"\n')
                with self.subTest(relative=relative), self.assertRaisesRegex(ValueError, 'relative source path'):
                    drum_builder.load_manifest(path)
            path.write_text('name="Collision"\n[[pads]]\npad=1\nsample="A.wav"\n'
                            '[[pads]]\npad=2\nsample="a.wav"\n')
            with self.assertRaisesRegex(ValueError,'case-colliding'):
                drum_builder.load_manifest(path)

    def test_source_map_rejects_symlink_escape_before_package_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'source'
            source.mkdir()
            outside = root/'outside.wav'
            self.write_wav(outside)
            try:
                (source/'linked.wav').symlink_to(outside)
            except OSError as error:
                self.skipTest(str(error))
            template = root/'template.xpm'
            self.write_template(template)
            manifest = drum_builder.DrumManifest('Unsafe',(drum_builder.PadSpec(1,'Alias.wav'),),
                                                  sources={'Alias.wav':'linked.wav'})
            with self.assertRaisesRegex(ValueError,'escapes source root'):
                drum_builder.build_drum_program(manifest, template, source, root/'out')
            self.assertFalse((root/'out').exists())

    def test_source_map_inheritance_is_explicit_and_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'base.toml').write_text('name="Base"\n[sources]\n"A.wav"="Clean/A.wav"\n'
                                         '[[pads]]\npad=1\nsample="A.wav"\n')
            child = root/'child.toml'
            child.write_text('extends="base.toml"\nname="Child"\n[sources]\n"A.wav"="Tube/A.wav"\n')
            self.assertEqual(drum_builder.load_manifest(child).sources, {'A.wav':'Tube/A.wav'})
            self.assertEqual(drum_builder.load_manifest(root/'base.toml').sources, {'A.wav':'Clean/A.wav'})

    def test_transition_recipe_builds_declared_colors_without_postprocessing(self):
        recipe = Path(__file__).resolve().parents[1] / "inventory/fg-found-transitions-01.toml"
        manifest = drum_builder.load_manifest(recipe)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "template.xpm"
            self.write_template(template)
            for pad in manifest.pads:
                self.write_wav(root / pad.sample)
            destination = drum_builder.build_drum_program(manifest, template, root, root / "out")
            actual = model.from_xpm(destination)
            planned = model.from_drum_manifest(recipe)
            self.assertEqual(len(actual.zones), 8)
            self.assertEqual([z.color for z in actual.zones], [0x8000FF] * 8)
            self.assertEqual([z.color for z in planned.zones], [z.color for z in actual.zones])
            self.assertEqual([z.mute_group for z in actual.zones], [0] * 4 + [1] * 4)
            for pad in manifest.pads:
                self.assertEqual((root / pad.sample).read_bytes(), (destination.parent / pad.sample).read_bytes())
            settings = json.loads(ET.parse(destination).findtext("./Program/ProgramPads"))["ProgramPads"]
            self.assertTrue(all(settings["pads"][f"value{i}"] == 0 for i in range(8, 128)))

    def test_rejects_invalid_color_category_with_context(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.toml"
            for value in ('"purple"', '""', 'false', '17', '["fx"]'):
                with self.subTest(value=value):
                    path.write_text('name="Bad"\n[[pads]]\npad=1\nsample="A.wav"\ncolor_category=' + value)
                    with self.assertRaisesRegex(ValueError, "pads entry 1 has invalid color_category"):
                        drum_builder.load_manifest(path)

    def test_inherited_layered_pad_preserves_explicit_color(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "base.toml").write_text(
                'name="Base"\n[[pads]]\npad=1\ncolor_category="fx"\n'
                'layers=[{sample="BD Soft.wav",velocity_start=0,velocity_end=63},'
                '{sample="BD Hard.wav",velocity_start=64,velocity_end=127}]\n'
            )
            child = root / "child.toml"
            child.write_text('extends="base.toml"\nname="Child"\n[[pads]]\npad=2\nsample="BD Auto.wav"\n')
            program = model.from_drum_manifest(child)
            self.assertEqual([z.color for z in program.zones], [0x8000FF, 0xFF0000])
            self.assertEqual(len(program.zones[0].layers), 2)

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
                '[[pads]]\npad = 1\nsample = "Bongo Test.wav"\nmute_group = 3\n'
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
            self.assertEqual(first.findtext("MuteGroup"), "3")
            self.assertEqual(second.findtext("./Layers/Layer/SampleFile"), "")
            self.assertEqual(seventeenth.findtext("./Layers/Layer/SliceEnd"), "29")
            self.assertEqual(seventeenth.findtext("MuteGroup"), "0")
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

    def test_rejects_invalid_mute_group(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.toml"
            path.write_text(
                'name="Bad"\n[[pads]]\npad=1\nsample="Hat.wav"\nmute_group=33\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "invalid mute_group 33"):
                drum_builder.load_manifest(path)

    def test_builds_explicit_velocity_layers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "template.xpm"
            source = root / "samples"
            output = root / "output"
            source.mkdir()
            self.write_template(template)
            self.write_wav(source / "BD Soft.wav", 10)
            self.write_wav(source / "BD Hard.wav", 30)
            manifest_path = root / "manifest.toml"
            manifest_path.write_text(
                'name="Layered"\n[[pads]]\npad=1\n'
                '[[pads.layers]]\nsample="BD Soft.wav"\nvelocity_start=0\nvelocity_end=63\n'
                '[[pads.layers]]\nsample="BD Hard.wav"\nvelocity_start=64\nvelocity_end=127\n',
                encoding="utf-8",
            )
            manifest = drum_builder.load_manifest(manifest_path)
            self.assertEqual(
                manifest.pads[0].layers,
                (
                    drum_builder.LayerSpec("BD Soft.wav", 0, 63),
                    drum_builder.LayerSpec("BD Hard.wav", 64, 127),
                ),
            )
            destination = drum_builder.build_drum_program(manifest, template, source, output)
            instrument = ET.parse(destination).getroot().find(
                './Program/Instruments/Instrument[@number="1"]'
            )
            layers = instrument.findall("./Layers/Layer")
            self.assertEqual(layers[0].findtext("SampleFile"), "BD Soft.wav")
            self.assertEqual(layers[0].findtext("VelStart"), "0")
            self.assertEqual(layers[0].findtext("VelEnd"), "63")
            self.assertEqual(layers[1].findtext("SampleFile"), "BD Hard.wav")
            self.assertEqual(layers[1].findtext("VelStart"), "64")
            self.assertEqual(layers[1].findtext("VelEnd"), "127")
            self.assertEqual(layers[0].findtext("Active"), "True")
            self.assertEqual(layers[1].findtext("Active"), "True")
            self.assertEqual((output / "BD Soft.wav").is_file(), True)
            self.assertEqual((output / "BD Hard.wav").is_file(), True)

    def test_rejects_gapped_or_overlapping_velocity_layers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, second_start in (("gap", 65), ("overlap", 63)):
                path = root / f"{name}.toml"
                path.write_text(
                    'name="Bad"\n[[pads]]\npad=1\n'
                    '[[pads.layers]]\nsample="Soft.wav"\nvelocity_start=0\nvelocity_end=63\n'
                    f'[[pads.layers]]\nsample="Hard.wav"\nvelocity_start={second_start}\nvelocity_end=127\n',
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(ValueError, "without gaps or overlaps"):
                    drum_builder.load_manifest(path)

    def test_rejects_more_than_four_velocity_layers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.toml"
            layers = []
            for index, (start, end) in enumerate(((0, 24), (25, 49), (50, 74), (75, 99), (100, 127))):
                layers.append(
                    f'[[pads.layers]]\nsample="Layer {index}.wav"\n'
                    f'velocity_start={start}\nvelocity_end={end}\n'
                )
            path.write_text('name="Bad"\n[[pads]]\npad=1\n' + "".join(layers), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "one through four"):
                drum_builder.load_manifest(path)

    def test_extends_a_base_manifest_with_additional_banks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "base.toml").write_text(
                'name="Base"\n[[pads]]\npad=1\nsample="Bongo.wav"\n',
                encoding="utf-8",
            )
            child = root / "expanded.toml"
            child.write_text(
                'name="Expanded"\nextends="base.toml"\n'
                '[[pads]]\npad=17\nsample="FX.wav"\n',
                encoding="utf-8",
            )
            manifest = drum_builder.load_manifest(child)
            self.assertEqual(manifest.name, "Expanded")
            self.assertEqual(
                manifest.pads,
                (
                    drum_builder.PadSpec(pad=1, sample="Bongo.wav"),
                    drum_builder.PadSpec(pad=17, sample="FX.wav"),
                ),
            )

    def test_rejects_an_inherited_pad_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "base.toml").write_text(
                'name="Base"\n[[pads]]\npad=1\nsample="Bongo.wav"\n',
                encoding="utf-8",
            )
            child = root / "expanded.toml"
            child.write_text(
                'name="Expanded"\nextends="base.toml"\n'
                '[[pads]]\npad=1\nsample="FX.wav"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate pad 1"):
                drum_builder.load_manifest(child)

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

    def test_rejects_programmatic_pad_without_a_sample_layer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "template.xpm"
            source = root / "samples"
            source.mkdir()
            self.write_template(template)
            manifest = drum_builder.DrumManifest(
                name="Bad", pads=(drum_builder.PadSpec(pad=1),)
            )
            with self.assertRaisesRegex(ValueError, "pad 1 has no sample layers"):
                drum_builder.build_drum_program(manifest, template, source, root / "output")


if __name__ == "__main__":
    unittest.main()
