"""Validated append-only compact snapshots, offline assembly and probe metadata."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, shutil

def encoded(value): return (json.dumps(value, ensure_ascii=False, separators=(',',':'),sort_keys=True,allow_nan=False)+'\n').encode()
def digest(raw): return hashlib.sha256(raw).hexdigest()
def validate(data):
    if data.get('schema') != 1 or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',data.get('captured_at','')): raise ValueError('Invalid dated snapshot')
    rows = data.get('records')
    if not isinstance(rows,list) or not rows: raise ValueError('Empty snapshot')
    ids = [r.get('id') for r in rows]
    if len(ids)!=len(set(ids)) or not all(isinstance(i,str) and i.isdigit() for i in ids): raise ValueError('Duplicate or invalid GBIF IDs')
    if len(data.get('cohorts',[]))!=4: raise ValueError('Four source cohorts required')
    for c in data['cohorts']:
        actual=sum(r['region']==c['region'] and r['era']==c['era'] for r in rows)
        if actual != c['loaded'] or not 0 < actual <= 900 or c['matched'] < actual: raise ValueError('Invalid coverage counts')
        if not c['query'].startswith('https://api.gbif.org/v1/occurrence/search?'): raise ValueError('Invalid source query')
    for r in rows:
        if r['dataset'] not in data['datasets'] or r['region'] not in data['regions'] or r['era'] not in ('historic','modern'): raise ValueError('Unknown attribution or cohort')
        if not 1700<=r['year']<=int(data['captured_at'][:4]): raise ValueError('Date outside coverage')
        if r['era']=='historic' and (r['year']>1999 or r['basis']!='PRESERVED_SPECIMEN'): raise ValueError('Historic cohort mismatch')
        if r['era']=='modern' and r['year']<2000: raise ValueError('Modern cohort mismatch')
        if r.get('point'):
            if r['coordinates'].startswith('withheld'): raise ValueError('Restricted coordinates retained')
            if len(r['point'])!=2 or any(not isinstance(v,(int,float)) or abs(v/.02-round(v/.02))>1e-8 for v in r['point']): raise ValueError('Coordinates insufficiently generalized')
            west,south,east,north=data['regions'][r['region']]['bounds']
            if not west-.02<=r['point'][0]<=east+.02 or not south-.02<=r['point'][1]<=north+.02: raise ValueError('Coordinates outside regional coverage')
        if any(k in r for k in ('decimalLatitude','decimalLongitude','locality','verbatimLocality')): raise ValueError('Original location fields forbidden')
    encoded(data)
    return data

def save(payload,root):
    validate(payload);folder=root/'data';folder.mkdir(exist_ok=True)
    raw=encoded(payload);sha=digest(raw);stamp=payload['captured_at'];name='snapshots/'+stamp.replace(':','').replace('-','')+'-'+sha[:12]+'.json'
    target=folder/name;target.parent.mkdir(exist_ok=True)
    if target.exists() and target.read_bytes()!=raw: raise ValueError('Archive collision')
    if not target.exists(): target.write_bytes(raw)
    history_path=folder/'history.json';history=json.loads(history_path.read_text()) if history_path.exists() else []
    if not any(h['file']==name for h in history):history.append({'captured_at':stamp,'file':name,'count':len(payload['records']),'sha256':sha})
    index={'schema':1,'tool':'museumdrawer','captured_at':stamp,'checked_at':stamp,'record_count':len(payload['records']),'records':len(payload['records']),'snapshots':len(history),'latest':'current.json','history':'history.json','source':'GBIF','coverage':payload['coverage'],'status':'sampled','sources':payload['sources']}
    for filename,value in [('current.json',payload),('history.json',history),('index.json',index)]:
        temp=folder/(filename+'.tmp');temp.write_bytes(encoded(value));temp.replace(folder/filename)
    print(f'Saved {len(payload["records"]):,} records, {len(history)} immutable capture(s)',flush=True)

def assemble(root,stage):
    folder=root/'data';data=validate(json.loads((folder/'current.json').read_text()));history=json.loads((folder/'history.json').read_text())
    if not history:raise ValueError('Missing history')
    for item in history:
        path=Path(item['file'])
        if path.is_absolute() or '..' in path.parts or path.parts[0]!='snapshots':raise ValueError('Invalid archive path')
        raw=(folder/path).read_bytes()
        if digest(raw)!=item['sha256']:raise ValueError('Archive checksum mismatch')
        validate(json.loads(raw))
    if not any(h['sha256']==digest(encoded(data)) for h in history):raise ValueError('Current capture is not archived')
    shutil.copytree(folder,stage/'data')
    build={'built_at':datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')}
    (stage/'data/build.json').write_bytes(encoded(build))
