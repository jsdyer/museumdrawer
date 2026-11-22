import {ERA_LABELS, filterRecords, counts, decades, cells, csv, safeURL} from './model.mjs';
const $=id=>document.getElementById(id), fmt=n=>Number(n).toLocaleString('en-CA');
const state={data:null,region:'langley',page:1,cell:'',records:[],snapshot:'current.json'};
const filterIds=['query','era','kingdom','dataset','license','quality','minYear','maxYear','mapped'];
function node(tag,text,className){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el;}
function link(text,url){const a=node('a',text);const safe=safeURL(url);if(safe){a.href=safe;a.target='_blank';a.rel='noopener noreferrer';}return a;}
function option(value,text){const el=node('option',text);el.value=value;return el;}
function stamp(value){return new Date(value).toLocaleString('en-CA',{dateStyle:'medium',timeStyle:'short',timeZone:'UTC'})+' UTC';}
function sourceName(id){return state.data.datasets[id]?.title||id;}
async function readJSON(file){const response=await fetch('./data/'+file);if(!response.ok)throw new Error('Capture could not be loaded ('+response.status+').');return response.json();}
function form(){const values={region:state.region,cell:state.cell};for(const id of filterIds)values[id]=$(id).type==='checkbox'?$(id).checked:$(id).value;return values;}
function updateOptions(){
 const kingdom=$('kingdom').value,dataset=$('dataset').value;
 $('kingdom').replaceChildren(option('','All kingdoms'),...counts(state.data.records.filter(r=>r.region===state.region),'kingdom').map(([k,n])=>option(k,k+' · '+fmt(n))));
 $('dataset').replaceChildren(option('','All datasets'),...counts(state.data.records.filter(r=>r.region===state.region),'dataset').map(([k,n])=>option(k,sourceName(k)+' · '+fmt(n))));
 if([...$('kingdom').options].some(o=>o.value===kingdom))$('kingdom').value=kingdom;
 if([...$('dataset').options].some(o=>o.value===dataset))$('dataset').value=dataset;
}
function metadata(){
 const d=state.data;$('capture-date').textContent='Captured '+stamp(d.captured_at);$('snapshot-download').href='./data/'+state.snapshot;
 $('coverage').replaceChildren();$('query-links').replaceChildren();
 for(const cohort of d.cohorts){
  $('query-links').append(link(d.regions[cohort.region].name+' · '+ERA_LABELS[cohort.era]+' API query',cohort.query));
  if(cohort.region!==state.region)continue;
  const box=node('div');box.append(node('strong',ERA_LABELS[cohort.era]+' · '+fmt(cohort.loaded)+' retained / '+fmt(cohort.matched)+' GBIF matches'));
  box.append(node('p',cohort.era==='historic'?'Preserved specimens, 1700–1999.':'All record types, 2000–'+d.captured_at.slice(0,4)+'.'));
  if(!cohort.count_stable)box.append(node('p','GBIF totals changed during collection; coverage is approximate.'));
  if(cohort.strata){const detail=node('details'),summary=node('summary','Time-band coverage');detail.append(summary);for(const band of cohort.strata)detail.append(node('p',band.years.join('–')+': '+fmt(band.loaded)+' retained / '+fmt(band.matched)+' matches'+(band.complete?' · complete':' · capped / incomplete')));box.append(detail);}
  $('coverage').append(box);
 }
 $('coverage').append(node('p',state.data.cohorts.find(c=>c.region===state.region).method+' Charts, maps and filters use only retained records.','sample-note'));
 const region=d.regions[state.region], b=region.bounds;
 $('coverage-details').textContent=d.coverage+' '+region.name+' box: '+b[1]+'–'+b[3]+'° N; '+Math.abs(b[2])+'–'+Math.abs(b[0])+'° W. Missing coordinates and records without an interpreted year are outside these queries.';
}
function renderTimeline(records){
 const series=decades(records), parent=$('timeline');parent.replaceChildren();
 if(!series.length){parent.append(node('p','No dated records in this selection.','caption'));return;}
 const map=new Map(series.map(d=>[d.year,d])), min=series[0].year,max=series.at(-1).year;
 const maximum=Math.max(...series.map(d=>Math.max(d.historic,d.modern))), total=(max-min)/10+1;
 parent.setAttribute('role','img');parent.setAttribute('aria-label','Records by decade: '+series.map(d=>`${d.year}s: ${d.historic} historic, ${d.modern} modern`).join('; '));
 for(let year=min;year<=max;year+=10){const d=map.get(year)||{historic:0,modern:0};const col=node('div',undefined,'decade');col.title=`${year}s: ${fmt(d.historic)} historic; ${fmt(d.modern)} modern`;
  for(const era of ['historic','modern']){const bar=node('div',undefined,'bar '+era);bar.style.height=(d[era]/maximum*100)+'%';col.append(bar);}
  if((year-min)/10%Math.max(1,Math.ceil(total/8))===0||year===max)col.append(node('span',String(year),'tick'));
  parent.append(col);
 }
}
function svg(tag,attrs={},text){const el=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [key,value]of Object.entries(attrs))el.setAttribute(key,String(value));if(text!==undefined)el.textContent=text;return el;}
function renderMap(records){
 const map=$('map');map.replaceChildren(svg('title',{id:'map-title'},'Generalized '+state.data.regions[state.region].name+' occurrence map'));
 const b=state.data.regions[state.region].bounds;const west=b[0]-.015,south=b[1]-.015,east=b[2]+.015,north=b[3]+.015;
 const x=lon=>45+(lon-west)/(east-west)*525, y=lat=>295-(lat-south)/(north-south)*260;
 for(let i=0;i<=5;i++){const lon=west+(east-west)*i/5,lat=south+(north-south)*i/5;
  map.append(svg('line',{x1:x(lon),x2:x(lon),y1:35,y2:295,class:'grid'}),svg('line',{x1:45,x2:570,y1:y(lat),y2:y(lat),class:'grid'}));
  map.append(svg('text',{x:x(lon),y:317,'text-anchor':'middle'},Math.abs(lon).toFixed(2)+'°W'),svg('text',{x:39,y:y(lat)+3,'text-anchor':'end'},lat.toFixed(2)+'°N'));
 }
 const grid=cells(records),max=Math.max(1,...grid.map(c=>c.count));
 for(const cell of grid){const size=9+Math.sqrt(cell.count/max)*18,colour=cell.historic&&cell.modern?'#7b7152':cell.historic?'#ab6743':'#3e6253';
  const rect=svg('rect',{x:x(cell.point[0])-size/2,y:y(cell.point[1])-size/2,width:size,height:size,rx:2,fill:colour,opacity:.85,class:'mapcell',tabindex:'0',role:'button','aria-label':`${fmt(cell.count)} records in rounded cell ${cell.key}. Filter this cell.`});
  rect.append(svg('title',{},`${cell.point[1].toFixed(2)}°N, ${Math.abs(cell.point[0]).toFixed(2)}°W · ${cell.historic} historic / ${cell.modern} modern`));
  const select=()=>{state.cell=cell.key;state.page=1;render();};rect.addEventListener('click',select);rect.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select();}});map.append(rect);
 }
 const centre=state.data.regions[state.region].centre;
 map.append(svg('circle',{cx:x(centre[0]),cy:y(centre[1]),r:3,fill:'#172e26'}),svg('text',{x:x(centre[0])+7,y:y(centre[1])-7},state.region==='langley'?'Langley':'Halifax'),svg('text',{x:570,y:20,'text-anchor':'end'},'N ↑'));
 const mappable=records.filter(r=>r.point).length;
 $('map-note').textContent=`${fmt(mappable)} mapped records in ${fmt(grid.length)} coarse cells; ${fmt(records.length-mappable)} omitted. Rust = historic, green = modern, olive = both. Larger squares contain more records.`;
 $('clear-cell').hidden=!state.cell;
}
function renderSources(records){
 const root=$('sources-chart');root.replaceChildren();const grouped=counts(records,'dataset').slice(0,5),max=grouped[0]?.[1]||1;
 if(!grouped.length){root.append(node('p','No source records in this selection.','caption'));return;}
 for(const [id,count]of grouped){const item=node('div',undefined,'source-bar');const line=node('div',undefined,'source-caption'),name=node('span',sourceName(id));name.title=sourceName(id);line.append(name,node('strong',fmt(count)));const track=node('div',undefined,'source-track'),bar=node('i');bar.style.width=(count/max*100)+'%';track.append(bar);item.append(line,track);root.append(item);}
}
function detail(row){
 const root=$('detail-content');root.replaceChildren(node('span','GBIF / '+row.id,'number'),node('h2',row.name),node('p',ERA_LABELS[row.era]+' · '+row.event_date,'intro'));
 const ds=state.data.datasets[row.dataset],list=node('dl');
 const facts={'Record type':row.basis.replaceAll('_',' '),'Kingdom / rank':row.kingdom+' / '+row.rank,'Source dataset':ds.title,'Publisher registry ID':ds.publisher,'Institution / collection':[row.institution,row.collection].filter(Boolean).join(' / ')||'Not provided','Catalogue number':row.catalogue||'Not provided','Recorded by':row.recorded_by||'Not provided','Licence':row.license,'Coordinates':row.coordinates,'Source uncertainty':row.uncertainty_m===null?'Not reported':fmt(row.uncertainty_m)+' m; map rounding adds uncertainty','GBIF flags':row.issues.length?row.issues.join(', '):'No flags supplied','Capture date':stamp(state.data.captured_at)};
 for(const [key,value]of Object.entries(facts))list.append(node('dt',key),node('dd',value));root.append(list);
 if(ds.citation)root.append(node('p',ds.citation,'caption'));
 const links=node('div',undefined,'detail-links');links.append(link('Original GBIF record ↗',row.url),link('Source dataset & attribution ↗',ds.url));if(safeURL(row.license_url))links.append(link('Licence terms ↗',row.license_url));root.append(links,node('p','Location coordinates are deliberately coarse or omitted. Source flags identify possible issues; they are not a complete quality assessment.','caption'));$('detail').showModal();
}
function renderCards(records){
 const sort=$('sort').value,sorted=[...records].sort((a,b)=>sort==='name'?a.name.localeCompare(b.name):sort==='newest'?b.year-a.year||a.name.localeCompare(b.name):a.year-b.year||a.name.localeCompare(b.name));
 const pages=Math.max(1,Math.ceil(sorted.length/18));state.page=Math.min(state.page,pages);const page=sorted.slice((state.page-1)*18,state.page*18);
 const root=$('cards');root.replaceChildren();
 for(const row of page){const card=node('article',undefined,'record-card '+row.era),top=node('div',undefined,'card-top');top.append(node('span',row.era==='historic'?'Preserved specimen':row.basis.replaceAll('_',' ').toLocaleLowerCase()),node('strong',String(row.year)));
  card.append(top,node('h4',row.name,'card-name'),node('p',row.kingdom+' · '+(row.institution||sourceName(row.dataset)),'card-data'),node('p',(row.catalogue?'No. '+row.catalogue+' · ':'')+row.license,'card-data'));
  const action=node('button','Open record card ↗','card-action');action.addEventListener('click',()=>detail(row));card.append(action);root.append(card);
 }
 $('results-count').textContent=`${fmt(records.length)} filtered records · ${records.length?fmt((state.page-1)*18+1):0}–${fmt(Math.min(state.page*18,records.length))} shown`;
 $('page-label').textContent='Page '+state.page+' of '+pages;$('previous').disabled=state.page<=1;$('next').disabled=state.page>=pages;$('empty').hidden=Boolean(records.length);$('export').disabled=!records.length;
}
function render(){
 const f=form();if(f.minYear&&f.maxYear&&Number(f.minYear)>Number(f.maxYear))$('maxYear').setCustomValidity('The final year must be after the first year.');else $('maxYear').setCustomValidity('');
 const records=filterRecords(state.data.records,f);state.records=records;
 $('stat-records').textContent=fmt(records.length);$('stat-historic').textContent=fmt(records.filter(r=>r.era==='historic').length);$('stat-modern').textContent=fmt(records.filter(r=>r.era==='modern').length);$('stat-taxa').textContent=fmt(new Set(records.map(r=>r.name)).size);
 renderTimeline(records);renderMap(records);renderSources(records);renderCards(records);
}
async function capture(file){
 const previous=state.snapshot;$('snapshot').disabled=true;$('load-status').hidden=false;$('load-status').textContent='Opening the selected capture…';
 try{const data=await readJSON(file);if(data.schema!==1||!Array.isArray(data.records)||!data.records.length)throw new Error('The capture is not valid.');state.data=data;state.snapshot=file;state.page=1;state.cell='';updateOptions();metadata();render();$('app').hidden=false;$('load-status').hidden=true;}
 catch(error){$('load-status').textContent=error.message+' The previous capture is unchanged. Please reload to retry.';$('snapshot').value=previous;}
 finally{$('snapshot').disabled=false;}
}
function reset(){for(const id of filterIds){if($(id).type==='checkbox')$(id).checked=false;else $(id).value=id==='quality'?'any':'';}state.cell='';state.page=1;render();}
for(const id of filterIds)$(id).addEventListener('input',()=>{state.page=1;render();});
for(const button of document.querySelectorAll('[data-region]'))button.addEventListener('click',()=>{state.region=button.dataset.region;state.cell='';state.page=1;for(const b of document.querySelectorAll('[data-region]')){b.classList.toggle('active',b===button);b.setAttribute('aria-pressed',String(b===button));}updateOptions();metadata();render();});
$('snapshot').addEventListener('change',()=>capture($('snapshot').value));$('reset').addEventListener('click',reset);$('sort').addEventListener('change',()=>{state.page=1;renderCards(state.records);});
$('previous').addEventListener('click',()=>{state.page--;renderCards(state.records);$('results-count').scrollIntoView({block:'nearest'});});$('next').addEventListener('click',()=>{state.page++;renderCards(state.records);$('results-count').scrollIntoView({block:'nearest'});});
$('clear-cell').addEventListener('click',()=>{state.cell='';state.page=1;render();});$('close-detail').addEventListener('click',()=>$('detail').close());$('detail').addEventListener('click',event=>{if(event.target===$('detail'))$('detail').close();});
$('export').addEventListener('click',()=>{const blob=new Blob([csv(state.records,state.data.datasets)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=node('a');a.href=url;a.download=`museumdrawer-${state.region}-${state.data.captured_at.slice(0,10)}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
try{const [history,build]=await Promise.all([readJSON('history.json'),readJSON('build.json')]);$('snapshot').replaceChildren(option('current.json','Latest retained capture'),...[...history].reverse().map(h=>option(h.file,stamp(h.captured_at)+' · '+fmt(h.count)+' records')));$('build-date').textContent='Built '+stamp(build.built_at);await capture('current.json');}
catch(error){$('load-status').textContent='The collection could not be opened. '+error.message+' Please reload to retry.';}
