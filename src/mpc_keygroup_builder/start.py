"""Goal-based, offline workflow guidance. Prints instructions; never runs them."""

import json


WORKFLOWS = {
    'find': {
        'title': 'Find an instrument you already liked',
        'command': 'mpc-library inventory/program-status.csv --favorite yes',
        'needs': 'Local checkout and its listening ledger; no card required.',
        'next': 'Use the reported program path when the matching library is available. The ledger is historical evidence, not proof that a file exists today.',
        'guide': 'docs/catalog.md',
    },
    'capture': {
        'title': 'Preserve a saved musical idea',
        'command': 'mpc-project-capture "/path/to/projects" --project "Idea.xpj" --output "work/ideas/take-01" --dry-run --json',
        'needs': 'A saved XPJ with its companion ProjectData folder on accessible local storage.',
        'next': 'Replace the example paths, review the preview, then remove --dry-run --json and add --note "What to keep" to capture. Stop editing the source while copying.',
        'guide': 'docs/idea-snapshots.md',
    },
    'experiment': {
        'title': 'Try a variation without losing the original',
        'command': 'mpc-idea-archive restore "work/ideas/take-01" --output "work/experiments/take-02" --dry-run',
        'needs': 'A verified local archive; the original card can be disconnected.',
        'next': 'Remove --dry-run to create an independent copy. Edit that copy, then capture it as a new archive; do not rewrite the original checksums.',
        'guide': 'docs/idea-snapshots.md',
    },
    'groove': {
        'title': 'Hear drum grooves and save one as MIDI',
        'command': 'mpc-drum-session "/path/to/Kit.xpm" recipes/drums/dusty-pocket.toml recipes/drums/funk-machine.toml --tempo 96 --output work/drum-session-01',
        'needs': 'An XML Drum Program with its referenced WAV files and the pattern recipes from the checkout.',
        'next': 'Open work/drum-session-01/index.html. Play the loops and download the MIDI for the groove you want.',
        'guide': 'docs/drum-ideas.md',
    },
    'sdk': {
        'title': 'Design a plugin encoder page on this computer',
        'command': 'mpc-plugin-map check midi/sdk-examples/loop-throw.toml --sdk-dump plugins/LoopThrow/params.reference.json',
        'needs': 'Toolkit checkout. The reference dump is included.',
        'next': 'Open site/sdk-mapping.html to choose encoders, or generate a companion from the validated page.',
        'guide': 'docs/akai-sdk.md',
    },
    'prepare': {
        'title': 'Plan a card update without applying it',
        'command': 'mpc-package-deploy "/path/to/local/package" "/path/to/card/NewPackage"',
        'needs': 'An explicit local package and an explicitly identified destination. This step reads both; it does not auto-discover a card.',
        'next': 'Review the plan and verify sample references before considering --apply. A successful copy is not a hardware listening pass.',
        'guide': 'docs/hardware-workflow-tools.md',
    },
    'demo': {
        'title': 'Try the toolkit with no hardware or licensed samples',
        'command': 'mpc-tools demo --output "work/my-first-demo"',
        'needs': 'An installed toolkit and a new writable output directory.',
        'next': 'Verify the result with mpc-tools demo --verify "work/my-first-demo". This generates synthetic audio locally, not an MPC-authored project.',
        'guide': 'docs/portable-demo.md',
    },
}


def show(goal: str | None = None, as_json: bool = False) -> int:
    selected = {goal: WORKFLOWS[goal]} if goal else WORKFLOWS
    report = {'format': 1, 'kind': 'mpc-start', 'workflows': selected,
              'boundary': 'Guidance only: no commands executed, no storage discovery, no files written. Replace example paths before running commands.'}
    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print('START HERE — choose one musical task, not the whole toolkit')
        for key, item in selected.items():
            print(f"\n{key}: {item['title']}\nNeeds: {item['needs']}\n  {item['command']}\nNext: {item['next']}\nGuide: {item['guide']}")
        print('\n' + report['boundary'])
    return 0
