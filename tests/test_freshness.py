import contextlib
import hashlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mpc_keygroup_builder import freshness, workstation_wave
from mpc_keygroup_builder.entrypoints import invoke
from mpc_keygroup_builder.readiness import check


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.recipes = self.root / 'recipes'
        (self.recipes / 'drums').mkdir(parents=True)
        self.recipe = self.recipes / 'drums' / 'kit.toml'
        self.recipe.write_text('name="Original"\n')
        self.bundle = self.root / 'bundle'
        shutil.copytree(self.recipes, self.bundle / 'Recipes')
        (self.bundle / 'recipe-inputs.json').write_text(json.dumps(freshness.receipt(freshness.snapshot(self.recipes))))
        self.seal()

    def seal(self):
        hashes = {p.relative_to(self.bundle).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.bundle.rglob('*') if p.is_file() and p.name != 'checksums.json'}
        (self.bundle / 'checksums.json').write_text(json.dumps(hashes))

    def test_current_and_relocated_recipe_tree(self):
        moved = self.root / 'moved'
        shutil.copytree(self.recipes, moved)
        self.assertEqual(freshness.check_bundle(self.bundle, moved)['freshness'], 'current')

    def test_added_removed_changed_are_distinct(self):
        self.recipe.write_text('name="Changed"\n')
        (self.recipes / 'drums' / 'new.toml').write_text('name="New"')
        report = freshness.check_bundle(self.bundle, self.recipes)
        self.assertEqual(report['changed'], ['drums/kit.toml'])
        self.assertEqual(report['added'], ['drums/new.toml'])
        self.assertEqual(report['freshness'], 'stale')
        self.recipe.unlink()
        self.assertEqual(freshness.check_bundle(self.bundle, self.recipes)['removed'], ['drums/kit.toml'])

    def test_removing_all_recipes_is_stale(self):
        self.recipe.unlink()
        self.assertEqual(freshness.check_bundle(self.bundle, self.recipes)['freshness'], 'stale')

    def test_nonrecipe_files_do_not_change_fingerprint(self):
        before = freshness.snapshot(self.recipes)
        (self.recipes / 'notes.txt').write_text('notes')
        self.assertEqual(freshness.snapshot(self.recipes), before)

    def test_missing_receipt_is_unknown_not_current(self):
        (self.bundle / 'recipe-inputs.json').unlink()
        self.seal()
        self.assertEqual(freshness.check_bundle(self.bundle, self.recipes)['freshness'], 'unknown')

    def test_integrity_failure_precedes_freshness(self):
        (self.bundle / 'Recipes/drums/kit.toml').write_text('tampered')
        with self.assertRaises(ValueError):
            freshness.check_bundle(self.bundle, self.recipes)

    def test_inconsistent_receipt_rejected_even_with_new_checksums(self):
        (self.bundle / 'recipe-inputs.json').write_text('{}')
        self.seal()
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            freshness.check_bundle(self.bundle, self.recipes)

    def test_symlinks_and_special_files_rejected(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.recipes, target_is_directory=True)
        with self.assertRaises(ValueError):
            freshness.snapshot(alias)
        self.recipe.unlink()
        self.recipe.symlink_to(self.bundle / 'Recipes/drums/kit.toml')
        with self.assertRaises(ValueError):
            freshness.snapshot(self.recipes)

    def test_cli_status_and_no_write(self):
        self.recipe.write_text('changed')
        before = (self.bundle / 'checksums.json').read_bytes()
        with contextlib.redirect_stdout(io.StringIO()) as output:
            status = invoke('mpc-tools', ['check', '--bundle', str(self.bundle), '--recipe-root', str(self.recipes), '--json'])
        self.assertEqual(status, 1)
        self.assertEqual(json.loads(output.getvalue())['checks'][0]['detail']['freshness'], 'stale')
        self.assertEqual((self.bundle / 'checksums.json').read_bytes(), before)
        with self.assertRaises(ValueError):
            check(archives=[self.bundle], recipe_root=self.recipes)

    def test_wave_build_records_receipt_and_rejects_mutating_source(self):
        source = Path(__file__).resolve().parents[1] / 'recipes'
        tree = self.root / 'full-recipes'
        shutil.copytree(source, tree)
        output = self.root / 'wave'
        workstation_wave.build_wave(tree, output, families=('dusty',), seeds_per_family=1)
        self.assertEqual(freshness.check_bundle(output, tree)['freshness'], 'current')
        copy = workstation_wave._copy_recipes
        def mutate(root, stage, report):
            copy(root, stage, report)
            recipe = next((root / 'drums').glob('*.toml'))
            recipe.write_text(recipe.read_text() + '\n# concurrent edit\n')
        failed = self.root / 'failed-wave'
        with patch.object(workstation_wave, '_copy_recipes', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed during generation'):
                workstation_wave.build_wave(tree, failed, families=('dusty',), seeds_per_family=1)
        self.assertFalse(failed.exists())
        self.assertEqual(list(self.root.glob('.failed-wave.staging-*')), [])
