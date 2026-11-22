import copy, json, sys, tempfile, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from archive import validate, save, assemble, digest
from collect import normalise, collect_cohort, ROOT

class SourceTests(unittest.TestCase):
 def row(self):return {'key':123,'year':1880,'decimalLatitude':49.100123,'decimalLongitude':-122.654321,'datasetKey':'a','basisOfRecord':'PRESERVED_SPECIMEN','license':'http://creativecommons.org/licenses/by/4.0/legalcode','issues':[]}
 def test_normalizer_discards_precise_and_sensitive_locations(self):
  source=self.row();source['locality']='Precise private description';row=normalise(source,'langley','historic');self.assertNotIn('decimalLatitude',row);self.assertNotIn('locality',row);self.assertEqual(row['point'],[-122.66,49.1])
  source['informationWithheld']='Sensitive';row=normalise(source,'langley','historic');self.assertIsNone(row['point'])
 def test_unknown_uncertainty_remains_unknown(self):
  self.assertIsNone(normalise(self.row(),'langley','historic')['uncertainty_m'])
 def test_bounded_pagination_stratifies_and_deduplicates(self):
  calls=[]
  def response(url):
   from urllib.parse import urlparse,parse_qs
   calls.append(url);q=parse_qs(urlparse(url).query)
   if q['limit']==['0']:return {'count':2000}
   year=int(q['year'][0].split(',')[0]);offset=int(q['offset'][0]);source=self.row();source.update(key=year*1000+offset,year=year)
   return {'count':800,'offset':offset,'endOfRecords':False,'results':[{**source,'key':source['key']+i} for i in range(100)]}
  with patch('collect.request',side_effect=response),patch('collect.time.sleep'):
   records,cohort=collect_cohort('langley','historic',2026)
  self.assertEqual(len(calls),10);self.assertEqual(len(records),900);self.assertEqual(len(cohort['strata']),3);self.assertFalse(cohort['complete']);self.assertFalse(cohort['count_stable'])
 def test_bad_page_offset_is_rejected(self):
  with patch('collect.request',side_effect=[{'count':10},{'count':10,'offset':100,'results':[]}]), self.assertRaisesRegex(ValueError,'offset'):
   collect_cohort('langley','historic',2026)

class ArchiveTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.data=json.loads((ROOT/'data/current.json').read_text())
 def test_real_capture_schema_and_no_sensitive_fields(self):validate(self.data)
 def test_duplicate_id_rejected(self):
  data=copy.deepcopy(self.data);data['records'].append(data['records'][0])
  with self.assertRaisesRegex(ValueError,'Duplicate'):validate(data)
 def test_coordinate_precision_rejected(self):
  data=copy.deepcopy(self.data);data['records'][0]['point']=[-122.654321,49.100123]
  with self.assertRaisesRegex(ValueError,'generalized'):validate(data)
 def test_archive_checksums_and_previous_captures_survive(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);stage=root/'stage';stage.mkdir();save(copy.deepcopy(self.data),root);first=set((root/'data/snapshots').glob('*.json'))
   next_data=copy.deepcopy(self.data);next_data['captured_at']=(datetime.fromisoformat(self.data['captured_at'].replace('Z','+00:00'))+timedelta(days=1)).isoformat(timespec='seconds').replace('+00:00','Z');save(next_data,root);self.assertEqual(len(list((root/'data/snapshots').glob('*.json'))),2);self.assertTrue(all(p.exists() for p in first));assemble(root,stage)
   file=next(iter(first));file.write_text('{}')
   with self.assertRaisesRegex(ValueError,'checksum'):assemble(root,root/'badstage')
 def test_snapshot_path_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);save(copy.deepcopy(self.data),root);p=root/'data/history.json';h=json.loads(p.read_text());h[0]['file']='../outside.json';p.write_text(json.dumps(h))
   with self.assertRaisesRegex(ValueError,'archive path'):assemble(root,root/'stage')
if __name__=='__main__':unittest.main()
