import { chromium } from "playwright";

const API='http://127.0.0.1:8000';
const WEB='http://127.0.0.1:5173';

async function api(path, options={}){ const r=await fetch(`${API}${path}`, options); const t=await r.text(); let b=null; try{b=t?JSON.parse(t):null}catch{b=t}; return {ok:r.ok,status:r.status,body:b}; }
const phone = `+2126${String(Date.now()).slice(-8)}`;
const password='secret123';
await api('/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({full_name:'QA Hist',phone,role:'farmer',password,terms_accepted:true,data_consent_accepted:true,consent_version:'2026-04-13'})});
const login=await api('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({phone,password,legal_acknowledged:true})});
const s=login.body; const auth={Authorization:`Bearer ${s.access_token}`,'Content-Type':'application/json'};
await api('/olive-land-pieces',{method:'POST',headers:auth,body:JSON.stringify({piece_name:'Hist Piece',season_year:2025})});
const season=await api('/olive-seasons',{method:'POST',headers:auth,body:JSON.stringify({season_year:2025,land_pieces:1,land_piece_name:'Hist Piece',tanks_20l:9,tanks_taken_home_20l:8,pressing_cost_mode:'oil_tanks',pressing_cost:0})});
const seasonId=season.body.id;

const browser=await chromium.launch({headless:true});
const page=await browser.newPage();
await page.goto(`${WEB}/index.html`);
await page.evaluate((sess)=>localStorage.setItem('worker_radar_session', JSON.stringify(sess)), s);
await page.goto(`${WEB}/olive-season.html`,{waitUntil:'networkidle'});
await page.click('#olive-mode-usage');
await page.waitForFunction(()=>{const sel=document.querySelector('#usage-season-id'); return !!sel && sel.options.length>0;});
await page.selectOption('#usage-season-id', seasonId);
await page.waitForTimeout(300);
await page.selectOption('#usage-inventory-item-id', `season_tanks:${seasonId}`);
await page.fill('input[name="usage_quantity_used"]','1');
await page.fill('input[name="usage_type"]','hist_ok');
await page.click('#usage-form button[type="submit"]');
await page.waitForTimeout(2500);
const txt = await page.$eval('#usage-history-list', el => el.innerText);
console.log(txt);
await browser.close();


