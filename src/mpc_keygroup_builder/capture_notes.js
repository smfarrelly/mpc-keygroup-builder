(() => {
  "use strict";
  const manifest = JSON.parse(document.getElementById("note-manifest").textContent);
  const key = "mpc-xl3-notes:" + manifest.fingerprint;
  const byKey = new Map(manifest.controls.map(control => [control.key, control]));
  const select = document.getElementById("gesture");
  const field = document.getElementById("observation");
  const status = document.getElementById("note-status");
  let notes = new Map();

  function payload() {
    return {
      kind: "mpc-preset-gesture-notes", schema_version: 1, fingerprint: manifest.fingerprint,
      project: manifest.project, project_sha256: manifest.project_sha256,
      observations: Array.from(notes, ([id, note]) => ({...byKey.get(id), note}))
    };
  }
  function parse(text) {
    const data = JSON.parse(text);
    if (data?.kind !== "mpc-preset-gesture-notes" || data.schema_version !== 1 ||
        data.fingerprint !== manifest.fingerprint || !Array.isArray(data.observations)) {
      throw Error("Choose a notes file for this saved project and controller layout.");
    }
    const result = new Map();
    for (const row of data.observations) {
      if (!byKey.has(row?.key) || result.has(row.key) || typeof row.note !== "string" || row.note.length > 2000) {
        throw Error("A control or note is invalid. Your current notes are still available.");
      }
      result.set(row.key, row.note);
    }
    return result;
  }
  function store(message) {
    try {
      localStorage.setItem(key, JSON.stringify(payload()));
      status.textContent = message;
    } catch {
      status.textContent = "Browser storage is unavailable. Download your notes before closing.";
    }
  }
  function show() {
    field.value = notes.get(select.value) || "";
  }
  for (const control of byKey.values()) {
    const option = document.createElement("option");
    option.value = control.key;
    option.textContent = [control.mode, control.endpoint, control.target, control.preset].filter(Boolean).join(" · ");
    select.append(option);
    const cell = document.getElementById(control.key);
    if (cell) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Take a note";
      button.className = "note-link";
      button.setAttribute("aria-label", "Take a note for " + option.textContent);
      button.onclick = () => {
        select.value = control.key;
        show();
        field.focus();
      };
      cell.append(button);
    }
  }
  try {
    const text = localStorage.getItem(key);
    if (text) notes = parse(text);
  } catch {
    status.textContent = "Could not restore browser notes. You can restore a downloaded file.";
  }
  select.onchange = show;
  field.oninput = () => {
    if (field.value.trim()) notes.set(select.value, field.value);
    else notes.delete(select.value);
    store("Saved in this browser.");
  };
  document.getElementById("save-notes").onclick = () => {
    const blob = new Blob([JSON.stringify(payload(), null, 2) + "\n"], {type: "application/json"});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "mpc-preset-notes-" + manifest.fingerprint.slice(0, 12) + ".json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  document.getElementById("restore-notes").onchange = async event => {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file) return;
    try {
      const imported = parse(await file.text());
      for (const [id, note] of imported) {
        if (notes.has(id) && notes.get(id) !== note) {
          throw Error("A restored note conflicts with one in this browser. Download your current notes before editing.");
        }
      }
      for (const [id, note] of imported) notes.set(id, note);
      show();
      store("Restored " + imported.size + " notes.");
    } catch (error) {
      status.textContent = error.message;
    }
    input.value = "";
  };
  show();
  document.getElementById("notebook").hidden = false;
})();
