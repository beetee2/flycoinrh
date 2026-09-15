import { test, expect } from '@playwright/test';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

// Real local API and full model. One explicit comparison = 9 attempted calls.
// No route mocks, cached responses, fixture service, or automatic retries.
test('real pixels to retina to response and downloadable JSON on desktop and mobile', async ({page}) => {
  const review=path.resolve('..', process.env.FLYJAM_LAB_EVIDENCE ?? 'artifacts/checks/lab/real-browser', 'review');await mkdir(review,{recursive:true});
  await page.goto('/lab');
  await expect(page.getByRole('status',{name:'Local model status'})).toContainText('Ready');
  await expect(page.getByRole('button',{name:/Run comparison/})).toBeEnabled();
  await page.getByRole('combobox',{name:'Preset for A'}).selectOption('Vertical stripes');
  await page.getByRole('combobox',{name:'Preset for B'}).selectOption('Horizontal stripes');
  // Exercise a keyboard edit with known exact grayscale value, then restore equal-brightness preset.
  await page.getByRole('button',{name:'A pixel row 1 column 1: 0'}).focus();await page.keyboard.press('Enter');
  await expect(page.getByRole('button',{name:'A pixel row 1 column 1: 255'})).toBeVisible();
  await page.getByRole('combobox',{name:'Preset for A'}).selectOption('Vertical stripes');
  await page.screenshot({path:path.join(review,'desktop-editor.png'),fullPage:true});
  const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/lab/compare')&&r.request().method()==='POST',{timeout:110_000});
  await page.getByRole('button',{name:/Run comparison/}).click();
  await expect(page.getByRole('button',{name:/Running comparison/})).toBeDisabled();
  await expect(page.getByRole('status',{name:'Local model status'})).toContainText('Busy');
  const health = await page.request.get('/health/live');expect(health.status()).toBe(200);
  const response=await responsePromise;expect(response.status()).toBe(200);const result=await response.json();
  const submitted=response.request().postDataJSON();expect(result.request).toEqual(submitted);
  expect(result.fixture).toBe(false);expect(result.cached).toBe(false);expect(result.samples).toHaveLength(9);
  expect(result.seeds).toEqual([17,29,43]);expect(result.comparison.equal_brightness).toBe(true);expect(result.comparison.same_seed_repeatable).toBe(true);
  await expect(page.getByRole('region',{name:'Comparison result'})).toBeVisible();
  await expect(page.getByText(/input drive is not neuron firing/)).toBeVisible();
  await expect(page.getByText(/Matching motor rates do not establish identical whole-brain activity/)).toBeVisible();
  for(const side of ['A','B']) {
    const key=side==='A'?'a':'b';
    expect(result.request[key]).toHaveLength(256);
    await page.getByText(`All 256 pixel values · ${side}`,{exact:true}).click();
    const text=await page.getByTestId(`submitted-${side}`).innerText();expect(text.trim().split(/\s+/).map(Number)).toEqual(result.request[key]);
    await page.getByText(`All 256 pixel values · ${side}`,{exact:true}).click();
    expect(result.retina[side].sampled_pixel_count).toBeGreaterThan(0);
    expect(result.retina[side].discarded_pixel_indices.length).toBe(256-result.retina[side].sampled_pixel_count);
    for(const popName of ['L1','L2']) {
      const pop=result.retina[side].populations[popName];const sums=Array(256).fill(0);
      pop.pixel_indices.forEach((pixel:number,i:number)=>{sums[pixel]+=pop.drive_hz[i];});
      const expected=sums.map((sum:number,i:number)=>`Pixel ${i}: ${pop.coverage_counts[i] ? sum/pop.coverage_counts[i] : 'unsampled'}`);
      const map=page.getByRole('img',{name:`${side} ${popName} input drive in Hz, not neuron firing`,exact:true});
      expect(await map.locator('rect title').allTextContents()).toEqual(expected);
    }
  }
  const fmt=(n:number)=>Number.isInteger(n)?String(n):n.toFixed(4);
  for(const sample of result.samples) for(const [motor,rate] of Object.entries(sample.motor_rates_hz)) {
    await expect(page.getByTestId(`rate-${sample.side}-${sample.seed}-${motor}`)).toHaveText(fmt(rate as number));
  }
  for(const [motor,metric] of Object.entries(result.comparison.motor_rates_hz)) {
    const d=metric as {a_mean:number;a_sd:number};await expect(page.getByTestId(`mean-A-${motor}`)).toHaveText(`${fmt(d.a_mean)} ± ${fmt(d.a_sd)}`);
  }
  const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Download result JSON'}).click();
  const download=await downloadPromise;const resultPath=path.join(review,'browser-result.json');await download.saveAs(resultPath);
  expect(JSON.parse(await readFile(resultPath,'utf8'))).toEqual(result);
  await writeFile(path.join(review,'browser-submitted.json'),JSON.stringify(submitted,null,2)+'\n');
  await page.getByText('Existing neural statistics · all samples',{exact:true}).click();
  for(const sample of result.samples) for(const [stat,value] of Object.entries(sample.statistics)) {
    await expect(page.getByTestId(`stat-${sample.side}-${sample.seed}-${stat}`)).toHaveText(fmt(value as number));
  }
  await page.screenshot({path:path.join(review,'desktop-result.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await expect(page.getByRole('button',{name:'Download result JSON'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.screenshot({path:path.join(review,'mobile-result.png'),fullPage:true});
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:path.join(review,'mobile-editor.png')});
  await page.getByRole('combobox',{name:'Preset for A'}).selectOption('Black');
  await expect(page.getByText(/Editors changed after this run/)).toBeVisible();
});
