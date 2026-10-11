import { test, expect } from '@playwright/test';
test('capture desktop and mobile renders',async ({page})=>{
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.setViewportSize({width:1440,height:1000});await page.goto('/');
 await expect(page.locator('.preloader')).toHaveCount(0,{timeout:25000});
 await expect(page.locator('canvas')).toHaveCount(3);await expect(page.locator('.scene-fallback')).toHaveCount(0);
 await page.waitForTimeout(800);await page.screenshot({path:'artifacts/journey-01-sky.png'});
 async function goTo(progress,phase){
   await page.evaluate(p=>{const section=document.querySelector('.opening-journey');const stage=document.querySelector('.opening-viewport');window.scrollTo({top:section.offsetTop+p*(section.offsetHeight-stage.offsetHeight),behavior:'instant'});},progress);
   await expect(page.locator('.opening-viewport')).toHaveAttribute('data-phase',phase);
   await page.waitForTimeout(500);
 }
 await goTo(.3,'clouds');await page.screenshot({path:'artifacts/journey-02-clouds.png'});
 await goTo(.56,'window');await page.screenshot({path:'artifacts/journey-03-window.png'});
 const above=Number(await page.locator('.opening-viewport').getAttribute('data-camera-y'));expect(above).toBeGreaterThan(-25);
 await goTo(.67,'emerge');
 const below=Number(await page.locator('.opening-viewport').getAttribute('data-camera-y'));expect(below).toBeLessThan(-25);
 await expect(page.locator('.journey-product')).toHaveAttribute('inert','');
 await goTo(.9,'pod');await expect(page.locator('.journey-product')).not.toHaveAttribute('inert','');
 await expect(page.locator('.opening-viewport')).toHaveAttribute('data-camera-pitch','0.000');
 await page.screenshot({path:'artifacts/journey-04-pod.png'});
 await goTo(.56,'window');expect(Number(await page.locator('.opening-viewport').getAttribute('data-camera-y'))).toBeGreaterThan(-25);
 await page.locator('#twin').scrollIntoViewIfNeeded();await page.waitForTimeout(400);await page.screenshot({path:'artifacts/desktop-demo.png'});
 await page.setViewportSize({width:390,height:844});await page.goto('/');await expect(page.locator('.preloader')).toHaveCount(0,{timeout:25000});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.waitForTimeout(500);await page.screenshot({path:'artifacts/mobile-journey-sky.png'});
 await goTo(.56,'window');await page.screenshot({path:'artifacts/mobile-journey-window.png'});
 await goTo(.9,'pod');await page.screenshot({path:'artifacts/mobile-journey-pod.png'});
 expect(errors).toEqual([]);
});
