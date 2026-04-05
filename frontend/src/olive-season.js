import "./ui-feedback.js";
import { requireRole as Ne, renderAppTabs as Ce, clearSession as ge, authHeaders as b } from "./session.js";import { API_BASE as v } from "./config.js";const D=Ne("farmer","./workers.html"),ae=document.getElementById("role-hint"),Me=document.getElementById("logout-btn"),oe=document.getElementById("app-tabs"),o=document.getElementById("olive-season-form"),V=document.getElementById("olive-season-message"),P=document.getElementById("olive-seasons-list"),ie=document.getElementById("season-progress"),Pe=document.getElementById("refresh-seasons-btn"),Fe=document.getElementById("reset-form-btn"),J=document.getElementById("delete-season-btn"),me=document.getElementById("kg-needed-per-tank"),ve=document.getElementById("toggle-insights-btn"),De=document.getElementById("olive-insights-embed"),He=document.getElementById("refresh-finance-btn"),m=document.getElementById("finance-season-id"),W=document.getElementById("budget-summary-kpis"),Y=document.getElementById("budget-comparison-chart"),G=document.getElementById("budget-piece-table-body"),y=document.getElementById("labor-day-form"),re=document.getElementById("labor-day-message"),pe=document.getElementById("labor-days-list"),u=document.getElementById("sale-form"),le=document.getElementById("sale-message"),_e=document.getElementById("sales-list"),E=document.getElementById("sale-type-select"),B=document.getElementById("sale-custom-item-select"),k=document.getElementById("usage-form"),ce=document.getElementById("usage-message"),je=document.getElementById("usage-list"),w=document.getElementById("usage-inventory-item-id"),ye=document.getElementById("olive-mode-season"),fe=document.getElementById("olive-mode-budget"),he=document.getElementById("olive-mode-usage"),be=document.getElementById("olive-mode-inventory"),qe=document.getElementById("olive-view-season"),Ae=document.getElementById("olive-view-budget"),Ue=document.getElementById("olive-view-usage"),Oe=document.getElementById("olive-view-inventory"),Re=document.getElementById("refresh-usage-btn"),g=document.getElementById("usage-season-id"),Ke=document.getElementById("refresh-inventory-embed-btn"),de=document.getElementById("olive-inventory-frame");let f=[],$e=[],ke=[],S=[],F=!1,we="season";D&&ae&&(ae.textContent=`Logged in as ${D.user.full_name} (farmer).`);D&&oe&&Ce(oe,D.user.role,"olive-season.html");Me.addEventListener("click",()=>{ge(),window.location.href="./login.html"});function L(e,t=!0){V.textContent=e,V.className=`message ${t?"success":"error"}`}function N(e,t=!0){re.textContent=e,re.className=`message ${t?"success":"error"}`}function C(e,t=!0){le.textContent=e,le.className=`message ${t?"success":"error"}`}function T(e,t=!0){ce.textContent=e,ce.className=`message ${t?"success":"error"}`}function Ee(){return String((E==null?void 0:E.value)||"oil_tank").trim()}function z(){const e=Ee(),t=Array.from(u.querySelectorAll("[data-sale-type]"));for(const n of t){const a=String(n.getAttribute("data-sale-type")||"").split(",").map(r=>r.trim()).filter(Boolean).includes(e);n.classList.toggle("is-hidden",!a);const d=n.querySelector("input, select, textarea");d&&(a||(d.value=""))}}function We(e){return e==="raw_kg"?"Raw Olives (KG)":e==="processed_container"?"Processed Containers":e==="soap"?"Soap":e==="custom_item"?"Custom Item":"Oil Tanks"}function Ye(){return new Date().getFullYear()}function i(e){const t=String(e??"").trim();if(!t)return null;const n=Number(t);return Number.isFinite(n)?n:null}function c(e){const t=i(e);return t===null?"-":t.toFixed(2)}function x(e){return`${Number(e||0).toFixed(2)}`}function ut(e){const t=i(e==null?void 0:e.total_cost)??0,n=i(e==null?void 0:e.labor_cost_total)??t,s=i(e==null?void 0:e.pressing_cost_money_equivalent);if((e==null?void 0:e.pressing_cost_mode)==="oil_tanks"){if(s!==null)return x(t);const a=i(e==null?void 0:e.pressing_cost_oil_tanks_20l)??0;return a>0?`${x(n)} + ${x(a)} tanks`:x(n)}return x(t)}function Ge(e){return String(e||"").trim()}function Ve(e,t,n){const s=e!==null?e:t;return s===null||n===null||n<=0?"-":(s/n).toFixed(2)}function parseApiDetailMessage(e){if(!e)return null;if(typeof e==="string")return e;if(Array.isArray(e)){for(const t of e){const n=parseApiDetailMessage(t);if(n)return n}return null}if(typeof e==="object"){if(typeof e.msg==="string"&&e.msg.trim())return e.msg;for(const t of ["detail","error","message"]){const n=parseApiDetailMessage(e[t]);if(n)return n}if(Array.isArray(e.errors)){for(const t of e.errors){const n=parseApiDetailMessage(t);if(n)return n}}}return null}async function p(e,t={}){const n=await fetch(e,{headers:b(),...t});if(n.status===401||n.status===403)return ge(),window.location.href="./login.html",null;if(!n.ok){let d=null,r="";try{d=await n.json()}catch{r=(await n.text().catch(()=>"")).trim()}const a=parseApiDetailMessage(d)||r||`Request failed (${n.status})`;throw new Error(a)}return n.status===204?null:n.json()}function Je(){return{season_year:Number(o.elements.season_year.value),land_pieces:Number(o.elements.land_pieces.value||1),land_piece_name:Ge(o.elements.land_piece_name.value),estimated_chonbol:i(o.elements.estimated_chonbol.value),actual_chonbol:i(o.elements.actual_chonbol.value),kg_per_land_piece:i(o.elements.kg_per_land_piece.value),tanks_20l:i(o.elements.tanks_20l.value),tanks_taken_home_20l:i(o.elements.tanks_taken_home_20l.value),pressing_cost_mode:String(o.elements.pressing_cost_mode.value||"money"),pressing_cost:i(o.elements.pressing_cost.value),pressing_cost_oil_tanks_20l:i(o.elements.pressing_cost_oil_tanks_20l.value),pressing_cost_oil_tank_unit_price:i(o.elements.pressing_cost_oil_tank_unit_price.value),notes:String(o.elements.notes.value||"").trim()||null}}function Se(){const e=i(o.elements.kg_per_land_piece.value),t=i(o.elements.actual_chonbol.value),n=i(o.elements.tanks_20l.value);me.value=Ve(e,t,n)}function H(){o.reset(),o.elements.season_id.value="",o.elements.land_pieces.value="1",o.elements.season_year.value=String(Ye()),J.hidden=!0,me.value="-",L("",!0),V.className="message"}function ze(e){o.elements.season_id.value=e.id,o.elements.season_year.value=String(e.season_year),o.elements.land_pieces.value=String(e.land_pieces??1),o.elements.land_piece_name.value=e.land_piece_name||"",o.elements.estimated_chonbol.value=e.estimated_chonbol??"",o.elements.actual_chonbol.value=e.actual_chonbol??"",o.elements.kg_per_land_piece.value=e.kg_per_land_piece??"",o.elements.tanks_20l.value=e.tanks_20l??"",o.elements.tanks_taken_home_20l.value=e.tanks_taken_home_20l??"",o.elements.pressing_cost_mode.value=e.pressing_cost_mode||"money",o.elements.pressing_cost.value=e.pressing_cost??"",o.elements.pressing_cost_oil_tanks_20l.value=e.pressing_cost_oil_tanks_20l??"",o.elements.pressing_cost_oil_tank_unit_price.value=e.pressing_cost_oil_tank_unit_price??"",o.elements.notes.value=e.notes||"",J.hidden=!1,Se()}function j(e){const t=[];return String(e.land_piece_name||"").trim()||t.push("piece name"),i(e.kg_per_land_piece)===null&&t.push("kg per land piece"),(i(e.tanks_20l)===null||Number(e.tanks_20l)<=0)&&t.push("tanks produced"),t}function Qe(e){const t=j(e);return t.length?`<span class="badge draft" title="Missing: ${t.join(", ")}">Draft (${t.length} missing)</span>`:'<span class="badge available">Complete</span>'}function ue(e){if(!ie)return;const t=e.length,n=e.filter(s=>j(s).length>0).length;ie.textContent=`Drafts: ${n} / ${t}`}function Xe(e){const t=j(e),n=t.length?`<div class="full season-missing"><strong>Missing:</strong> ${t.join(", ")}</div>`:'<div class="full season-missing complete">All key info completed.</div>';return`
    <article class="worker-card" data-season-id="${e.id}">
      <div class="list-head">
        <h3>${e.land_piece_name||"Unnamed Piece"}</h3>
        <div class="actions-row season-badges">
          <span class="badge day">Season ${e.season_year}</span>
          ${Qe(e)}
          <span class="badge day">${e.kg_needed_per_tank??"-"} kg / tank</span>
        </div>
      </div>
      <div class="worker-grid">
        <div><strong>Estimated Chonbol:</strong> ${e.estimated_chonbol??"-"}</div>
        <div><strong>Actual Chonbol:</strong> ${e.actual_chonbol??"-"}</div>
        <div><strong>KG per Piece:</strong> ${e.kg_per_land_piece??"-"}</div>
        <div><strong>Tanks (20L):</strong> ${e.tanks_20l??"-"}</div>
        <div><strong>Tanks Taken Home:</strong> ${e.tanks_taken_home_20l??"-"}</div>
        <div><strong>Pressing Cost:</strong> ${e.pressing_cost_mode==="oil_tanks"?`${c(e.pressing_cost_oil_tanks_20l)} tanks`:c(e.pressing_cost)}</div>
        <div><strong>Labor Cost:</strong> ${c(e.labor_cost_total)}</div>
        <div><strong>Total Cost:</strong> ${ut(e)}</div>
        <div><strong>Harvest Days:</strong> ${e.harvest_days??0}</div>
        ${n}
        <div class="full"><strong>Notes:</strong> ${e.notes||"-"}</div>
      </div>
      <div class="actions-row">
        <button class="btn ghost" type="button" data-edit-season="${e.id}">Modify</button>
      </div>
    </article>
  `}function Ze(e){const t=[...e].sort((s,a)=>Number(a.season_year)-Number(s.season_year)||String(s.land_piece_name||"").localeCompare(String(a.land_piece_name||""))),n=new Map;for(const s of t){const a=Number(s.season_year);n.has(a)||n.set(a,[]),n.get(a).push(s)}return Array.from(n.entries()).map(([s,a])=>({year:s,rows:a}))}function et(e,t=!1){const n=e.rows.filter(d=>j(d).length>0).length,s=e.rows.length;return`
    <details class="season-year-group"${t?" open":""}>
      <summary class="season-year-summary">
        <span class="season-year-title">${e.year}</span>
        <span class="season-year-meta">${s} piece${s>1?"s":""} | Drafts: ${n}</span>
      </summary>
      <div class="season-year-list">
        ${e.rows.map(Xe).join("")}
      </div>
    </details>
  `}function Ie(e){F=e,De.classList.toggle("is-hidden",!F),ve.textContent=F?"Hide Insights":"Show Insights"}function M(e){we=e;const t=e==="season",n=e==="budget",s=e==="usage",a=e==="inventory";qe.classList.toggle("is-hidden",!t),Ae.classList.toggle("is-hidden",!n),Ue.classList.toggle("is-hidden",!s),Oe.classList.toggle("is-hidden",!a),ye.className=`btn${t?"":" ghost"}`,fe.className=`btn${n?"":" ghost"}`,he.className=`btn${s?"":" ghost"}`,be.className=`btn${a?"":" ghost"}`,s&&q()}function tt(){if(!m||!g)return;if(!f.length){m.innerHTML='<option value="">No season records yet</option>',g.innerHTML='<option value="">No season records yet</option>';return}const e=m.value,t=f.map(a=>`<option value="${a.id}">${a.season_year} - ${a.land_piece_name}</option>`).join("");m.innerHTML=t,g.innerHTML=t;const s=f.some(a=>a.id===e)?e:f[0].id;m.value=s,g.value=s}function nt(){if(!B)return;if(!S.length){B.innerHTML='<option value="">No inventory items</option>';return}const e=String(B.value||"").trim();B.innerHTML=['<option value="">Select inventory item</option>',...S.map(n=>`<option value="${n.id}">${n.item_name} (${n.quantity_on_hand} ${n.unit_label})</option>`)].join("");const t=S.some(n=>n.id===e);B.value=t?e:""}function q(){if(!w)return;const e=String(w.value||"").trim(),t=String((g==null?void 0:g.value)||"").trim(),n=f.find(r=>r.id===t),s=i(n==null?void 0:n.remaining_tanks),a=['<option value="">Select inventory item</option>'];t&&s!==null&&s>0&&a.push(`<option value="season_tanks:${t}">Produced Tanks (${s.toFixed(2)} tanks)</option>`);for(const r of S)a.push(`<option value="inventory:${r.id}">${r.item_name} (${r.quantity_on_hand} ${r.unit_label})</option>`);w.innerHTML=a.join("");const d=Array.from(w.options).some(r=>r.value===e);w.value=d?e:""}function Q(){const e=String((m==null?void 0:m.value)||"").trim(),t=String((g==null?void 0:g.value)||"").trim();return e||t}function st(e){return`
    <article class="worker-card" data-labor-day-id="${e.id}">
      <div class="list-head">
        <h3>${e.work_date}</h3>
        <span class="badge day">${c(e.total_day_cost)} cost</span>
      </div>
      <div class="worker-grid">
        <div><strong>Men:</strong> ${e.men_count} x ${c(e.men_rate)}</div>
        <div><strong>Women:</strong> ${e.women_count} x ${c(e.women_rate)}</div>
        <div class="full"><strong>Notes:</strong> ${e.notes||"-"}</div>
      </div>
      <div class="actions-row"><button class="btn danger" type="button" data-delete-labor-day="${e.id}">Delete</button></div>
    </article>
  `}function at(e){let t="";return e.sale_type==="raw_kg"?t=`
      <div><strong>Raw KG Sold:</strong> ${c(e.raw_kg_sold)}</div>
      <div><strong>Price/KG:</strong> ${c(e.price_per_kg)}</div>
    `:e.sale_type==="processed_container"?t=`
      <div><strong>Containers Sold:</strong> ${c(e.containers_sold)}</div>
      <div><strong>Container Size:</strong> ${e.container_size_label||"-"}</div>
      <div><strong>KG/Container:</strong> ${c(e.kg_per_container)}</div>
      <div><strong>Price/Container:</strong> ${c(e.price_per_container)}</div>
    `:e.sale_type==="custom_item"||e.sale_type==="soap"?t=`
      <div><strong>Item:</strong> ${e.custom_item_name||"-"}</div>
      <div><strong>Quantity:</strong> ${c(e.custom_quantity_sold)} ${e.custom_unit_label||""}</div>
      <div><strong>Price/Unit:</strong> ${c(e.custom_price_per_unit)}</div>
    `:t=`
      <div><strong>Tanks Sold:</strong> ${c(e.tanks_sold)}</div>
      <div><strong>Price/Tank:</strong> ${c(e.price_per_tank)}</div>
    `,`
    <article class="worker-card" data-sale-id="${e.id}">
      <div class="list-head">
        <h3>${e.sold_on||"No date"}</h3>
        <span class="badge day">${c(e.total_revenue)} revenue</span>
      </div>
      <div class="worker-grid">
        <div><strong>Sale Type:</strong> ${We(e.sale_type)}</div>
        <div><strong>Inventory Delta (tanks):</strong> ${c(e.inventory_tanks_delta)}</div>
        ${t}
        <div><strong>Buyer:</strong> ${e.buyer||"-"}</div>
        <div class="full"><strong>Notes:</strong> ${e.notes||"-"}</div>
      </div>
      <div class="actions-row"><button class="btn danger" type="button" data-delete-sale="${e.id}">Delete</button></div>
    </article>
  `}function ot(e){return`
    <article class="worker-card" data-usage-item-id="${e.id}">
      <div class="list-head">
        <h3>${e.item_name}</h3>
        <span class="badge day">${c(e.quantity_on_hand)} ${e.unit_label} left</span>
      </div>
      <div class="worker-grid">
        <div><strong>Default Price:</strong> ${e.default_price_per_unit===null?"-":c(e.default_price_per_unit)}</div>
        <div><strong>Unit:</strong> ${e.unit_label}</div>
        <div class="full"><strong>Notes:</strong> ${e.notes||"-"}</div>
      </div>
    </article>
  `}function it(){return f.map(t=>{const n=i(t.total_cost)??0,s=i(t.sales_revenue_total)??0,a=i(t.profit)??s-n,d=(t.pressing_cost_mode==="oil_tanks"&&i(t.pressing_cost_money_equivalent)===null?(i(t.pressing_cost_oil_tanks_20l)??0):0);return{id:t.id,label:`${t.season_year} - ${t.land_piece_name||"Unnamed piece"}`,seasonYear:t.season_year,landPieceName:t.land_piece_name||"Unnamed piece",cost:n,revenue:s,profit:a,oilTankCost:d,costLabel:ut(t)}}).sort((t,n)=>Number(n.seasonYear)-Number(t.seasonYear)||t.landPieceName.localeCompare(n.landPieceName))}function rt(){if(!W||!Y||!G)return;const e=it();if(!e.length){W.innerHTML="",Y.innerHTML='<text class="chart-label" x="24" y="34">No season data yet.</text>',G.innerHTML='<tr><td colspan="5">No piece data yet.</td></tr>';return}const t=e.reduce((l,h)=>(l.cost+=h.cost,l.revenue+=h.revenue,l.profit+=h.profit,l.oilTankCost+=(h.oilTankCost||0),l),{cost:0,revenue:0,profit:0,oilTankCost:0}),n=t.revenue>0?t.profit/t.revenue*100:null,sn=t.oilTankCost>0?`${x(t.cost)} + ${x(t.oilTankCost)} tanks`:x(t.cost);W.innerHTML=`
    <article class="insight-kpi-card">
      <p class="insight-kpi-title">Total Cost</p>
      <p class="insight-kpi-value">${sn}</p>
      <p class="insight-kpi-caption">Across all pieces</p>
    </article>
    <article class="insight-kpi-card">
      <p class="insight-kpi-title">Total Revenue</p>
      <p class="insight-kpi-value">${x(t.revenue)}</p>
      <p class="insight-kpi-caption">Across all pieces</p>
    </article>
    <article class="insight-kpi-card">
      <p class="insight-kpi-title">Net Profit</p>
      <p class="insight-kpi-value">${x(t.profit)}</p>
      <p class="insight-kpi-caption">${t.profit>=0?"Positive season return":"Season currently at loss"}</p>
    </article>
    <article class="insight-kpi-card">
      <p class="insight-kpi-title">Global Margin</p>
      <p class="insight-kpi-value">${n===null?"-":`${n.toFixed(1)}%`}</p>
      <p class="insight-kpi-caption">Profit / revenue</p>
    </article>
  `;const s=e.reduce((l,h)=>Math.max(l,h.cost,Math.abs(h.profit)),1),a=e.slice(0,10),d=960,r=320,_=56,Z=24,U=26,xe=70,Le=d-_-Z,ee=r-U-xe,O=Le/a.length,R=Math.max(10,Math.min(28,(O-16)/2)),I=U+ee,te=l=>I-Math.abs(l)/s*ee,Be=a.map((l,h)=>{const K=_+h*O+O/2,ne=te(l.cost),se=te(l.profit),Te=l.landPieceName.length>12?`${l.landPieceName.slice(0,12)}...`:l.landPieceName;return`
        <rect class="chart-bar chart-bar-cost" x="${(K-R-3).toFixed(2)}" y="${ne.toFixed(2)}" width="${R.toFixed(2)}" height="${(I-ne).toFixed(2)}"></rect>
        <rect class="chart-bar ${l.profit>=0?"chart-bar-profit":"chart-bar-loss"}" x="${(K+3).toFixed(2)}" y="${se.toFixed(2)}" width="${R.toFixed(2)}" height="${(I-se).toFixed(2)}"></rect>
        <text class="chart-axis" x="${K.toFixed(2)}" y="${(I+16).toFixed(2)}" text-anchor="middle">${Te}</text>
      `}).join("");Y.innerHTML=`
    <rect class="chart-bg" x="0" y="0" width="${d}" height="${r}"></rect>
    <line class="chart-grid" x1="${_}" y1="${I}" x2="${d-Z}" y2="${I}"></line>
    <text class="chart-axis" x="${_}" y="${U-6}">Cost vs Profit (top 10 pieces)</text>
    <g>${Be}</g>
    <g>
      <rect class="chart-bar chart-bar-cost" x="${_}" y="${r-26}" width="14" height="14"></rect>
      <text class="chart-axis" x="${_+20}" y="${r-14}">Cost</text>
      <rect class="chart-bar chart-bar-profit" x="${_+100}" y="${r-26}" width="14" height="14"></rect>
      <text class="chart-axis" x="${_+120}" y="${r-14}">Profit</text>
      <rect class="chart-bar chart-bar-loss" x="${_+204}" y="${r-26}" width="14" height="14"></rect>
      <text class="chart-axis" x="${_+224}" y="${r-14}">Loss (negative profit)</text>
    </g>
  `,G.innerHTML=e.map(l=>{const h=l.revenue>0?`${(l.profit/l.revenue*100).toFixed(1)}%`:"-";return`
        <tr>
          <td>${l.label}</td>
          <td>${l.costLabel}</td>
          <td>${x(l.revenue)}</td>
          <td>${x(l.profit)}</td>
          <td>${h}</td>
        </tr>
      `}).join("")}function A(){const e=Q(),t=$e.filter(a=>a.season_id===e),n=ke.filter(a=>a.season_id===e),s=S;pe.innerHTML=t.length?t.map(st).join(""):"No labor days for selected season.",_e.innerHTML=n.length?n.map(at).join(""):"No sales records for selected season.",je.innerHTML=s.length?s.map(ot).join(""):"No inventory items yet.",rt()}async function X(){const[e,t,n,s]=await Promise.all([p(`${v}/olive-labor-days/mine`),p(`${v}/olive-sales/mine`),p(`${v}/olive-usages/mine`),p(`${v}/olive-inventory-items/mine`)]);$e=e||[],ke=t||[],S=s||[],nt(),q(),A()}async function $(){P.innerHTML="Loading seasons...";try{f=await p(`${v}/olive-seasons/mine`)||[],ue(f);const t=Ze(f);P.innerHTML=t.length?t.map((n,s)=>et(n,s===0)).join(""):"No season records yet.",tt(),await X()}catch(e){ue([]),P.innerHTML=`<p class="message error">${e.message}</p>`}}o.addEventListener("input",e=>{(e.target.name==="kg_per_land_piece"||e.target.name==="actual_chonbol"||e.target.name==="tanks_20l")&&Se()});o.addEventListener("submit",async e=>{e.preventDefault();const t=String(o.elements.season_id.value||"").trim(),n=Je();L("Saving season...",!0);try{await p(`${v}/olive-seasons${t?`/${t}`:""}`,{method:t?"PATCH":"POST",headers:b({"Content-Type":"application/json"}),body:JSON.stringify(n)}),await $(),H(),L("Season saved successfully.",!0)}catch(s){L(s.message||"Could not save season",!1)}});J.addEventListener("click",async()=>{const e=String(o.elements.season_id.value||"").trim();if(e&&window.confirm("Delete this season record?"))try{await p(`${v}/olive-seasons/${e}`,{method:"DELETE",headers:b()}),await $(),H(),L("Season deleted.",!0)}catch(t){L(t.message||"Could not delete season",!1)}});y.addEventListener("submit",async e=>{e.preventDefault();const t=Q();if(!t){N("Select a season first.",!1);return}const n={season_id:t,work_date:y.elements.work_date.value,men_count:Number(y.elements.men_count.value||0),women_count:Number(y.elements.women_count.value||0),men_rate:Number(y.elements.men_rate.value||0),women_rate:Number(y.elements.women_rate.value||0),notes:String(y.elements.notes.value||"").trim()||null};N("Saving labor day...",!0);try{await p(`${v}/olive-labor-days`,{method:"POST",headers:b({"Content-Type":"application/json"}),body:JSON.stringify(n)}),y.reset(),y.elements.men_count.value="0",y.elements.women_count.value="0",y.elements.men_rate.value="0",y.elements.women_rate.value="0",N("Labor day saved.",!0),await $()}catch(s){N(`Cannot save labor day: ${s.message||"Please check entered values."}`,!1)}});u.addEventListener("submit",async e=>{e.preventDefault();const t=Q();if(!t){C("Select a season first.",!1);return}const n=Ee(),s={season_id:t,sold_on:String(u.elements.sold_on.value||"").trim()||null,sale_type:n,tanks_sold:i(u.elements.tanks_sold.value),price_per_tank:i(u.elements.price_per_tank.value),raw_kg_sold:i(u.elements.raw_kg_sold.value),price_per_kg:i(u.elements.price_per_kg.value),containers_sold:i(u.elements.containers_sold.value),container_size_label:String(u.elements.container_size_label.value||"").trim()||null,kg_per_container:i(u.elements.kg_per_container.value),price_per_container:i(u.elements.price_per_container.value),custom_inventory_item_id:String(u.elements.custom_inventory_item_id.value||"").trim()||null,custom_item_name:String(u.elements.custom_item_name.value||"").trim()||null,custom_quantity_sold:i(u.elements.custom_quantity_sold.value),custom_unit_label:String(u.elements.custom_unit_label.value||"").trim()||null,custom_price_per_unit:i(u.elements.custom_price_per_unit.value),custom_inventory_tanks_delta:i(u.elements.custom_inventory_tanks_delta.value),buyer:String(u.elements.buyer.value||"").trim()||null,notes:String(u.elements.notes.value||"").trim()||null};n==="soap"&&(s.sale_type="soap",s.custom_item_name=s.custom_item_name||"Soap",s.custom_unit_label=s.custom_unit_label||"bar"),C("Saving sale...",!0);try{await p(`${v}/olive-sales`,{method:"POST",headers:b({"Content-Type":"application/json"}),body:JSON.stringify(s)}),u.reset(),E&&(E.value="oil_tank"),z(),C("Sale saved.",!0),await $()}catch(a){C(`Cannot save sale: ${a.message||"Please check remaining tanks and entered values."}`,!1)}});k.addEventListener("submit",async e=>{e.preventDefault();const t=String(k.elements.usage_inventory_item_id.value||"").trim();if(!t){T("Select an inventory source first.",!1);return}const n=i(k.elements.usage_quantity_used.value);if(n===null||n<=0){T("Enter a valid quantity.",!1);return}T("Saving usage...",!0);try{if(t.startsWith("inventory:")){const s=t.replace("inventory:",""),a=S.find(_=>_.id===s);if(!a)throw new Error("Inventory item not found");const d=i(a.quantity_on_hand)||0;if(n>d)throw new Error("Quantity used is greater than stock on hand");const r={quantity_on_hand:Number((d-n).toFixed(2)),notes:String(k.elements.notes.value||"").trim()||null};await p(`${v}/olive-inventory-items/${s}`,{method:"PATCH",headers:b({"Content-Type":"application/json"}),body:JSON.stringify(r)})}else if(t.startsWith("season_tanks:")){const a={season_id:t.replace("season_tanks:",""),used_on:null,tanks_used:n,usage_type:String(k.elements.usage_type.value||"").trim()||"consumption",notes:String(k.elements.notes.value||"").trim()||null};await p(`${v}/olive-usages`,{method:"POST",headers:b({"Content-Type":"application/json"}),body:JSON.stringify(a)})}else throw new Error("Unknown inventory source");k.reset(),w&&(w.value=""),T("Usage saved.",!0),await $()}catch(s){T(`Cannot save usage: ${s.message||"Please check remaining tanks and entered values."}`,!1)}});pe.addEventListener("click",async e=>{const t=e.target.closest("button[data-delete-labor-day]");if(!t)return;const n=t.dataset.deleteLaborDay;if(window.confirm("Delete this labor day entry?"))try{await p(`${v}/olive-labor-days/${n}`,{method:"DELETE",headers:b()}),await $()}catch(s){N(s.message||"Could not delete labor day",!1)}});_e.addEventListener("click",async e=>{const t=e.target.closest("button[data-delete-sale]");if(!t)return;const n=t.dataset.deleteSale;if(window.confirm("Delete this sale entry?"))try{await p(`${v}/olive-sales/${n}`,{method:"DELETE",headers:b()}),await $()}catch(s){C(s.message||"Could not delete sale",!1)}});g.addEventListener("change",()=>{m&&g&&(m.value=g.value),q(),A()});m.addEventListener("change",()=>{g&&m&&(g.value=m.value),q(),A()});P.addEventListener("click",e=>{const t=e.target.closest("button[data-edit-season]");if(!t)return;const n=t.dataset.editSeason,s=f.find(a=>a.id===n);s&&(ze(s),m&&f.some(a=>a.id===n)&&(m.value=n,g&&(g.value=n),A()),window.scrollTo({top:0,behavior:"smooth"}))});ve.addEventListener("click",()=>{Ie(!F)});Fe.addEventListener("click",H);Pe.addEventListener("click",$);He.addEventListener("click",X);Re.addEventListener("click",X);E&&E.addEventListener("change",z);ye.addEventListener("click",()=>M("season"));fe.addEventListener("click",()=>M("budget"));he.addEventListener("click",()=>M("usage"));be.addEventListener("click",()=>M("inventory"));Ke.addEventListener("click",()=>{de&&(de.src="./inventory.html?embedded=1")});H();Ie(!1);M(we);z();$();












