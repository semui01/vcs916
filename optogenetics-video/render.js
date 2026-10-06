// Usage: node render.js stills out_dir t1 t2 ...   |   node render.js video out_dir [workers] [fps]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs'), path = require('path');
const [mode, outDir, ...rest] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const url = 'file://' + path.resolve(__dirname, 'anim.html') + '#render';

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  page.on('console', m => { if (m.type() === 'error') console.error('CONSOLE', m.text()); });
  await page.goto(url); await page.evaluate(() => window.ready);
  return page;
}
const grab = (page, t, q) => page.evaluate(([t, q]) => { render(t); return document.getElementById('c').toDataURL('image/jpeg', q).split(',')[1]; }, [t, q]);

(async () => {
  const browser = await chromium.launch({ args: ['--disable-gpu-vsync', '--enable-gpu-rasterization', '--ignore-gpu-blocklist'] });
  if (mode === 'stills') {
    const page = await openPage(browser);
    fs.writeFileSync(path.join(outDir, 'cues.json'), JSON.stringify(await page.evaluate(() => ({ cues: CUES, scenes: SCENES, duration: DURATION })), null, 1));
    for (const ts of rest) { const b64 = await grab(page, +ts, 0.85); fs.writeFileSync(path.join(outDir, `t${(+ts).toFixed(2).padStart(6, '0')}.jpg`), Buffer.from(b64, 'base64')); }
  } else {
    const workers = +(rest[0] || 4), fps = +(rest[1] || 30);
    const page0 = await openPage(browser);
    const { duration } = await page0.evaluate(() => ({ duration: DURATION }));
    fs.writeFileSync(path.join(outDir, 'cues.json'), JSON.stringify(await page0.evaluate(() => ({ cues: CUES, scenes: SCENES, duration: DURATION })), null, 1));
    await page0.close();
    const total = Math.round(duration * fps), per = Math.ceil(total / workers), t0 = Date.now();
    let done = 0;
    await Promise.all(Array.from({ length: workers }, async (_, w) => {
      const a = w * per, b = Math.min(total, a + per);
      const page = await openPage(browser);
      const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '14', '-pix_fmt', 'yuv420p', '-r', String(fps), path.join(outDir, `seg${w}.mp4`)], { stdio: ['pipe', 'inherit', 'inherit'] });
      for (let f = a; f < b; f++) {
        const buf = Buffer.from(await grab(page, f / fps, 0.94), 'base64');
        if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
        if (++done % 150 === 0) console.log(`${done}/${total} frames  ${((Date.now() - t0) / 1000).toFixed(0)}s`);
      }
      ff.stdin.end(); await new Promise(r => ff.on('close', r)); await page.close();
    }));
    fs.writeFileSync(path.join(outDir, 'segs.txt'), Array.from({ length: workers }, (_, w) => `file 'seg${w}.mp4'`).join('\n'));
    console.log('render done in', ((Date.now() - t0) / 1000).toFixed(0), 's');
  }
  await browser.close();
})();
