import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const base = 'http://127.0.0.1:8765/';
const browser = await chromium.launch({headless: true});
try {
  const desktop = await browser.newPage({viewport:{width:1365,height:900}});
  await desktop.goto(base + 'index.html');
  const card = desktop.locator('a.project.card-link').filter({hasText:'Pawsitive Care'});
  assert.equal(await card.count(), 1, 'Homepage needs one clickable Pawsitive Care card');
  await card.click();
  await desktop.waitForURL('**/pawsitive-preview.html');
  assert.match(await desktop.locator('h1').innerText(), /Pawsitive Care/);
  assert.match(await desktop.locator('.pet').innerText(), /Milo/);
  await desktop.locator('[data-tab="history"]').click();
  assert.equal(await desktop.locator('[data-pane="history"]').isVisible(), true);
  assert.equal(await desktop.locator('[data-pane="home"]').isVisible(), false);
  console.log('PASS: Pawsitive card and read-only preview navigation');

  await desktop.goto(base + 'work.html#pawfect');
  await desktop.waitForTimeout(300);
  const top = await desktop.locator('#pawfect').evaluate(el => el.getBoundingClientRect().top);
  assert.ok(top >= -30 && top < 320, 'Pawsitive case-study anchor did not scroll to project: ' + top);
  console.log('PASS: Deep link to Pawsitive case study');

  await desktop.goto(base + 'projects.html');
  await desktop.locator('a[href="weather-traffic-overview.html"]').click();
  await desktop.waitForURL('**/weather-traffic-overview.html');
  assert.match(await desktop.locator('h1').innerText(), /weather and traffic congestion/i);
  assert.equal(await desktop.locator('.story-card').count(), 3);
  console.log('PASS: Weather project opens the actual three-part overview');

  await desktop.goto(base + 'projects.html#connecticut-mortality');
  await desktop.locator('#connecticut-mortality img').waitFor({state:'visible'});
  const imageLoaded = await desktop.locator('#connecticut-mortality img').evaluate(el => el.complete && el.naturalWidth > 0);
  assert.ok(imageLoaded, 'Connecticut screenshot did not load');
  console.log('PASS: Connecticut dashboard screenshot');

  for (const file of [
    'projects/dashboards/healthcare-analytics-tableau-expanded.twbx',
    'projects/dashboards/us-border-crossings-interactive-dashboard.twbx',
    'projects/dashboards/connecticut-drug-related-mortality-tableau-revised.twbx',
    'projects/dashboards/connecticut-drug-related-mortality-power-bi.pbix'
  ]) {
    const res = await desktop.request.head(base + file);
    assert.equal(res.status(),200,file+' missing from HTTP server');
  }
  console.log('PASS: Four major workbook/download URLs return HTTP 200');

  await desktop.screenshot({path:'portfolio-projects-desktop.png',fullPage:true});
  const mobile = await browser.newPage({viewport:{width:390,height:844},isMobile:true,deviceScaleFactor:1});
  for (const page of ['index.html','projects.html','work.html','pawsitive-preview.html','weather-traffic-overview.html']) {
    await mobile.goto(base + page);
    await mobile.waitForLoadState('domcontentloaded');
    const dimensions = await mobile.evaluate(() => ({
      viewport: window.innerWidth,
      documentWidth: document.documentElement.scrollWidth,
      mainWidth: document.querySelector('main')?.getBoundingClientRect().width ?? 0
    }));
    assert.ok(dimensions.documentWidth <= dimensions.viewport + 3,
      page+' has horizontal overflow: '+JSON.stringify(dimensions));
    console.log('PASS: Mobile width',page,JSON.stringify(dimensions));
  }
  await mobile.goto(base + 'pawsitive-preview.html');
  await mobile.screenshot({path:'portfolio-preview-mobile.png',fullPage:true});
  console.log('All browser checks passed');
} finally {
  await browser.close();
}
