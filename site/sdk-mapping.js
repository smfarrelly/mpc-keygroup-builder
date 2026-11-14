"use strict";

const element = id => document.getElementById(id);
const example = JSON.parse(element("bundled-dump").textContent);
let plugin;
let selected;
let fileRevision = 0;

function validate(dump) {
  if (!dump || typeof dump.name !== "string" || !dump.name.trim() ||
      typeof dump.vendor !== "string" || typeof dump.uid !== "string" || typeof dump.isInstrument !== "boolean" ||
      !Number.isInteger(dump.version) || !["numInputs", "numOutputs", "numPrograms"].every(
        key => Number.isInteger(dump[key]) && dump[key] >= 0) || !Number.isInteger(dump.uidInt) ||
      dump.uidInt < -2147483648 || dump.uidInt > 2147483647 || !Array.isArray(dump.params)) {
    throw Error("Choose the build/params.json written by Akai host_sim.");
  }
  const seen = new Set();
  for (const p of dump.params) {
    if (!p || !Number.isInteger(p.index) || p.index < 0 || p.index >= dump.params.length ||
        seen.has(p.index) || typeof p.name !== "string" || typeof p.automatable !== "boolean" ||
        typeof p.display !== "string" || typeof p.label !== "string" ||
        !Array.isArray(p.choices) || !p.choices.every(v => typeof v === "string")) {
      throw Error("Invalid parameter metadata. Regenerate params.json with host_sim.");
    }
    if (typeof p.kind !== "string" || !Number.isFinite(p.default) || p.default < 0 || p.default > 1) {
      throw Error("Invalid parameter kind or startup value.");
    }
    seen.add(p.index);
  }
  return dump;
}

function load(dump, preselect) {
  plugin = validate(dump);
  selected = preselect ? plugin.params.filter(p => p.automatable && p.name.trim()).slice(0, 8) : [];
  element("query").value = "";
  element("plugin-name").textContent = plugin.name;
  element("file-status").textContent = plugin.vendor + " · " + plugin.params.length + " parameters";
  render();
}

function toggle(p) {
  if (selected.includes(p)) selected = selected.filter(item => item !== p);
  else if (selected.length < 8) selected.push(p);
  render();
}

function drawParameters() {
  const query = element("query").value.toLowerCase().trim();
  const list = element("params");
  list.replaceChildren();
  for (const p of plugin.params) {
    if (![p.name, p.label, ...p.choices].join(" ").toLowerCase().includes(query)) continue;
    const li = document.createElement("li");
    const label = document.createElement("label");
    const check = document.createElement("input");
    check.type = "checkbox";
    check.checked = selected.includes(p);
    check.disabled = !p.automatable || !p.name.trim() || (!check.checked && selected.length === 8);
    check.addEventListener("change", () => {
      toggle(p);
      const next = [...list.querySelectorAll("input")].find(input => input.dataset.index === String(p.index));
      next?.focus();
    });
    check.dataset.index = String(p.index);
    const name = document.createElement("span");
    name.textContent = p.name || "(unnamed parameter)";
    const facts = document.createElement("small");
    const detail = ["Index " + p.index, [p.display, p.label].filter(Boolean).join(" "), p.choices.join(" / ")];
    if (!p.automatable) detail.push("Automation unavailable");
    facts.textContent = detail.filter(Boolean).join(" · ");
    name.append(facts);
    label.append(check, name);
    li.append(label);
    list.append(li);
  }
  if (!list.children.length) list.textContent = "No matching parameters.";
}

function render() {
  drawParameters();
  const list = element("selected");
  list.replaceChildren();
  selected.forEach((p, i) => {
    const li = document.createElement("li");
    const text = document.createElement("span");
    text.textContent = (i + 1) + ". " + p.name + " · CC " + (20 + i);
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Remove";
    button.setAttribute("aria-label", "Remove " + p.name);
    button.onclick = () => {
      toggle(p);
      (list.querySelector("button") || element("query")).focus();
    };
    li.append(text, button);
    list.append(li);
  });
  element("selection-hint").textContent = selected.length + " of 8 encoders assigned";
  element("export").disabled = !selected.length;
}

function tomlString(s) {
  // JSON string escapes also work in TOML basic strings, except DEL must be escaped.
  return JSON.stringify(s).replace(/\x7f/g, "\\u007f");
}

function profileText(slot, channel) {
  const uid = (plugin.uidInt >>> 0).toString(16).padStart(8, "0");
  const slug = plugin.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const id = (slug || "plugin") + "-" + uid + "-encoders";
  const lines = ["schema_version = 1", "id = " + tomlString(id),
    "name = " + tomlString(plugin.name + " Encoders"), "plugin = " + tomlString(plugin.name),
    'description = "Live encoder assignments selected from SDK parameter metadata."',
    "slot = " + slot, "channel = " + channel, 'probe = "top-encoder-1"', "",
    "[sdk_identity]", "vendor = " + tomlString(plugin.vendor), "uid_int = " + plugin.uidInt];
  selected.forEach((p, i) => lines.push("", "[[controls]]", 'control = "top-encoder-' + (i + 1) + '"',
    "name = " + tomlString(p.name), "ui_parameter = " + p.index, 'priority = "core"'));
  return {id, text: lines.join("\n") + "\n"};
}

element("export").onclick = () => {
  for (const id of ["slot", "channel"]) {
    const field = element(id);
    if (!field.reportValidity()) return;
  }
  const {id, text} = profileText(element("slot").valueAsNumber, element("channel").valueAsNumber);
  const url = URL.createObjectURL(new Blob([text], {type: "text/plain;charset=utf-8"}));
  const link = document.createElement("a");
  link.href = url;
  link.download = id + ".toml";
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
element("query").oninput = drawParameters;
element("example").onclick = () => {
  ++fileRevision;
  element("file").value = "";
  load(example, true);
};
element("file").onchange = async event => {
  const revision = ++fileRevision;
  const file = event.target.files[0];
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    if (revision === fileRevision) load(data, false);
  } catch (error) {
    if (revision === fileRevision) element("file-status").textContent = file.name + " · " + error.message;
  }
};
load(example, true);
