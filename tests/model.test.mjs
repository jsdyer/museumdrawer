import test from 'node:test';
import assert from 'node:assert/strict';
import {filterRecords,counts,decades,cells,csv,safeURL} from '../web/model.mjs';
const rows=[
 {id:'1',name:'Amanita test',region:'langley',era:'historic',year:1881,kingdom:'Fungi',dataset:'a',license:'CC BY 4.0',spatial_issue:false,uncertainty_m:null,point:[-122.66,49.1],issues:[]},
 {id:'2',name:'Rosa test',region:'langley',era:'modern',year:2020,kingdom:'Plantae',dataset:'b',license:'CC0 1.0',spatial_issue:false,uncertainty_m:100,point:[-122.66,49.1],issues:[]},
 {id:'3',name:'Bird test',region:'halifax',era:'historic',year:1930,kingdom:'Animalia',dataset:'c',license:'CC BY-NC 4.0',spatial_issue:true,uncertainty_m:200,point:null,issues:['COORDINATE_INVALID']},
];
test('filters intersect region, era, year, licence and source without losing input',()=>{assert.deepEqual(filterRecords(rows,{region:'langley',era:'historic',maxYear:1999,license:'CC BY 4.0',dataset:'a'}).map(r=>r.id),['1']);assert.equal(rows.length,3);});
test('unknown uncertainty cannot pass precise filter and spatial flags are excluded',()=>{assert.deepEqual(filterRecords(rows,{quality:'precise'}).map(r=>r.id),['2']);assert.equal(filterRecords(rows,{quality:'clean'}).length,2);});
test('map-only and cell filters omit withheld locations',()=>{assert.equal(filterRecords(rows,{mapped:true}).length,2);assert.equal(filterRecords(rows,{cell:'-122.66,49.1'}).length,2);assert.equal(cells(rows).length,1);assert.equal(cells(rows)[0].historic,1);assert.equal(cells(rows)[0].modern,1);});
test('search and years are not interpreted as markup or regular expressions',()=>{assert.equal(filterRecords(rows,{query:'rosa'}).length,1);assert.equal(filterRecords(rows,{query:'.*'}).length,0);assert.equal(filterRecords(rows,{minYear:2026,maxYear:1800}).length,0);});
test('decades separate source eras and taxonomy counts are discrete',()=>{assert.deepEqual(decades(rows).map(d=>[d.year,d.historic,d.modern]),[[1880,1,0],[1930,1,0],[2020,0,1]]);assert.equal(counts(rows,'region')[0][1],2);});
test('CSV escapes commas, formulas, quotes and omits coordinate values',()=>{const text=csv([{...rows[0],name:'=1+1',catalogue:'a,"b"'}],{a:{title:'Herbarium',url:'https://www.gbif.org/dataset/a'}});assert.ok(text.includes('"\'=1+1"'));assert.ok(text.includes('"a,""b"""'));assert.ok(text.includes('Herbarium'));assert.ok(!text.includes('-122.66'));});
test('links allow HTTPS only',()=>{assert.equal(safeURL('javascript:alert(1)'),null);assert.equal(safeURL('http://example.com'),null);assert.equal(safeURL('https://www.gbif.org/'),'https://www.gbif.org/');});
