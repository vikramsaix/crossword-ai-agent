# Demo media

- `crossword-agent-demo.mp4` — final narrated client-facing demonstration (H.264/AAC, 1280×720, 24 fps, 51.28 seconds).
- `preview-contact-sheet.png` — representative frames for quick review.
- `demo_script.txt` — narration text.
- `render_demo.py` — deterministic Pillow + FFmpeg motion-graphics source. It produces a silent 54-second timeline at `demo/crossword-agent-demo-silent.mp4`; the final MP4 is muxed with generated narration from the task workspace.

To recreate the silent graphics timeline, run these commands from the
`crossword-agent-assessment` project directory:

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r demo/requirements.txt
python3 demo/render_demo.py
```

Pillow supplies image rendering. The renderer uses FFmpeg from your PATH when
available, otherwise the executable bundled with `imageio-ffmpeg`. It supports
Linux, macOS, and Windows font locations, with a Pillow font fallback.

The narration WAV is not checked in; the final narrated MP4 is included as the submission artifact.
