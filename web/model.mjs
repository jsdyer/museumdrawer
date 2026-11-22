export const ERA_LABELS = {historic:'Historic specimens', modern:'Modern records'};
export function filterRecords(records, f={}) {
  const query=(f.query||'').trim().toLocaleLowerCase();
  return records.filter(r => (!f.region||r.region===f.region) && (!f.era||r.era===f.era) && (!f.kingdom||r.kingdom===f.kingdom)
    && (!f.dataset||r.dataset===f.dataset) && (!f.license||r.license===f.license)
    && (!f.minYear||r.year>=Number(f.minYear)) && (!f.maxYear||r.year<=Number(f.maxYear))
    && (f.quality!=='clean'||!r.spatial_issue)
    && (f.quality!=='precise'||(!r.spatial_issue&&r.uncertainty_m!==null&&r.uncertainty_m<=1000))
    && (!f.mapped||r.point) && (!f.cell||r.point?.join(',')===f.cell)
    && (!query||[r.name,r.institution,r.collection,r.catalogue,r.recorded_by].some(v=>String(v||'').toLocaleLowerCase().includes(query))));
}
export function counts(records,key) {
 const map=new Map();for(const r of records){const value=typeof key==='function'?key(r):r[key];map.set(value,(map.get(value)||0)+1);}return [...map].sort((a,b)=>b[1]-a[1]||String(a[0]).localeCompare(String(b[0])));
}
export function decades(records){const map=new Map();for(const r of records){const year=Math.floor(r.year/10)*10;const v=map.get(year)||{year,historic:0,modern:0};v[r.era]++;map.set(year,v);}return [...map.values()].sort((a,b)=>a.year-b.year);}
export function cells(records){const map=new Map();for(const r of records){if(!r.point)continue;const key=r.point.join(',');const v=map.get(key)||{key,point:r.point,historic:0,modern:0,count:0};v.count++;v[r.era]++;map.set(key,v);}return [...map.values()];}
export function csv(records,datasets={}){
 const keys=['id','name','region','era','year','event_date','kingdom','basis','institution','collection','catalogue','license','license_url','uncertainty_m','coordinates','issues','url'];
 const safe=v=>{let text=String(v??'');if(/^(?:\s*[=+\-@]|[\t\r])/.test(text))text="'"+text;return '"'+text.replaceAll('"','""')+'"';};
 return '\uFEFF'+[keys.concat(['dataset_title','dataset_url']).map(safe).join(','),...records.map(r=>keys.map(k=>safe(Array.isArray(r[k])?r[k].join('; '):r[k])).concat([safe(datasets[r.dataset]?.title||r.dataset),safe(datasets[r.dataset]?.url)]).join(','))].join('\r\n');
}
export function safeURL(value){try{const u=new URL(value);return u.protocol==='https:'?u.href:null;}catch{return null;}}
