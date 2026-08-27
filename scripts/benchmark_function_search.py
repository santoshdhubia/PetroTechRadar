#!/usr/bin/env python3
"""Benchmark usability of PetroTechRadar function-level search."""
from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs'/'data'
TESTS=[
('Read SEG-Y trace headers',['equinor/segyio'],['header','attributes','tracefield']),
('Read SEG-Y traces',['equinor/segyio'],['trace','gather']),
('Get inline and crossline data from SEG-Y',['equinor/segyio','trhallam/segysak'],['iline','xline','inline','crossline']),
('Create a new SEG-Y file',['equinor/segyio'],['create']),
('Load SEG-Y into xarray',['trhallam/segysak'],['segy','xarray','open']),
('Perform seismic inversion',['PyLops/pylops','simpeg/simpeg'],['inversion','solver','least','optimization']),
('Apply convolution operator',['PyLops/pylops'],['convolve','convolution']),
('Solve least squares inverse problem',['PyLops/pylops','simpeg/simpeg'],['least','lsqr','solver','optimization']),
('Run acoustic wave propagation',['devitocodes/devito','ar4/deepwave'],['acoustic','wave','scalar']),
('Run elastic wave propagation',['devitocodes/devito','ar4/deepwave'],['elastic','wave']),
('Full waveform inversion FWI',['devitocodes/devito','ar4/deepwave','PyLops/pylops'],['fwi','wave','gradient','jacobian']),
('Compute wavefield gradient',['ar4/deepwave','devitocodes/devito'],['gradient','jacobian','wave']),
('Build finite difference operator',['devitocodes/devito'],['operator','equation','derivative']),
('Run reservoir simulation',['OPM/opm-simulators'],['flow','simulator','model']),
('Access reservoir simulation results',['OPM/ResInsight','OPM/opm-simulators'],['result','case','summary']),
('Visualize reservoir model',['OPM/ResInsight'],['view','display','case','plot']),
('Work with corner point grids',['equinor/xtgeo','OPM/ResInsight'],['grid','corner']),
('Read well data',['equinor/xtgeo'],['well','read']),
('Work with surfaces',['equinor/xtgeo'],['surface','regular']),
('Geomechanics simulation',['GEOS-DEV/GEOS','OPM/ResInsight'],['geomech','mechanic','stress']),
('Mesh or grid operations',['GEOS-DEV/GEOS','equinor/xtgeo'],['mesh','grid']),
('Read Eclipse reservoir data',['OPM/ResInsight','equinor/xtgeo'],['eclipse','egrid','grid','case']),
('Extract seismic gather',['equinor/segyio','trhallam/segysak'],['gather']),
('Access seismic depth slice',['equinor/segyio'],['depth','slice']),
('Find seismic samples and offsets',['equinor/segyio'],['sample','offset']),
]
STOP={'how','do','i','a','an','the','to','from','with','and','or','for','of','into','get','find','work','use','run','perform','access','read'}
def toks(s):return [x for x in re.split(r'[^a-z0-9+#.-]+',s.lower()) if len(x)>1 and x not in STOP]
def flatten(payload):
 out=[]
 for r in payload.get('repositories',[]):
  repo=r['repository']
  for f in r.get('functions',[]):out.append((repo,f))
 return out
def search(rows,q,k=5):
 qt=toks(q); results=[]
 for repo,f in rows:
  name=str(f.get('name','')).lower(); desc=str(f.get('description','')).lower(); sig=str(f.get('signature','')).lower(); path=str(f.get('source_file','')).lower(); blob=' '.join((name,desc,sig,path))
  score=0.0
  for t in qt:
   if t in name:score+=4
   if t in desc:score+=2.5
   if t in sig:score+=1.5
   if t in path:score+=0.5
  score+=min(float(f.get('quality_score',0)),10)*0.12
  if 'experimental' in path:score-=3
  if 'deprecated' in desc:score-=3
  if f.get('api_level')=='primary_public':score+=0.5
  if score>1:results.append((score,repo,f))
 return sorted(results,key=lambda x:(-x[0],-float(x[2].get('quality_score',0))))[:k]
def main():
 p=json.loads((DATA/'functions.json').read_text(encoding='utf-8')); rows=flatten(p); report=[]; repo_hit=func_hit=0
 for q,repos,hints in TESTS:
  r=search(rows,q); rh=any(repo in repos for _,repo,_ in r); fh=any(repo in repos and any(h in str(f.get('name','')).lower() or h in str(f.get('description','')).lower() for h in hints) for _,repo,f in r)
  repo_hit+=rh;func_hit+=fh
  report.append({'query':q,'expected_repositories':repos,'repository_top5_hit':rh,'useful_function_top5_hit':fh,'results':[{'score':round(s,2),'repository':repo,'name':f.get('name'),'signature':f.get('signature'),'description':f.get('description'),'source_file':f.get('source_file'),'api_level':f.get('api_level')} for s,repo,f in r]})
 n=len(TESTS); summary={'generated_from':p.get('generated_at'),'queries':n,'repository_top5_accuracy':round(repo_hit/n,3),'useful_function_top5_accuracy':round(func_hit/n,3),'target':0.80}
 out={'summary':summary,'tests':report}; (DATA/'function_search_benchmark.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(summary,indent=2))
 for x in report:
  if not x['useful_function_top5_hit']:print('MISS:',x['query'],'=>',[(y['repository'],y['name']) for y in x['results']])
if __name__=='__main__':main()
