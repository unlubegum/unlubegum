// video.html'i kare kare çekip MP4'e çevirir:  node render.js <kare-klasörü>
const { chromium } = require('playwright');
const path = require('path');
const FPS = 30;
(async () => {
  const dir = process.argv[2];
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 540, height: 960 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.join(__dirname, 'video.html') + '#capture');
  const dur = await p.evaluate(() => DURATION);
  for (let i = 0; i < dur * FPS; i++) {
    await p.evaluate(t => render(t), i / FPS);
    await p.screenshot({ path: `${dir}/f${String(i).padStart(5, '0')}.png` });
  }
  await b.close();
})();
