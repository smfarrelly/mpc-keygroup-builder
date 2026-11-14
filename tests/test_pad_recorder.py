import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
import io
import json
import os
import subprocess
from pathlib import Path
import tempfile
import time
import unittest
import wave

from mpc_keygroup_builder import bundle_verify, ideas, pad_recorder as recorder


class PadRecorderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name, amplitude in (("Kick", 1000), ("Kick Loud", 3000)):
            with wave.open(str(self.root / (name + ".wav")), "wb") as wav:
                wav.setparams((2, 2, 44100, 100, "NONE", ""))
                wav.writeframes(amplitude.to_bytes(2, "little") * 200)
        self.program = self.root / "kit.xpm"
        self.program.write_text('''<MPCVObject><Program type="Drum"><ProgramName>Test &amp; Kit</ProgramName>
          <PadNoteMap><PadNote number="1"><Note>44</Note></PadNote><PadNote number="17"><Note>70</Note></PadNote></PadNoteMap>
          <Instruments><Instrument number="1"><OneShot>True</OneShot><Layers>
          <Layer><SampleFile>Kick.wav</SampleFile><VelEnd>95</VelEnd><SliceStart>2</SliceStart><SliceEnd>8</SliceEnd></Layer>
          <Layer><SampleFile>Kick Loud.wav</SampleFile><VelStart>96</VelStart></Layer></Layers></Instrument>
          <Instrument number="17"><Layers><Layer><SampleFile>Kick.wav</SampleFile></Layer></Layers></Instrument>
          </Instruments></Program></MPCVObject>''')

    def test_real_regions_layers_events_and_export(self):
        layout, assets = recorder.bank_data(self.program, "A")
        pad, = layout["pads"]
        self.assertEqual((pad["pad"], pad["note"], pad["oneShot"]), (1, 44, True))
        with wave.open(io.BytesIO(base64.b64decode(assets[pad["layers"][0]["audio"]]))) as stream:
            self.assertEqual((stream.getnframes(), stream.getnchannels()), (7, 2))
        page = recorder.build(self.program, self.root / "page")
        self.assertIn("Test &amp; Kit", page.read_text())
        self.assertEqual(bundle_verify.verify_bundle(page.parent)["verified_files"], 2)
        take = json.loads((page.parent / "starter.take.json").read_text())
        take["events"] = [dict(tick=7, duration_ticks=60, pad=1, velocity=95),
                          dict(tick=120, duration_ticks=60, pad=1, velocity=96)]
        take_path = self.root / "input.take.json"
        take_path.write_text(json.dumps(take))
        wav = recorder.render(self.program, take_path, self.root / "render")
        result = json.loads(wav.with_suffix(".json").read_text())
        self.assertEqual([row["sample"] for row in result["events"]], ["Kick.wav", "Kick Loud.wav"])
        self.assertEqual(result["events"][0]["played_frames"], 7)
        self.assertEqual(bundle_verify.verify_bundle(wav.parent)["verified_files"], 5)
        idea = recorder.validate_take(take, layout)
        self.assertEqual((wav.parent / "pattern.mid").read_bytes(), ideas.render_midi(idea))
        with self.assertRaises(FileExistsError):
            recorder.render(self.program, take_path, wav.parent)

    def test_reject_bad_takes_and_modified_audio(self):
        layout, _ = recorder.bank_data(self.program, "A")
        take = recorder.initial_take(layout, 120, 1)
        for key, value in (("bars", True), ("channel", 0), ("tempo", float("nan")), ("bank", "B"),
                           ("version", True), ("fingerprint", "old"), ("events", [None]),
                           ("events", [dict(tick=1919, duration_ticks=2, pad=1, velocity=40)]),
                           ("events", [dict(tick=0, duration_ticks=1, pad=17, velocity=40)])):
            with self.subTest(key=key), self.assertRaises(ValueError):
                recorder.validate_take({**take, key: value}, layout)
        path = self.root / "Kick.wav"
        path.write_bytes(path.read_bytes().replace((1000).to_bytes(2, "little"), (2000).to_bytes(2, "little")))
        updated, _ = recorder.bank_data(self.program, "A")
        with self.assertRaisesRegex(ValueError, "different kit"):
            recorder.validate_take(take, updated)

    def test_recipe_uses_selected_bank(self):
        recipe = self.root / "kick.toml"
        recipe.write_text('schema_version=1\nid="kick"\nname="Kick"\nbars=1\nsteps_per_bar=16\n'
                          '[[events]]\nrole="kick"\nsteps=[0,4]\nvelocity=100\n')
        page = recorder.build(self.program, self.root / "page", bank="B", recipe=recipe)
        take = json.loads((page.parent / "starter.take.json").read_text())
        self.assertEqual([e["pad"] for e in take["events"]], [17, 17])
        with self.assertRaisesRegex(ValueError, "no playable pads"):
            recorder.build(self.program, self.root / "missing", bank="H")
        self.assertFalse((self.root / "missing").exists())

    def test_reject_overlap_and_unreadable_samples(self):
        self.program.write_text(self.program.read_text().replace("<VelStart>96", "<VelStart>95"))
        with self.assertRaisesRegex(ValueError, "velocity 95"):
            recorder.bank_data(self.program, "A")
        (self.root / "Kick.wav").write_bytes(b"broken")
        with self.assertRaisesRegex(ValueError, "Kick.wav"):
            recorder.bank_data(self.program, "A")

    @unittest.skipUnless(os.environ.get("MPC_TEST_CHROME"), "needs a headless Chrome executable")
    def test_browser_records_velocity_and_filters_a_simulated_midi_input(self):
        page = recorder.build(self.program, self.root / "web")
        script = r"""<script>
        (async () => {
          const get = id => document.getElementById(id);
          const wait = ms => new Promise(r => setTimeout(r, ms));
          const until = async fn => { for(let i=0;i<500;i++){ if(fn())return; await wait(10); } throw Error("timeout"); };
          const assert = (value, message) => { if (!value) throw Error(message); };
          const port = {id:"pads", name:"Fixture", state:"connected", close:async()=>{}};
          const access = {inputs:new Map([["pads",port]])};
          let calls = 0, blob;
          Object.defineProperty(navigator,"requestMIDIAccess",{value:async options => {
            assert(options.sysex === false,"unexpected SysEx request"); calls++; return access;
          }});
          const original = URL.createObjectURL.bind(URL);
          URL.createObjectURL = b => { blob = b; return original(b); };
          HTMLAnchorElement.prototype.click = () => {};
          assert(calls===0, "initial MIDI access");
          get("connect-midi").click();
          await until(()=>get("midi-port").options.length===2);
          assert(calls===1 && !port.onmidimessage,"input selection");
          get("midi-port").value="pads"; get("midi-port").onchange();
          get("midi-channel").value="10"; get("record").click();
          await until(()=>get("record").getAttribute("aria-pressed")==="true");
          const send = (s,n,v) => port.onmidimessage({data:[s,n,v],timeStamp:performance.now()});
          send(0x90,44,80); send(0xb9,44,80); send(0x99,44,0); send(0x89,44,80); send(0x99,40,80);
          assert(get("midi-status").textContent.includes("outside bank"),"wrong-bank diagnostic");
          send(0x99,44,95);
          await until(()=>get("count").textContent==="1 hit");
          assert(get("midi-status").textContent.includes("velocity 95"),"velocity display");
          get("stop").click(); get("save").click();
          const take = JSON.parse(await blob.text());
          assert(take.events.length===1 && take.events[0].pad===1 && take.events[0].velocity===95,"recorded take");
          port.state="disconnected"; access.onstatechange();
          assert(get("midi-port").value==="" && port.onmidimessage===null,"disconnection");
          document.body.dataset.result="passed";
        })().catch(e => { document.body.dataset.result=e.message; })
            .finally(() => fetch("/result", {method:"POST",body:document.body.dataset.result}));

        </script>"""
        html = page.read_text().replace("</body>", script + "</body>").encode()
        results = []
        class Probe(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(html if self.path == "/" else b"")

            def do_POST(self):
                if self.path == "/result":
                    results.append(self.rfile.read(int(self.headers["Content-Length"])).decode())
                self.send_response(204)
                self.end_headers()

            def log_message(self, *_args):
                pass

        # Decoding runs on a real audio thread. Advancing Chrome's virtual clock
        # can exhaust a JS timeout before that thread runs on a busy CI machine.
        with HTTPServer(("127.0.0.1", 0), Probe) as server:
            server.timeout = 0.25
            url = f"http://127.0.0.1:{server.server_port}/"
            process = subprocess.Popen([os.environ["MPC_TEST_CHROME"], "--headless", "--no-sandbox",
                                        "--disable-gpu", "--disable-dev-shm-usage", "--mute-audio",
                                        "--autoplay-policy=no-user-gesture-required",
                                        "--user-data-dir=" + str(self.root / "profile"), url],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                deadline = time.monotonic() + 25
                while not results and process.poll() is None and time.monotonic() < deadline:
                    server.handle_request()
            finally:
                process.terminate()
                process.wait(timeout=10)
        self.assertEqual(results, ["passed"])
