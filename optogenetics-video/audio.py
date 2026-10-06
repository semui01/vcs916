"""Score + SFX + voiceover mix for the optogenetics video.

usage: python3 audio.py cues.json timeline.json vo_dir out.wav [--no-vo]
All music and SFX are synthesized here; cue times come from the animation (cues.json).
"""
import json, sys, numpy as np, soundfile as sf
from scipy.signal import lfilter, butter, sosfilt, resample_poly

SR = 48000
cues_doc = json.load(open(sys.argv[1])); TL = json.load(open(sys.argv[2])); VO_DIR = sys.argv[3]; OUT = sys.argv[4]
NO_VO = '--no-vo' in sys.argv
DUR = cues_doc['duration']; N = int(DUR * SR)
scenes = {s['id']: s for s in cues_doc['scenes']}
rs = np.random.default_rng(1)

def t_(n): return np.arange(n) / SR
def env_exp(n, k): return np.exp(-t_(n) * k)
def adsr(n, a=0.01, r=0.1):
    e = np.ones(n); na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e
def lp(x, f, order=2): return sosfilt(butter(order, min(f, SR / 2 - 100) / (SR / 2), 'low', output='sos'), x)
def hp(x, f, order=2): return sosfilt(butter(order, f / (SR / 2), 'high', output='sos'), x)
def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo / (SR / 2), min(hi, SR / 2 - 100) / (SR / 2)], 'band', output='sos'), x)
def sweep(f0, f1, n, curve='exp'):
    f = np.geomspace(f0, f1, n) if curve == 'exp' else np.linspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)
def noise(n): return rs.standard_normal(n)
def tvlp(x, f0, f1, steps=64):
    """time-varying lowpass by block crossfade"""
    out = np.zeros_like(x); edges = np.linspace(0, len(x), steps + 1).astype(int)
    for i in range(steps):
        a, b = edges[i], edges[i + 1]; f = f0 * (f1 / f0) ** (i / steps)
        seg = x[max(0, a - 2000):b]; y = lp(seg, f); out[a:b] = y[-(b - a):]
    return out
def stereo(x, pan=0.0):
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    return np.stack([x * l, x * r], 1)

# ---------------------------------------------------------------- SFX
def sfx(kind, length=None, pitch=0):
    L = lambda s: int(s * SR)
    if kind == 'laser':
        n = L(0.26); x = sweep(2600, 260, n) * 0.6 + np.sign(sweep(1300, 130, n)) * 0.12
        return lp(x * env_exp(n, 14), 9000) * 0.55
    if kind in ('boom', 'impact'):
        n = L(2.2 if kind == 'boom' else 1.2); f = 34 + 46 * np.exp(-t_(n) * 9)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 2.0 if kind == 'boom' else 3.5)
        x += lp(noise(n), 900) * env_exp(n, 18) * 0.5
        return x * (1.0 if kind == 'boom' else 0.6)
    if kind in ('riser', 'zoom'):
        n = L(length or 1.2); nz = noise(n); e = np.linspace(0, 1, n) ** 2.2
        x = tvlp(nz, 300, 9000) * 0.5 + sweep(180, 1400, n) * 0.25
        return x * e
    if kind in ('whoosh', 'swoosh'):
        n = L(length or (0.6 if kind == 'whoosh' else 0.9)); e = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
        return bp(noise(n), 400, 5000) * e * 0.55
    if kind == 'glitch':
        n = L(0.45); x = np.zeros(n); i = 0
        while i < n:
            seg = rs.integers(L(0.01), L(0.05)); f = rs.choice([180, 360, 720, 1440, 2880])
            x[i:i + seg] = np.sign(np.sin(2 * np.pi * f * t_(min(seg, n - i)))) * rs.uniform(0.2, 0.6) * (rs.random() > 0.3)
            i += seg
        return lp(x, 7000) * 0.5
    if kind == 'stamp':
        n = L(0.9); x = sfx('impact')[:n] * 0.9
        x[:L(0.02)] += noise(L(0.02)) * 0.8; return x
    if kind == 'tick':
        n = L(length or 1); rate = 10; x = np.zeros(n)
        clk = hp(noise(L(0.012)), 2500) * env_exp(L(0.012), 300)
        for k in np.arange(0, length or 1, 1 / rate): i = L(k); x[i:i + len(clk)] += clk[:max(0, n - i)]
        return x * 0.5
    if kind == 'rewind':
        n = L(length or 1); x = np.zeros(n); seg = L(0.07)
        for i in range(0, n - seg, seg): x[i:i + seg] += sweep(2200 - 1500 * i / n, 300, seg) * np.hanning(seg)
        return bp(x, 200, 6000) * 0.25
    if kind == 'bubbles':
        n = L(length or 3); x = np.zeros(n)
        for _ in range(int((length or 3) * 6)):
            i = rs.integers(0, n - L(0.12)); m = L(rs.uniform(0.04, 0.1)); f0 = rs.uniform(350, 900)
            x[i:i + m] += sweep(f0, f0 * 2.2, m) * env_exp(m, 30) * rs.uniform(0.2, 0.6)
        return x * 0.5
    if kind == 'ping':
        n = L(1.6); f = 1046.5 * 2 ** (pitch * 2 / 12)
        x = sum(a * np.sin(2 * np.pi * f * h * t_(n)) for h, a in [(1, 1), (2.01, 0.4), (3.0, 0.15), (4.2, 0.08)])
        return x * env_exp(n, 3.5) * 0.35
    if kind in ('shimmer', 'spark'):
        n = L(2.6); x = np.zeros(n)
        for j, semi in enumerate([0, 7, 12, 16, 19, 24, 28]):
            d = L(j * 0.045); f = 880 * 2 ** (semi / 12); m = n - d
            x[d:] += np.sin(2 * np.pi * f * t_(m)) * env_exp(m, 2.2) * 0.12
        if kind == 'spark':
            cr = np.zeros(L(0.5)); idx = rs.integers(0, len(cr), 120); cr[idx] = rs.uniform(-1, 1, 120); x[:len(cr)] += hp(cr, 3000) * 0.8
        return x
    if kind == 'flash':
        n = L(0.5); return (hp(noise(n), 3000) * env_exp(n, 12) * 0.4 + sweep(3000, 1200, n) * env_exp(n, 9) * 0.15)
    if kind == 'lock':
        n = L(0.35); x = np.zeros(n)
        for d, f in [(0, 2400), (0.09, 1700)]:
            i = L(d); m = L(0.08); x[i:i + m] += (np.sin(2 * np.pi * f * t_(m)) + hp(noise(m), 2000) * 0.6) * env_exp(m, 60)
        return x * 0.6 + sfx('impact')[:n] * 0.25
    if kind == 'photon':
        n = L(length or 0.6); tt = t_(n); f = np.geomspace(400, 2400, n) * (1 + 0.03 * np.sin(2 * np.pi * 30 * tt))
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.linspace(0.1, 1, n) ** 1.5 * 0.3
    if kind == 'snap':
        n = L(1.0); x = np.zeros(n); x[:L(0.008)] = noise(L(0.008)) * 1.0
        x += sfx('impact')[:n] * 0.7
        boing = np.sin(2 * np.pi * np.cumsum(220 * (1 + 0.25 * np.sin(2 * np.pi * 14 * t_(n)) * env_exp(n, 4))) / SR) * env_exp(n, 5) * 0.3
        return x + boing
    if kind == 'rush':
        n = L(length or 3); e = np.minimum(1, np.linspace(0, 6, n)) * np.minimum(1, np.linspace(4, 0, n) + 0.3)
        x = tvlp(noise(n), 500, 4000) * 0.5
        grains = np.zeros(n)
        for _ in range(int((length or 3) * 40)):
            i = rs.integers(0, n - L(0.03)); m = L(0.02); grains[i:i + m] += np.sin(2 * np.pi * rs.uniform(600, 1800) * t_(m)) * np.hanning(m) * 0.35
        return (x + grains) * e * 0.8
    if kind == 'zap':
        n = L(0.6); tt = t_(n)
        x = np.sign(np.sin(2 * np.pi * 120 * tt)) * 0.3 + noise(n) * 0.4 * (rs.random(n) > 0.7)
        x = bp(x, 150, 6000) * env_exp(n, 7)
        return x + sweep(1800, 90, n) * env_exp(n, 9) * 0.4
    if kind == 'click':
        n = L(0.12); return (hp(noise(n), 1500) * env_exp(n, 80) + np.sin(2 * np.pi * 900 * t_(n)) * env_exp(n, 50) * 0.5) * 0.7
    if kind == 'slide':
        n = L(length or 1); return bp(noise(n), 800, 3500) * np.sin(np.pi * np.linspace(0, 1, n)) * 0.25
    if kind == 'blip':
        n = L(0.1); return np.sin(2 * np.pi * 1760 * t_(n)) * env_exp(n, 40) * 0.3
    raise ValueError(kind)

# ---------------------------------------------------------------- MUSIC
BPM = 100; BEAT = 60 / BPM; BAR = 4 * BEAT
def mtof(m): return 440 * 2 ** ((m - 69) / 12)
PROG = [[50, 53, 57, 62], [46, 50, 53, 58], [53, 57, 60, 65], [48, 52, 55, 60]]   # Dm Bb F C
FINAL = [50, 54, 57, 62, 66]                                                        # D major
def additive(f, n, harm=8, bright=1.0, detune=0.0):
    tt = t_(n); x = np.zeros(n)
    for h in range(1, harm + 1):
        if f * h > 12000: break
        a = (1 / h) * np.exp(-(h - 1) * 0.35 / bright)
        x += a * (np.sin(2 * np.pi * f * h * (1 + detune) * tt) + np.sin(2 * np.pi * f * h * (1 - detune) * tt + 1.3))
    return x
def S_(i): return scenes[i]['start']
bloom = [c['t'] for c in cues_doc['cues'] if c['type'] == 'boom'][-1]
sepia_a, sepia_b = [c['t'] for c in cues_doc['cues'] if c['type'] == 'rewind'][0], S_(3)
def section_energy(t):
    """0..1 intensity curve of the score"""
    pts = [(0, .55), (S_(2), .5), (sepia_a, .25), (S_(3), .4), (S_(4), .5), (S_(5), .55), (S_(6), .75), (S_(7), .9), (S_(8), .55), (S_(9), .9), (S_(10), 1.0), (S_(11), .7), (bloom, 1.0), (DUR, .6)]
    xs, ys = zip(*pts); return np.interp(t, xs, ys)

pad = np.zeros(N); bass = np.zeros(N); arp = np.zeros(N); kick = np.zeros(N); hat = np.zeros(N); bell = np.zeros(N)
nbars = int(np.ceil(DUR / BAR)) + 1
for b in range(nbars):
    t0 = b * BAR
    if t0 >= DUR: break
    chord = FINAL if t0 >= bloom - BAR * 0.5 else PROG[b % 4]
    n = min(int(BAR * SR * 1.25), N - int(t0 * SR)); i0 = int(t0 * SR)
    # pad
    p = sum(additive(mtof(m), n, 6, 0.8, 0.003) for m in chord) * adsr(n, 0.6, 0.8) * 0.07
    pad[i0:i0 + n] += p
    # bass: 8th-note pulse with pumping envelope
    root = mtof(chord[0] - 12)
    for k in range(8):
        tk = t0 + k * BEAT / 2; j = int(tk * SR); m = int(BEAT / 2 * SR)
        if j + m > N: break
        bass[j:j + m] += additive(root, m, 5, 0.6) * (1 - np.exp(-t_(m) * 60)) * env_exp(m, 5) * 0.22
    # arpeggio 16ths
    seq = [chord[0] + 12, chord[1] + 12, chord[2] + 12, chord[3] + 12, chord[2] + 24, chord[3] + 12, chord[1] + 12, chord[2] + 12]
    for k in range(16):
        tk = t0 + k * BEAT / 4; j = int(tk * SR); m = int(0.22 * SR)
        if j + m > N: break
        arp[j:j + m] += additive(mtof(seq[k % 8]), m, 4, 1.2) * env_exp(m, 18) * 0.06
    # drums
    for k in range(4):
        tk = t0 + k * BEAT; j = int(tk * SR); m = int(0.4 * SR)
        if j + m > N: break
        kick[j:j + m] += np.sin(2 * np.pi * np.cumsum(45 + 110 * np.exp(-t_(m) * 30)) / SR) * env_exp(m, 9) * 0.6
        for off in (0.5,):
            jj = int((tk + off * BEAT) * SR); mm = int(0.06 * SR)
            if jj + mm < N: hat[jj:jj + mm] += hp(noise(mm), 7000) * env_exp(mm, 70) * 0.25
# 1866 music-box bells
mel = [74, 77, 81, 79, 77, 74, 72, 74, 69, 72, 74, 77]
for k, m in enumerate(mel):
    tk = sepia_a + 0.4 + k * BEAT / 2
    if tk > sepia_b + 0.5: break
    j = int(tk * SR); n = int(1.2 * SR)
    bell[j:j + n] += (np.sin(2 * np.pi * mtof(m) * t_(n)) + 0.3 * np.sin(2 * np.pi * mtof(m) * 4.01 * t_(n))) * env_exp(n, 4) * 0.12

tt = t_(N); E = section_energy(tt)
def gate(a, b, fade=0.4):
    return np.clip((tt - a) / fade, 0, 1) * np.clip((b - tt) / fade, 0, 1)
sep = gate(sepia_a, sepia_b, 0.3)
arp_on = np.clip(gate(S_(3), DUR) + gate(0, S_(2)) * 0.5, 0, 1) * (1 - sep)
kick_on = np.clip(gate(S_(6), S_(8)) + gate(S_(9) + 0.6, S_(11) + 0.2) + gate(bloom, DUR - 1.0), 0, 1)
hat_on = np.clip(gate(S_(9) + 0.6, S_(11)) + gate(bloom, DUR - 1), 0, 1)
# pad lowpass breathing with energy
pad_f = lp(pad, 1800) * (0.6 + 0.6 * E) * (1 - 0.6 * sep) + lp(pad, 500) * 0.6 * sep
music_m = pad_f + bass * E * (1 - 0.7 * sep) + arp * arp_on * E + kick * kick_on * 0.9 + hat * hat_on + bell
# sidechain pump from the kick grid
pump = 1 - 0.25 * kick_on * np.exp(-((tt % BEAT)) * 8)
music_m *= pump
# drop-outs before the big hits for impact
for hit in [c['t'] for c in cues_doc['cues'] if c['type'] in ('boom',)]:
    music_m *= 1 - 0.7 * np.clip(1 - np.abs(tt - (hit - 0.15)) / 0.15, 0, 1)
music = np.stack([music_m, music_m], 1)
# simple stereo widening of the arp
d = int(0.012 * SR); music[d:, 1] += (arp * arp_on * E)[:-d] * 0.4; music[:, 0] += arp * arp_on * E * 0.4
music = lp(music.T, 14000).T

# ---------------------------------------------------------------- SFX bus
fx = np.zeros((N, 2))
for c in cues_doc['cues']:
    x = sfx(c['type'], c.get('len'), c.get('pitch', 0)) * c.get('gain', 1)
    i = int(c['t'] * SR)
    if i >= N or i + len(x) <= 0: continue
    if i < 0: x = x[-i:]; i = 0
    x = x[:N - i]
    pan = {'whoosh': rs.uniform(-.5, .5), 'swoosh': -.3, 'ping': rs.uniform(-.3, .3), 'blip': .3, 'bubbles': rs.uniform(-.4, .4)}.get(c['type'], 0)
    fx[i:i + len(x)] += stereo(x, pan)

# ---------------------------------------------------------------- VO
vo = np.zeros(N)
if not NO_VO:
    for ch in TL['chunks']:
        a, sr = sf.read(f"{VO_DIR}/{ch['i']:02d}.wav")
        a = resample_poly(a, SR, sr); i = int(ch['start'] * SR); a = a[:N - i]; vo[i:i + len(a)] += a
    vo = hp(vo, 70)
    # gentle presence + compression
    vo = vo + bp(vo, 2500, 6000) * 0.25
    vo = vo / (np.abs(vo).max() + 1e-9) * 0.9
    env = np.sqrt(lfilter([1 - 0.999], [1, -0.999], vo ** 2)); g = np.minimum(1, (0.18 / (env + 1e-6)) ** 0.4); vo = vo * g
    vo = vo / (np.abs(vo).max() + 1e-9) * 0.95
# duck music under VO
venv = lfilter([1 - 0.9995], [1, -0.9995], np.abs(vo)); venv = venv / (venv.max() + 1e-9)
duck = 1 - 0.6 * np.clip(venv * 3, 0, 1)
MUS, FXB, VOB = music * duck[:, None] * 0.34, fx * 0.42, stereo(vo, 0) * 1.0
rms = lambda x: float(np.sqrt((x ** 2).mean()))
print("stem rms  music %.3f  fx %.3f  vo %.3f" % (rms(MUS), rms(FXB), rms(VOB)), "peaks", [round(float(np.abs(x).max()), 2) for x in (MUS, FXB, VOB)])
mix = MUS + FXB + VOB
fade = np.clip((DUR - tt) / 1.0, 0, 1); mix *= fade[:, None]
mix = np.tanh(mix * 1.1) / np.tanh(1.1)  # soft limiter; final loudness set by ffmpeg loudnorm
sf.write(OUT, mix.astype(np.float32), SR)
print('wrote', OUT, mix.shape[0] / SR, 's')
