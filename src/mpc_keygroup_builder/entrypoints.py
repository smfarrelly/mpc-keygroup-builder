"""Shared console dispatch with consistent versions and friendly expected errors."""

from __future__ import annotations

import importlib
import importlib.metadata
import json
import os
import sys
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandSpec:
    module: str
    function: str
    category: str
    summary: str
    documentation: str


def _spec(module: str, category: str, summary: str, documentation: str, function: str = "main") -> CommandSpec:
    return CommandSpec(module, function, category, summary, documentation)


COMMANDS = {
    "mpc-tools": _spec("ux", "Start here", "Discover commands, diagnose installation, and run guided demos", "docs/getting-started.md"),
    "mpc-keygroup": _spec("cli", "Build", "Build one pitched Keygroup from WAV files", "docs/keygroup-building.md"),
    "mpc-keygroup-batch": _spec("workflow", "Build", "Run manifest-driven Keygroup batches", "docs/keygroup-building.md"),
    "mpc-program-test": _spec("testing", "Inspect", "Semantically simulate XPM programs", "docs/testing-framework.md"),
    "mpc-program-audition": _spec("audition", "Inspect", "Render a local Keygroup audition", "docs/testing-framework.md"),
    "mpc-bundle-verify": _spec("bundle_verify", "Inspect", "Verify a complete checksummed workflow bundle", "docs/testing-framework.md"),
    "mpc-program-color": _spec("programs", "Build", "Apply semantic colors to a Drum Program", "docs/program-model-and-layouts.md"),
    "mpc-project-capture": _spec("capture", "Hardware", "Capture paired MPC project evidence", "docs/key37-routing-capture.md"),
    "mpc-hardware-results": _spec("hardware", "Hardware", "Validate or apply hardware listening results", "docs/hardware-workflow-tools.md"),
    "mpc-hardware-init": _spec("hardware", "Hardware", "Initialize a hardware listening ledger", "docs/hardware-workflow-tools.md", "init_main"),
    "mpc-drum-audit": _spec("drum_audit", "Inspect", "Audit pads, roles, and mute groups", "docs/testing-framework.md"),
    "mpc-xpm": _spec("xpm", "Inspect", "Inspect or compare XPM documents", "docs/testing-framework.md"),
    "mpc-xpj": _spec("xpj", "Inspect", "Inspect or compare MPC project captures", "docs/xpj-inspector.md"),
    "mpc-drum-map": _spec("drum_map", "Inspect", "Render a bank-by-bank Drum map", "docs/hardware-workflow-tools.md"),
    "mpc-drum-build": _spec("drum_builder", "Build", "Build a self-contained Drum Program", "docs/program-model-and-layouts.md"),
    "mpc-drum-compose": _spec("drum_compose", "Build", "Compose complete banks from Drum Programs", "docs/program-model-and-layouts.md"),
    "mpc-loop-inventory": _spec("loop_inventory", "Inspect", "Inventory tempo-labelled audio loops", "docs/ableton-source-inspector.md"),
    "mpc-ableton": _spec("ableton", "Inspect", "Inspect Ableton racks and libraries", "docs/ableton-source-inspector.md"),
    "mpc-ableton-backlog": _spec("ableton_backlog", "Inspect", "Prioritize an Ableton conversion backlog", "docs/ableton-source-inspector.md"),
    "mpc-ableton-drum": _spec("ableton_drum", "Build", "Plan and build Ableton Drum conversions", "docs/ableton-source-inspector.md"),
    "mpc-ableton-fidelity": _spec("ableton_fidelity", "Inspect", "Model Ableton-to-MPC feature fidelity", "docs/ableton-source-inspector.md"),
    "mpc-ableton-wave": _spec("ableton_wave", "Build", "Plan and build diverse Ableton Drum waves", "docs/ableton-source-inspector.md"),
    "mpc-ableton-risk": _spec("ableton_risk", "Inspect", "Prioritize Ableton conversion risks for hardware review", "docs/ableton-source-inspector.md"),
    "mpc-program-model": _spec("model", "Inspect", "Normalize an XPM or Drum manifest", "docs/program-model-and-layouts.md"),
    "mpc-program-designer": _spec("designer", "Browser", "Generate a self-contained Program Designer", "docs/program-designer.md"),
    "mpc-web-demo": _spec("web_demo", "Browser", "Generate the no-install synthetic browser demo", "docs/browser-demo.md"),
    "mpc-keygroup-variant": _spec("keygroup_variant", "Build", "Build preservation-first Keygroup variants", "docs/keygroup-variants.md"),
    "mpc-layout": _spec("layout", "Layout", "Plan semantic layouts", "docs/program-model-and-layouts.md"),
    "mpc-layout-export": _spec("layout_export", "Layout", "Export one verified layout XPM", "docs/program-model-and-layouts.md", "export_main"),
    "mpc-layout-verify": _spec("layout_export", "Layout", "Verify an exported layout", "docs/program-model-and-layouts.md", "verify_main"),
    "mpc-layout-package": _spec("layout_export", "Layout", "Package multiple layout candidates", "docs/program-model-and-layouts.md", "package_main"),
    "mpc-layout-draft": _spec("layout_draft", "Layout", "Validate and export browser layout drafts", "docs/program-designer.md"),
    "mpc-scratchpad-check": _spec("candidates", "Hardware", "Report Scratchpad acceptance gates", "docs/hardware-workflow-tools.md"),
    "mpc-sd-deploy": _spec("deploy", "Deploy", "Plan or apply additive SD updates", "docs/hardware-workflow-tools.md"),
    "mpc-package-deploy": _spec("package_deploy", "Deploy", "Transactionally deploy one package", "docs/hardware-workflow-tools.md"),
    "mpc-audio-levels": _spec("levels", "Inspect", "Measure WAV levels and outliers", "docs/testing-framework.md"),
    "mpc-routing-capture": _spec("routing", "Hardware", "Capture and inspect routing XPJ evidence", "docs/key37-routing-capture.md"),
    "mpc-repository-guard": _spec("guardrails", "Development", "Refuse licensed or generated artifacts in Git", "docs/hardware-workflow-tools.md"),
    "mpc-reference-cache": _spec("reference_cache", "Reference", "Cache and verify personal vendor-document copies", "docs/vendor-documents.md"),
    "mpc-rig": _spec("rig", "Hardware", "Validate or render rig profiles", "docs/rig-profiles.md"),
    "mpc-library": _spec("library", "Catalog", "Query the hardware-status ledger", "docs/catalog.md"),
    "mpc-catalog": _spec("catalog", "Catalog", "Build or query the normalized catalog", "docs/catalog.md"),
    "mpc-drum-idea": _spec("ideas", "Creative MIDI", "Generate role-addressed Drum MIDI", "docs/drum-ideas.md"),
    "mpc-harmony-idea": _spec("harmony", "Creative MIDI", "Generate Chords and Bass MIDI", "docs/creative-midi.md"),
    "mpc-melody-idea": _spec("melody", "Creative MIDI", "Generate motif-based Melody MIDI", "docs/creative-midi.md"),
    "mpc-workstation-idea": _spec("workstation", "Creative MIDI", "Generate a four-part Scratchpad idea", "docs/creative-midi.md"),
    "mpc-arrange-idea": _spec("arrangement", "Creative MIDI", "Derive five traceable arrangement sections", "docs/creative-midi.md"),
    "mpc-idea-batch": _spec("idea_batch", "Creative MIDI", "Generate and rank a bounded seed batch", "docs/creative-midi.md"),
    "mpc-kit-select": _spec("kit_select", "Catalog", "Select one deterministic cross-library kit", "docs/catalog.md"),
    "mpc-kit-wave": _spec("kit_wave", "Catalog", "Build and audit a multi-recipe kit wave", "docs/catalog.md"),
    "mpc-portable-demo": _spec("portable_demo", "Start here", "Build the redistributable end-to-end fixture", "docs/portable-demo.md"),
    "mpc-midi-control": _spec("midi_control", "MIDI control", "Compile and compare controller maps", "docs/declarative-midi-control.md"),
    "mpc-launch-control": _spec("launch_control", "MIDI control", "Inspect Launch Control Components captures", "docs/declarative-midi-control.md"),
    "mpc-session-report": _spec("session", "Hardware", "Combine rig, candidate, and capture readiness", "docs/rig-profiles.md"),
    "mpc-plugin-audit": _spec("plugin_audit", "Inspect", "Inventory installed MPC plugin content", "docs/hardware-workflow-tools.md"),
    "mpc-plugin-params": _spec("plugin_params", "MIDI control", "Search plugin controls and verified MIDI Learn mappings", "docs/plugin-parameters.md"),
    "mpc-plugin-skin-audit": _spec("plugin_skin_audit", "MIDI control", "Compare plugin UI skin parameter metadata", "docs/plugin-parameters.md"),
    "mpc-plugin-map": _spec("plugin_map", "MIDI control", "Compile role-based Launch Control plugin pages", "docs/plugin-mapping.md"),
    "mpc-plugin-companion": _spec("plugin_companion", "Browser", "Generate an offline plugin-mapping companion", "docs/plugin-mapping.md"),
    "mpc-plugin-results": _spec("plugin_results", "Hardware", "Validate companion exports and write a durable ledger", "docs/plugin-mapping.md"),
    "mpc-plugin-seed": _spec("plugin_seed", "MIDI control", "Generate a ranked plugin performance-profile draft", "docs/plugin-mapping.md"),
    "mpc-plugin-coverage": _spec("plugin_coverage", "MIDI control", "Measure plugin mapping coverage and rank omissions", "docs/plugin-mapping.md"),
    "mpc-controller-capacity": _spec("controller_capacity", "MIDI control", "Validate the complete Custom Mode and channel plan", "docs/declarative-midi-control.md"),
    "mpc-schema": _spec("schema", "Reference", "Discover schemas and validate declarative files", "docs/schemas.md"),
    "mpc-showcase": _spec("showcase", "Start here", "Build six reproducible composition evidence bundles", "docs/composition-showcase.md"),
    "mpc-recipe-audit": _spec("recipe_audit", "Creative MIDI", "Audit recipe dependencies, compatibility, IDs, and channels", "docs/creative-midi.md"),
    "mpc-workstation-wave": _spec("workstation_wave", "Creative MIDI", "Generate and rank a multi-family workstation wave", "docs/creative-wave.md"),
    "mpc-creative-review": _spec("creative_review", "Browser", "Render an offline creative-wave review companion", "docs/creative-wave.md"),
    "mpc-creative-results": _spec("creative_results", "Creative MIDI", "Validate review exports and package an MPC shortlist", "docs/creative-wave.md"),
}


EXPECTED_ERRORS = (
    ValueError,
    FileNotFoundError,
    FileExistsError,
    PermissionError,
    IsADirectoryError,
    NotADirectoryError,
    json.JSONDecodeError,
    tomllib.TOMLDecodeError,
    ET.ParseError,
)


def version() -> str:
    try:
        return importlib.metadata.version("mpc-keygroup-builder")
    except importlib.metadata.PackageNotFoundError:
        # Source checkouts used by system pytest may not expose wheel metadata.
        # Keep --version useful without making the command depend on its cwd.
        project = os.path.join(os.path.dirname(__file__), "..", "..", "pyproject.toml")
        try:
            with open(project, "rb") as stream:
                value = tomllib.load(stream).get("project", {}).get("version")
            return str(value) if value else "development"
        except (OSError, tomllib.TOMLDecodeError):
            return "development"


def _hint(error: Exception, command: str) -> str:
    if isinstance(error, FileNotFoundError):
        return "Check the path and spelling. Absolute paths are easiest when files are on removable media."
    if isinstance(error, PermissionError):
        return "Check directory permissions and confirm removable media is mounted read-write."
    if isinstance(error, FileExistsError):
        return f"Choose a new output path, or run `{command} -h` to see whether safe replacement is supported."
    if isinstance(error, (json.JSONDecodeError, tomllib.TOMLDecodeError, ET.ParseError)):
        return "The input document is malformed. The error location above identifies where parsing stopped."
    return f"The input failed validation. Review the named field or path, then run `{command} -h` for accepted values."


def invoke(command: str, arguments: list[str] | None = None, *, friendly: bool = True) -> int:
    spec = COMMANDS.get(command)
    if spec is None:
        choices = ", ".join(sorted(COMMANDS))
        print(f"ERROR: unknown MPC command {command!r}\nAvailable commands: {choices}", file=sys.stderr)
        return 2
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    if arguments == ["--version"]:
        print(f"{command} {version()}")
        return 0
    module = importlib.import_module(f"mpc_keygroup_builder.{spec.module}")
    target = getattr(module, spec.function)
    previous = sys.argv
    try:
        sys.argv = [command, *arguments]
        return int(target() or 0)
    except EXPECTED_ERRORS as error:
        if not friendly or os.environ.get("MPC_DEBUG") == "1":
            raise
        print(f"ERROR: {error}", file=sys.stderr)
        print(f"NEXT: {_hint(error, command)}", file=sys.stderr)
        print("DEBUG: Re-run with MPC_DEBUG=1 to show the Python traceback.", file=sys.stderr)
        return 2
    finally:
        sys.argv = previous


def main() -> int:
    command = sys.argv[0].replace("\\", "/").rsplit("/", 1)[-1]
    for suffix in (".exe", ".cmd", ".bat"):
        if command.casefold().endswith(suffix):
            command = command[: -len(suffix)]
            break
    return invoke(command)
