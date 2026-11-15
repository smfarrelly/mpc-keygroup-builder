# Check the volume of an exported track

On the laptop, choose the actual WAV you play on the other stereo. For an MPC-only mix use the Audio Mixdown WAV. For the whole rig use the stereo MASTER L/R recording from the LiveTrak L6. Headphone monitor volume is independent of the measurements. Use the same musical edit when comparing two bounces.

From a current checkout with FFmpeg installed, run:

```bash
uv run mpc-export-loudness "/path/to/My Take.wav"
uv run mpc-export-loudness "/path/to/My Take.wav" --reference "/path/to/Reference.wav"
```

On Ubuntu install FFmpeg with `sudo apt install ffmpeg`. On other systems put FFmpeg on your PATH. Verify with `ffmpeg -version`. Input WAVs can be integer PCM or floating point, including 32-bit float recordings. Both files are read locally. Paste or drag a WAV's full path into the terminal if its name contains spaces.

- **Integrated loudness (LUFS)** measures the whole track using loudness gating. A positive gain-to-reference estimate means the export plays quieter. A reference is optional. Choose one with a similar arrangement if you're comparing different songs.
- **True peak (dBTP)** estimates the highest reconstructed signal level on any channel. The timestamp points to the beginning of the strongest 50 ms window. Listen there to identify the sound using the headroom. Equal peaks resolve to the first window.
- **Clean gain** is the constant gain available before the chosen ceiling. The default is −1 dBTP. Set a different ceiling with `--ceiling -2`. The suggested upward gain is rounded down to a tenth of a dB. If the reference needs more gain than fits, listen at the peak timestamp before adjusting that hit or auditioning Peak Finish. Measure the new bounce after any processing.
- **Very short or quiet files** can have a measurable peak and no gated integrated reading. Digital silence has no peak timestamp. Mono is measured for playback through both stereo channels. The scanner uses FFmpeg's 192 kHz resampling and integrated loudness implementation. [FFmpeg loudnorm documentation](https://ffmpeg.org/ffmpeg-filters.html#loudnorm)

Use `--json` for a reusable report. Positive `headroom_db` is available gain, negative means the file exceeds the chosen ceiling. Missing measurements are JSON null. To save a report, redirect the output to a new JSON filename.
