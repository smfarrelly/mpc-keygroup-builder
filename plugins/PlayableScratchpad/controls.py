"""Resolve the combined XL3 worksheet against all three actual SDK host dumps."""

import csv
import tomllib
from mpc_keygroup_builder import plugin_map, sdk_params
from audio import HERE


def worksheet(folder):
    config = tomllib.loads((HERE / "controls.toml").read_text())
    channel = config.pop("channel")
    used = set()
    with (folder / "XL3 controls.csv").open("x", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(
            [
                "XL3 control",
                "Channel",
                "CC",
                "Behavior",
                "Plugin",
                "Parameter",
                "SDK index",
            ]
        )
        for plugin, bindings in config.items():
            params = sdk_params.inspect(HERE.parent / plugin / "build/params.json")
            by_name = {p["name"]: p for p in params["controls"]}
            for endpoint, name in bindings.items():
                param = by_name[name]
                cc = plugin_map.endpoint_cc(endpoint)
                if cc in used or not param["sdk"]["automatable"]:
                    raise ValueError(
                        f"unavailable endpoint or parameter: {endpoint} / {name}"
                    )
                used.add(cc)
                writer.writerow(
                    [
                        endpoint,
                        channel,
                        cc,
                        "toggle" if "button" in endpoint else "absolute",
                        params["plugin"],
                        name,
                        param["ui_parameter"],
                    ]
                )
