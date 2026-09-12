import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

test.use({ viewport:{width:390,height:844},isMobile:true,hasTouch:true });
// This journey edits only. It must never launch a model comparison.
test('mobile full-width grid supports captured touch drawing without inference', async ({page}) => {
  let comparisons=0;
  page.on('request',request=>{if(request.method()==='POST'&&request.url().endsWith('/api/lab/compare')) comparisons++;});
  await page.goto('/lab');
  await page.getByRole('combobox',{name:'Preset for A'}).selectOption('Black');
  const first=page.getByRole('button',{name:'A pixel row 1 column 1: 0'});
  await first.scrollIntoViewIfNeeded();
  const grid=page.getByRole('group',{name:'Pattern A pixels'});
  const gridBox=await grid.boundingBox();expect(gridBox!.width).toBeGreaterThan(310);
  const cells=await Promise.all([1,2,3].map(column=>page.getByRole('button',{name:`A pixel row 1 column ${column}: 0`}).boundingBox()));
  const session=await page.context().newCDPSession(page);
  const point=(index:number)=>({x:cells[index]!.x+cells[index]!.width/2,y:cells[index]!.y+cells[index]!.height/2});
  await session.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[point(0)]});
  await session.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[point(1)]});
  await session.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[point(2)]});
  await session.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  for(const column of [1,2,3]) await expect(page.getByRole('button',{name:`A pixel row 1 column ${column}: 255`})).toBeVisible();
  await expect(page.getByRole('button',{name:'B pixel row 1 column 1: 0'})).toBeAttached();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await expect(page.getByRole('region',{name:'Comparison result'})).toHaveCount(0);
  expect(comparisons).toBe(0);
  await page.evaluate(()=>window.scrollTo(0,0));
  const review=path.resolve('../artifacts/milestones/P00/review');await mkdir(review,{recursive:true});
  await page.screenshot({path:path.join(review,'mobile-editor-final.png'),fullPage:true});
});
