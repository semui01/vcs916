"""Generate the voiceover with Kokoro TTS, one wav per caption chunk, and a timeline.json."""
import json, sys, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

TTS = sys.argv[1]  # dir holding kokoro-v1.0.onnx + voices-v1.0.bin
VOICE = sys.argv[2] if len(sys.argv) > 2 else "am_michael"
SPEED = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0

# (scene, caption text, spoken text or None, pause after in seconds)
CHUNKS = [
  (1, "Neuroscientists can now fire lasers into a living brain", None, 0.05),
  (1, "to instantly control an animal's movements.", None, 0.45),
  (2, "But this sci-fi reality was actually hijacked", None, 0.05),
  (2, "from an 1866 observation of green pond scum.", "from an eighteen sixty-six observation of green pond scum.", 0.45),
  (3, "A biologist noticed that microscopic algae", None, 0.05),
  (3, "possessed a natural light sensor,", None, 0.1),
  (3, "allowing them to actively swim toward the perfect level of sunlight.", None, 0.45),
  (4, "A century later, scientists realized", None, 0.05),
  (4, "the algae reacted to light in just half a millisecond,", None, 0.1),
  (4, "faster than human vision.", None, 0.45),
  (5, "The secret was an elegant two-in-one protein on the cell surface", "The secret was an elegant, two-in-one protein on the cell surface,", 0.05),
  (5, "that directly detects light while acting as a tightly closed gate.", None, 0.4),
  (6, "When light hits it, the gate immediately snaps open.", None, 0.25),
  (6, "Ions rush inside, creating an instant electrical signal,", None, 0.2),
  (7, "a protein called channelrhodopsin.", "a protein called, channel-roh-dopsin.", 0.55),
  (8, "This sparked a wild idea.", None, 0.25),
  (8, "What if we transplanted this exact algal gate", "What if we transplanted this exact algal gate", 0.0),
  (8, "into a mammalian nerve cell?", None, 0.45),
  (9, "It worked.", None, 0.3),
  (9, "The neuron turned into a biological switch fired by light,", None, 0.15),
  (9, "a technique named optogenetics.", "a technique named, optogenetics.", 0.55),
  (10, "Today, scientists thread tiny optical fibers into living brains.", None, 0.25),
  (10, "By pulsing light, they activate these hijacked neurons", None, 0.05),
  (10, "to trigger movements or reactivate memories.", None, 0.55),
  (11, "This revolutionary neuroscience breakthrough only exists", None, 0.05),
  (11, "because we figured out how to hijack", None, 0.0),
  (11, "a microscopic algae's reflex for finding the sun.", None, 0.0),
]

k = Kokoro(f"{TTS}/kokoro-v1.0.onnx", f"{TTS}/voices-v1.0.bin")
out, t, sr0 = [], 0.6, None
pieces = []
for i, (scene, cap, spoken, pause) in enumerate(CHUNKS):
    audio, sr = k.create(spoken or cap, voice=VOICE, speed=SPEED, lang="en-us")
    sr0 = sr
    # trim leading/trailing near-silence so captions sync tightly
    a = np.abs(audio); thr = 0.01 * a.max()
    nz = np.where(a > thr)[0]
    audio = audio[max(0, nz[0] - int(0.02*sr)): nz[-1] + int(0.06*sr)]
    dur = len(audio) / sr
    sf.write(f"vo/{i:02d}.wav", audio, sr)
    out.append(dict(i=i, scene=scene, text=cap, start=round(t, 3), end=round(t + dur, 3)))
    t += dur + pause + 0.08
json.dump(dict(voice=VOICE, speed=SPEED, sr=sr0, total=round(t, 3), chunks=out), open("timeline.json", "w"), indent=1)
print("total speech timeline:", round(t, 2), "s")
