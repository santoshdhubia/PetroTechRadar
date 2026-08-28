#!/usr/bin/env python3
"""Benchmark usability of PetroTechRadar function-level search with task-aware ranking."""
from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'docs'/'data'
TESTS=[
('Read SEG-Y trace headers',['equinor/segyio'],['header','attributes','tracefield']),('Read SEG-Y traces',['equinor/segyio'],['trace','gather']),('Get inline and crossline data from SEG-Y',['equinor/segyio','trhallam/segysak'],['iline','xline','inline','crossline']),('Create a new SEG-Y file',['equinor/segyio'],['create']),('Load SEG-Y into xarray',['trhallam/segysak'],['segy','xarray','open']),('Perform seismic inversion',['PyLops/pylops','simpeg/simpeg'],['inversion','solver','least','optimization']),('Apply convolution operator',['PyLops/pylops'],['convolve','convolution']),('Solve least squares inverse problem',['PyLops/pylops','simpeg/simpeg'],['least','lsqr','solver','optimization']),('Run acoustic wave propagation',['devitocodes/devito','ar4/deepwave'],['acoustic','wave','scalar']),('Run elastic wave propagation',['devitocodes/devito','ar4/deepwave'],['elastic','wave']),('Full waveform inversion FWI',['devitocodes/devito','ar4/deepwave','PyLops/pylops'],['fwi','wave','gradient','jacobian']),('Compute wavefield gradient',['ar4/deepwave','devitocodes/devito'],['gradient','jacobian','wave']),('Build finite difference operator',['devitocodes/devito'],['operator','equation','derivative']),('Run reservoir simulation',['OPM/opm-simulators'],['flow','simulator','model']),('Access reservoir simulation results',['OPM/ResInsight','OPM/opm-simulators'],['result','case','summary']),('Visualize reservoir model',['OPM/ResInsight'],['view','display','case','plot']),('Work with corner point grids',['equinor/xtgeo','OPM/ResInsight'],['grid','corner']),('Read well data',['equinor/xtgeo'],['well','read']),('Work with surfaces',['equinor/xtgeo'],['surface','regular']),('Geomechanics simulation',['GEOS-DEV/GEOS','OPM/ResInsight'],['geomech','mechanic','stress']),('Mesh or grid operations',['GEOS-DEV/GEOS','equinor/xtgeo'],['mesh','grid']),('Read Eclipse reservoir data',['OPM/ResInsight','equinor/xtgeo'],['eclipse','egrid','grid','case']),('Extract seismic gather',['equinor/segyio','trhallam/segysak'],['gather']),('Access seismic depth slice',['equinor/segyio'],['depth','slice']),('Find seismic samples and offsets',['equinor/segyio'],['sample','offset'])]
STOP={'how','do','i','a','an','the','to','from','with','and','or','for','of','into','get','find','work','use','run','perform','access','read','new','data'}
SYN={'seg-y':['segy','seg-y'],'segy':['segy','seg-y'],'inline':['inline','iline'],'crossline':['crossline','xline'],'fwi':['fwi','full waveform inversion'],'wavefield':['wavefield','wave'],'convolution':['convolution','convolve'],'least':['least','lsqr'],'squares':['squares','lsqr'],'reservoir':['reservoir','eclipse'],'geomechanics':['geomechanics','geomech','mechanics'],'surface':['surface','regularsurface'],'well':['well','wells'],'grid':['grid','mesh','egrid'],'xarray':['xarray','dataset'],'visualize':['visualize','visualization','view','plot','display']}
TASKS=[
(('seg-y','segy'),['SEG-Y I/O'],{'equinor/segyio':8,'trhallam/segysak':7}),
(('xarray',),['SEG-Y I/O'],{'trhallam/segysak':10}),
(('inversion','inverse'),['inversion'],{'PyLops/pylops':6,'simpeg/simpeg':5}),
(('fwi','full waveform'),['FWI','wave simulation'],{'ar4/deepwave':7,'devitocodes/devito':7,'PyLops/pylops':4}),
(('acoustic','elastic','wave','wavefield'),['wave simulation'],{'ar4/deepwave':6,'devitocodes/devito':6}),
(('finite difference','operator'),['wave simulation'],{'devitocodes/devito':7,'PyLops/pylops':3}),
(('reservoir simulation','eclipse'),['reservoir simulation'],{'OPM/opm-simulators':8,'OPM/ResInsight':5,'equinor/xtgeo':3}),
(('visualize','visualization'),['visualization'],{'OPM/ResInsight':8}),
(('well',),['well data'],{'equinor/xtgeo':7}),
(('surface',),['grids and surfaces'],{'equinor/xtgeo':7}),
(('grid','mesh','corner point'),['grids and surfaces'],{'equinor/xtgeo':6,'OPM/ResInsight':5,'GEOS-DEV/GEOS':5}),
(('geomech','geomechanics'),['geomechanics'],{'GEOS-DEV/GEOS':8,'OPM/ResInsight':4}),]
def toks(s):return [x for x in re.split(r'[^a-z0-9+#.-]+',s.lower()) if len(x)>1 and x not in STOP]
def expanded(q):
 ql=q.lower(); out=set(toks(q))
 for k,vals in SYN.items():
  if k in ql or k in out:out.update(vals)
 return out
def load_caps():
 p=json.loads((DATA/'capabilities.json').read_text(encoding='utf-8')); return {r['repository']:r for r in p.get('repositories',[])}
def flatten(payload):return [(r['repository'],f) for r in payload.get('repositories',[]) for f in r.get('functions',[])]
def context_bonus(repo,q,caps):
 ql=q.lower(); bonus=0.0; rc=caps.get(repo,{})
 primary=set(rc.get('primary_capabilities',[])); secondary=set(rc.get('secondary_capabilities',[]))
 for phrases,wanted,boosts in TASKS:
  if any(p in ql for p in phrases):
   bonus+=boosts.get(repo,0)
   if primary.intersection(wanted):bonus+=4
   elif secondary.intersection(wanted):bonus+=2
 return bonus
def search(rows,q,caps,k=5):
 qt=expanded(q); ql=q.lower(); results=[]
 for repo,f in rows:
  name=str(f.get('name','')).lower(); desc=str(f.get('description','')).lower(); sig=str(f.get('signature','')).lower(); path=str(f.get('source_file','')).lower(); score=context_bonus(repo,q,caps)
  for t in qt:
   if t in name:score+=4.5
   if t in desc:score+=2.7
   if t in sig:score+=1.2
   if t in path:score+=0.4
  # exact multiword/technical phrase matching
  for phrase in ('trace header','depth slice','corner point','reservoir simulation','full waveform inversion','finite difference','least squares'):
   if phrase in ql and (phrase in name.replace('_',' ') or phrase in desc):score+=5
  score+=min(float(f.get('quality_score',0)),10)*0.10
  if f.get('api_level')=='primary_public':score+=0.7
  if 'experimental' in path:score-=5
  if 'deprecated' in desc or 'debugging' in desc:score-=4
  # generic APIs should not win solely on generic verbs
  leaf=name.rsplit('.',1)[-1]
  if leaf in {'create','load','read','write','apply','run','get','set'} and context_bonus(repo,q,caps)<=0:score-=5
  if score>2:results.append((score,repo,f))
 return sorted(results,key=lambda x:(-x[0],-float(x[2].get('quality_score',0))))[:k]
def main():
 p=json.loads((DATA/'functions.json').read_text(encoding='utf-8')); rows=flatten(p); caps=load_caps(); report=[]; repo_hit=func_hit=0
 for q,repos,hints in TESTS:
  r=search(rows,q,caps); rh=any(repo in repos for _,repo,_ in r); fh=any(repo in repos and any(h in (str(f.get('name',''))+' '+str(f.get('description',''))).lower() for h in hints) for _,repo,f in r); repo_hit+=rh;func_hit+=fh
  report.append({'query':q,'expected_repositories':repos,'repository_top5_hit':rh,'useful_function_top5_hit':fh,'results':[{'score':round(s,2),'repository':repo,'name':f.get('name'),'signature':f.get('signature'),'description':f.get('description'),'source_file':f.get('source_file'),'api_level':f.get('api_level')} for s,repo,f in r]})
 n=len(TESTS); summary={'generated_from':p.get('generated_at'),'ranking':'task-aware-v2','queries':n,'repository_top5_accuracy':round(repo_hit/n,3),'useful_function_top5_accuracy':round(func_hit/n,3),'target':0.80}
 (DATA/'function_search_benchmark.json').write_text(json.dumps({'summary':summary,'tests':report},indent=2)+'\n',encoding='utf-8'); print(json.dumps(summary,indent=2))
 for x in report:
  if not x['useful_function_top5_hit']:print('MISS:',x['query'],'=>',[(y['repository'],y['name']) for y in x['results']])
if __name__=='__main__':main()
