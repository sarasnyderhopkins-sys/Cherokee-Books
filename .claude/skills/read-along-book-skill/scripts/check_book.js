// Smoke test for a built book: opens index.html in headless Chromium, presses Begin, turns pages, saves screenshots.
//   node scripts/check_book.js [book folder]        (needs Playwright: npm i -g playwright, or set PLAYWRIGHT_PATH)
const path = require('path');
const fs = require('fs');
let chromium;
for (const p of [process.env.PLAYWRIGHT_PATH, '/opt/node22/lib/node_modules/playwright', 'playwright'].filter(Boolean)) {
  try { chromium = require(p).chromium; break; } catch (e) {}
}
if (!chromium) { console.log('Playwright not found; open index.html in a browser and check by hand.'); process.exit(0); }
const folder = path.resolve(process.argv[2] || '.');
const shots = path.join(folder, 'build', 'shots'); fs.mkdirSync(shots, { recursive: true });
(async () => {
  const errors = [];
  const b = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
  const ctx = await b.newContext({ viewport: { width: 1100, height: 720 } });
  const p = await ctx.newPage();
  p.on('pageerror', e => errors.push(e.message));
  const state = () => p.evaluate(() => ({ counter: document.querySelector('#counter').textContent, caption: document.getElementById('caption').classList.contains('show'),
    text: document.getElementById('capSyl').textContent.slice(0, 40), cover: !document.getElementById('cover').hidden }));
  await p.goto('file://' + path.join(folder, 'index.html'));
  await p.waitForTimeout(1200);
  await p.screenshot({ path: path.join(shots, 'cover.png') });
  const s0 = await state();
  await p.click('#begin'); await p.waitForTimeout(7000);
  const s1 = await state();
  await p.screenshot({ path: path.join(shots, 'page-1.png') });
  const canNext = !(await p.$eval('#next', b => b.disabled));
  if (canNext) { await p.click('#next'); await p.waitForTimeout(1500); }
  const s2 = await state();
  await p.screenshot({ path: path.join(shots, 'page-2.png') });
  await p.setViewportSize({ width: 390, height: 780 }); await p.waitForTimeout(600);
  await p.screenshot({ path: path.join(shots, 'phone.png') });
  await b.close();
  const ok = s0.cover && !s1.cover && s1.caption && (!canNext || s2.counter.startsWith('2')) && !errors.length;
  console.log(JSON.stringify({ cover: s0, afterBegin: s1, afterNext: s2, errors }, null, 1));
  console.log(ok ? `OK — screenshots in ${shots}` : 'CHECK FAILED — look at the screenshots and errors above');
  process.exit(ok ? 0 : 1);
})();
