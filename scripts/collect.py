#!/usr/bin/env python3
"""Collect bounded, attributed GBIF occurrence samples; never retain exact coordinates."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, math, time, urllib.parse, urllib.request
from archive import save, validate
ROOT = Path(__file__).resolve().parents[1]
REGIONS = {
    'langley': {'name': 'Langley, British Columbia', 'bounds': [-122.80, 49.02, -122.52, 49.20], 'centre': [-122.66, 49.10]},
    'halifax': {'name': 'Halifax, Nova Scotia', 'bounds': [-63.70, 44.56, -63.45, 44.74], 'centre': [-63.58, 44.65]},
}
PAGE_SIZE, MAX_PAGES = 300, 3
API = 'https://api.gbif.org/v1/'
SPATIAL_FLAGS = {'ZERO_COORDINATE','COORDINATE_OUT_OF_RANGE','COUNTRY_COORDINATE_MISMATCH','COORDINATE_INVALID','COORDINATE_REPROJECTION_SUSPICIOUS','COORDINATE_REPROJECTION_FAILED','COORDINATE_UNCERTAINTY_METERS_INVALID','COORDINATE_PRECISION_INVALID'}

def request(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'CoolCode Museum Drawer (+https://coolcode.ca/museumdrawer/)', 'Accept':'application/json'})
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = response.read(25_000_001)
            if len(raw) > 25_000_000: raise ValueError('GBIF page exceeds limit')
            return json.loads(raw)
        except (OSError, TimeoutError):
            if attempt == 2: raise
            time.sleep(2 ** attempt)

def normalise(row, region, era):
    key = row.get('key'); year = row.get('year')
    if not isinstance(key, int) or not isinstance(year, int): raise ValueError('Missing GBIF identity or year')
    restricted = bool(row.get('informationWithheld') or row.get('dataGeneralizations'))
    lat, lon = row.get('decimalLatitude'), row.get('decimalLongitude')
    valid = all(isinstance(v, (int,float)) and math.isfinite(v) for v in (lat,lon)) and -90 <= lat <= 90 and -180 <= lon <= 180
    # Only a coarsened public grid survives. Never store verbatim locality, GPS or private data.
    point = [round(round(lon / .02) * .02, 2), round(round(lat / .02) * .02, 2)] if valid and not restricted else None
    issues = row.get('issues') or []
    uncertainty = row.get('coordinateUncertaintyInMeters')
    if not isinstance(uncertainty, (int,float)) or not math.isfinite(uncertainty) or uncertainty < 0: uncertainty = None
    license_url = row.get('license', '')
    license_name = 'CC BY-NC 4.0' if '/by-nc/' in license_url else 'CC BY 4.0' if '/by/' in license_url else 'CC0 1.0' if '/zero/' in license_url else 'Other / unknown'
    return {'id':str(key), 'region':region, 'era':era, 'name':row.get('species') or row.get('scientificName') or 'Unidentified taxon',
        'kingdom':row.get('kingdom') or 'Unassigned', 'rank':row.get('taxonRank') or 'Unknown', 'year':year,
        'month':row.get('month'), 'event_date':row.get('eventDate') or str(year),
        'basis':row.get('basisOfRecord') or 'UNKNOWN', 'dataset':row.get('datasetKey'),
        'institution':row.get('institutionCode') or '', 'collection':row.get('collectionCode') or '',
        'catalogue':row.get('catalogNumber') or '', 'recorded_by':row.get('recordedBy') or '',
        'license':license_name, 'license_url':license_url.replace('http://','https://'),
        'point':point, 'coordinates':'withheld / generalized by publisher' if restricted else 'public coordinates rounded to 0.02°' if point else 'not mappable',
        'uncertainty_m':uncertainty, 'spatial_issue':bool(SPATIAL_FLAGS.intersection(issues)), 'issues':issues,
        'url':f'https://www.gbif.org/occurrence/{key}'}

def collect_cohort(region, era, current_year):
    west,south,east,north = REGIONS[region]['bounds']
    params = {'decimalLatitude':f'{south},{north}', 'decimalLongitude':f'{west},{east}', 'hasCoordinate':'true', 'country':'CA', 'year':'1700,1999' if era=='historic' else f'2000,{current_year}'}
    if era == 'historic': params['basisOfRecord'] = 'PRESERVED_SPECIMEN'
    base = API + 'occurrence/search?' + urllib.parse.urlencode(params)
    summary = request(base + '&limit=0')
    if not isinstance(summary.get('count'),int):raise ValueError('Missing GBIF total')
    bands = [(1700,1899),(1900,1949),(1950,1999)] if era=='historic' else [(2000,2009),(2010,2019),(2020,current_year)]
    records, ids, pages, strata, duplicate_count = [], set(), [], [], 0
    for first,last in bands:
        band_params = {**params,'year':f'{first},{last}'}
        band_base = API + 'occurrence/search?' + urllib.parse.urlencode(band_params)
        counts, loaded, ended = [], 0, False
        for page in range(MAX_PAGES):
            url = band_base + f'&limit=100&offset={page*100}'
            response = request(url)
            if not isinstance(response.get('results'),list) or not isinstance(response.get('count'),int):raise ValueError('Unexpected GBIF search schema')
            if response.get('offset')!=page*100:raise ValueError('GBIF pagination offset mismatch')
            counts.append(response['count']);pages.append(url);rows=response['results']
            if len(rows)>100:raise ValueError('Oversized result page')
            for source_row in rows:
                row=normalise(source_row,region,era)
                if not first<=row['year']<=last:raise ValueError('Record outside requested time band')
                if row['id'] in ids:duplicate_count+=1;continue
                ids.add(row['id']);records.append(row);loaded+=1
            if response.get('endOfRecords') or len(rows)<100:ended=True;break
            time.sleep(.2)
        stable=len(set(counts))==1
        strata.append({'years':[first,last],'loaded':loaded,'matched':counts[0],'count_last_page':counts[-1],'complete':ended and stable and loaded==counts[0],'count_stable':stable,'query':band_base})
    if not records:raise ValueError(f'Unexpected empty {region}/{era}; preserving existing snapshot')
    stable=all(s['count_stable'] for s in strata) and sum(s['matched'] for s in strata)==summary['count']
    return records, {'region':region,'era':era,'matched':summary['count'],'count_last_page':sum(s['count_last_page'] for s in strata),'loaded':len(records),'complete':all(s['complete'] for s in strata) and stable,'count_stable':stable,'duplicate_rows':duplicate_count,'pages':len(pages),'query':base,'requests':pages,'strata':strata,'method':'Three time bands per era, each capped at 300 records using the first three 100-record pages in GBIF API order. This capped, stratified sample is not random or representative.'}

def dataset_info(key):
    data = request(API + 'dataset/' + key)
    return key, {'title':data.get('title') or key,'publisher':data.get('publishingOrganizationTitle') or data.get('publishingOrganizationKey') or 'See dataset page', 'citation': (data.get('citation') or {}).get('text','') if isinstance(data.get('citation'),dict) else str(data.get('citation') or ''), 'url':'https://www.gbif.org/dataset/'+key,'license':data.get('license','')}

def main():
    stamp = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
    records, cohorts = [], []
    for region in REGIONS:
        for era in ('historic','modern'):
            rows, cohort = collect_cohort(region,era,int(stamp[:4])); records.extend(rows);cohorts.append(cohort)
            print(f'{region}/{era}: {len(rows)} retained / {cohort["matched"]} matching',flush=True)
    keys = sorted({r['dataset'] for r in records})
    with ThreadPoolExecutor(max_workers=4) as pool: datasets = dict(pool.map(dataset_info, keys))
    payload={'schema':1,'captured_at':stamp,'source':'GBIF public Occurrence Search API','regions':REGIONS,'cohorts':cohorts,'datasets':datasets,'records':records,
      'coordinate_policy':'Source coordinates are rounded to a 0.02 degree grid (roughly 1–2 km). Records marked informationWithheld or dataGeneralizations have no cached or mapped coordinates. No verbatim locality or original GPS is retained.',
      'coverage':'Two fixed local bounding boxes, restricted to Canada and public coordinates. Historic: preserved specimens dated 1700–1999, split into 1700–1899, 1900–1949 and 1950–1999 bands. Modern: all record types dated 2000 through collection year, split into 2000–2009, 2010–2019 and 2020 onward bands. Up to 300 records per time band (900 per region/era), in API default order. Unused band capacity is not reassigned.',
      'sources':[{'title':'GBIF Occurrence API','url':'https://techdocs.gbif.org/en/openapi/v1/occurrence'}, {'title':'GBIF issues and flags','url':'https://techdocs.gbif.org/en/data-use/occurrence-issues-and-flags'},{'title':'GBIF data terms and licences','url':'https://www.gbif.org/terms'}]}
    validate(payload); save(payload,ROOT)
if __name__=='__main__':main()
