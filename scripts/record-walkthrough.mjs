import { chromium } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';

const out=path.resolve('artifacts/video');
const scenes=JSON.parse(await fs.readFile(path.join(out,'scenes.json'),'utf8'));
const browser=await chromium.launch({headless:true,executablePath:path.resolve('node_modules/playwright-core/.local-browsers/chromium-1248/chrome-win64/chrome.exe'),args:['--disable-webgl']});
const context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce',recordVideo:{dir:out,size:{width:1440,height:900}}});
await context.addInitScript(()=>localStorage.setItem('theme-storage',JSON.stringify({state:{theme:{type:'light',color:'#c4d8e5'}},version:0})));
const page=await context.newPage();
const clockStart=Date.now();
page.on('pageerror',error=>console.log('Page error:',error.message));
await page.goto('http://127.0.0.1:8001/',{waitUntil:'domcontentloaded'});
await page.locator('#twin').waitFor({timeout:30000});
await page.locator('.preloader').waitFor({state:'detached',timeout:25000});
await page.locator('.twin-map').waitFor({timeout:30000});
await page.addStyleTag({content:'.site-header{display:none!important}.twin-section{padding-top:24px}.twin-shell{box-shadow:none}#video-caption{position:fixed;z-index:99999;left:32px;right:32px;bottom:22px;background:#122630f2;color:#f3eee5;padding:20px 26px;border-radius:12px;box-shadow:0 10px 45px #0003;border:1px solid #ffffff25;font-family:Arial,sans-serif}#video-caption small{color:#efb083;font-size:11px;letter-spacing:2px;display:block;margin-bottom:8px}#video-caption h2{font-size:28px;line-height:1.15;margin:0 0 8px;letter-spacing:-.5px}#video-caption p{font-size:16px;line-height:1.45;margin:0;max-width:1100px}#video-badge{position:fixed;z-index:99999;right:32px;top:22px;background:#122630ed;color:#f3eee5;border-radius:30px;padding:10px 16px;font:11px Arial,sans-serif;letter-spacing:1px}'});
await page.evaluate(()=>{const caption=document.createElement('div');caption.id='video-caption';document.body.appendChild(caption);const badge=document.createElement('div');badge.id='video-badge';badge.textContent='ATMOS • SYNTHETIC DEMO';document.body.appendChild(badge)});
async function focus(selector){await page.locator(selector).first().evaluate(element=>window.scrollTo({top:element.getBoundingClientRect().top+window.scrollY-25,behavior:'instant'}));}
async function caption(scene,index){await page.evaluate(({scene,index,total})=>{const box=document.querySelector('#video-caption');box.replaceChildren();const tag=document.createElement('small');tag.textContent=`${String(index+1).padStart(2,'0')} / ${total} • PROJECT WALKTHROUGH`;const title=document.createElement('h2');title.textContent=scene.title;const description=document.createElement('p');description.textContent=scene.caption;box.append(tag,title,description)},{scene,index,total:scenes.length})}

const timeline=[];
let firstStart;
for(let i=0;i<scenes.length;i++){
  const scene=scenes[i];
  if(scene.id==='problem')await focus('#idea');
  if(scene.id==='map'){
    if(await page.getByRole('button',{name:'Demo',exact:true}).getAttribute('aria-pressed')!=='true'){await page.getByRole('button',{name:'Demo',exact:true}).click();await page.locator('.twin-map').waitFor({timeout:30000});}
    await page.getByRole('tab',{name:'Forecast',exact:true}).click();
    await focus('.twin-shell');
  }
  if(scene.id==='forecast'){
    await page.getByRole('button',{name:'Select Delhi'}).click();
    await focus('.twin-shell');
  }
  if(scene.id==='scenario'){
    await page.getByRole('tab',{name:'Scenario',exact:true}).click();
    await page.getByRole('button',{name:'Rainy',exact:true}).click();
    await focus('.twin-shell');
  }
  if(scene.id==='upload'){
    await focus('.import-workspace');
    await page.getByLabel('Dataset',{exact:true}).selectOption('wind');
    await page.getByLabel('Source / provenance').fill('Example user supplied weather');
    const now=new Date();now.setUTCMinutes(0,0,0);
    await page.getByLabel('CSV contents').fill(`city_id,time,speed_kmh,direction_deg,rain_mm,cloud_cover_pct\ndelhi,${now.toISOString()},20,310,6,85\n`);
  }
  if(scene.id==='impact'){
    if(await page.getByRole('button',{name:'Demo',exact:true}).getAttribute('aria-pressed')!=='true'){await page.getByRole('button',{name:'Demo',exact:true}).click();await page.locator('.twin-map').waitFor({timeout:30000});}
    await page.getByRole('tab',{name:'Impact',exact:true}).click();
    await focus('.twin-shell');
  }
  if(scene.id==='agents'){
    await page.getByRole('tab',{name:'Workflow',exact:true}).click();
    await focus('.mission-control');
    await page.getByRole('button',{name:'Run city analysis'}).click();
  }
  if(scene.id==='evidence'){
    await page.locator('.run-summary>b').filter({hasText:'COMPLETE'}).waitFor({timeout:30000});
    await page.getByRole('tab',{name:'Action plan',exact:true}).click();
    await focus('.mission-control');
  }
  if(scene.id==='aws'){
    await page.locator('.build-it-runtime').evaluate(element=>element.open=true);
    await focus('.build-it-runtime');
  }
  await caption(scene,i);
  const start=(Date.now()-clockStart)/1000;
  if(firstStart==null)firstStart=start;
  timeline.push({...scene,start:start-firstStart});
  console.log(`Recording ${scene.id} (${scene.duration.toFixed(1)}s)`);
  const until=Date.now()+(scene.duration+2)*1000;
  await page.screenshot({path:path.join(out,scene.id+'.png')});
  if(scene.id==='map'){
    await page.waitForTimeout(4000);
    await page.getByRole('button',{name:'Select Chandigarh'}).click();
    await page.waitForTimeout(3000);
    await page.getByRole('button',{name:'Select Delhi'}).click();
  }
  if(scene.id==='upload'){
    await page.waitForTimeout(4500);
    const button=page.getByRole('button',{name:'Import into live storage'});
    await button.evaluate(element=>element.scrollIntoView({block:'center'}));
    await button.click();
    await focus('.import-workspace');
  }
  if(scene.id==='evidence'){
    await page.waitForTimeout(4000);
    await page.locator('.action-board select').first().selectOption('done');
    await page.waitForTimeout(3000);
    await page.getByRole('tab',{name:'Evidence library',exact:true}).click();
    await focus('.mission-control');
  }
  // One-second lead and tail keep the voice away from scene changes.
  await page.waitForTimeout(Math.max(0,until-Date.now()));
}
const duration=(Date.now()-clockStart)/1000-firstStart;
await page.screenshot({path:path.join(out,'walkthrough-poster.png')});
const video=page.video();
await context.close();
const videoPath=await video.path();
await browser.close();
await fs.writeFile(path.join(out,'timeline.json'),JSON.stringify({videoPath,trimStart:firstStart,duration,scenes:timeline},null,2));
console.log('Saved recording:',videoPath);
