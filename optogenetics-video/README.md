# Hijacked Light: optogenetics motion graphic (1:20, 1080×1920)

Code-driven motion graphic for the "lasers into a living brain ← 1866 pond scum" script.

| file | role |
|---|---|
| `tts.py` | Kokoro TTS voiceover, one clip per caption line → `vo/*.wav` + `timeline.json` |
| `anim.html` | the whole animation as a pure `render(t)` canvas function. Open it in a browser to scrub and preview |
| `render.js` | Playwright frame renderer (4 parallel workers → x264), also dumps the SFX cue sheet |
| `audio.py` | synthesized score (D minor → D major at the finale), ~25 SFX types placed from cues, VO ducking |
| `build.sh` | full rebuild |

Scenes (all timing comes from the VO's word timings, so changing the VO re-times everything):
1. Laser into the brain, then a tethered mouse spinning on light pulses
2. SCI-FI glitch, HIJACKED stamp, year rewinds 2026→1866, sepia microscope with green pond scum
3. Chlamydomonas with its eyespot callout, then a swarm doing phototaxis to the "just right" light band
4. +100 years, a 0.50 ms stopwatch, algae vs human-vision bars
5. Zoom into the membrane: 7-helix protein, retinal "light sensor", locked ion gate
6. Photon hits, gate SNAPs open (elastic + shake), ions rush in, voltage spike
7. CHANNELRHODOPSIN title
8. Wild-idea spark, algal gene carried into a mammalian neuron
9. IT WORKED, neuron firing on light (ON/OFF switch + spike trace), OPTOGENETICS title
10. Optical fiber threads into the brain, pulses, MOVEMENT / MEMORY
11. Chain back to the origin (brain → neuron → channelrhodopsin → algae → sun), sun bloom, end card
