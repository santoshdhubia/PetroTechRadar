#!/usr/bin/env python3
"""Build a quality-ranked public API/capability index for PetroTechRadar."""
from __future__ import annotations
import ast, json, os, re, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT_DIR=ROOT/'docs'/'data'; SHARD_DIR=OUT_DIR/'functions'
TOKEN=os.getenv('GITHUB_TOKEN',''); MODE=os.getenv('CAPABILITY_MODE','test')
LEGACY_PER_REPO=int(os.getenv('LEGACY_FUNCTIONS_PER_REPO','300')); MAX_INDEXED_APIS=int(os.getenv('MAX_INDEXED_APIS','2000')); SEARCH_TERM_LIMIT=int(os.getenv('SEARCH_TERM_LIMIT','80'))
TEST_REPOS=['equinor/segyio','trhallam/segysak','PyLops/pylops','simpeg/simpeg','devitocodes/devito','ar4/deepwave','OPM/opm-simulators','OPM/ResInsight','GEOS-DEV/GEOS','equinor/xtgeo']
MAJOR_ORGS={'Equinor','OPM','NVIDIA','GEOS Consortium','SimPEG','PyLops','GemPy','pyGIMLi','Loop3D','Devito','OpendTect','SEG-Y'}
CAPABILITY_TERMS={
'SEG-Y I/O':['seg-y','segy','trace header','binary header'],'seismic processing':['seismic processing','filtering','stacking','migration'],
'inversion':['inversion','inverse problem','adjoint','gradient based'],'FWI':['full waveform inversion','fwi'],'wave simulation':['wave equation','wave propagation','acoustic','elastic wave'],
'reservoir simulation':['reservoir simulation','black oil','compositional','flow simulator'],'geomechanics':['geomechanics','poroelastic','rock mechanics'],
'geological modelling':['geological model','structural model','implicit modelling'],'grids and surfaces':['grid model','surface model','corner point grid','mesh'],
'well data':['well log','well data','trajectory','well path'],'visualization':['visualization','3d viewer','interactive viewer'],'data assimilation':['data assimilation','ensemble smoother','history matching']}
GENERIC={'keys','values','items','update','close','flush','reload','sort','copy','get','set','read','write','run','main','size','begin','end'}
SEARCH_STOP=GENERIC|{'self','cls','none','true','false','return','returns','value','values','data','file','from','into','using','with','this','that','class','function','method','object','array','list','string','int','float','bool','const','public','private','src','python','include'}
def shard_name(repo):return repo.lower().replace('/','__')+'.json'
def repo_search_terms(repo_row):
 text=' '.join([repo_row.get('repository',''),repo_row.get('description') or '',repo_row.get('language') or '',*repo_row.get('primary_capabilities',[]),*repo_row.get('secondary_capabilities',[])])
 counts={}
 def add(v,w=1):
  for t in re.split(r'[^a-z0-9+#.-]+',str(v).lower()):
   if len(t)>2 and t not in SEARCH_STOP:counts[t]=counts.get(t,0)+w
 add(text,4)
 for f in repo_row.get('functions',[]):
  add(f.get('name',''),3);add(f.get('description',''),1);add(f.get('source_file',''),1)
 return [k for k,_ in sorted(counts.items(),key=lambda kv:(-kv[1],kv[0]))[:SEARCH_TERM_LIMIT]]
def api(url):
 h={'Accept':'application/vnd.github+json','User-Agent':'PetroTechRadar-CapabilityIndexer/0.3'}
 if TOKEN:h['Authorization']=f'Bearer {TOKEN}'
 with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=30) as r:return json.loads(r.read().decode())
def raw(url):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'PetroTechRadar-CapabilityIndexer/0.3'}),timeout=30) as r:return r.read().decode('utf-8',errors='replace')
def meta(repo):return api(f'https://api.github.com/repos/{repo}')
def tree(repo,branch):return api(f"https://api.github.com/repos/{repo}/git/trees/{urllib.parse.quote(branch,safe='')}?recursive=1").get('tree',[])
def readme(repo):
 try:
  d=api(f'https://api.github.com/repos/{repo}/readme'); return raw(d['download_url']) if d.get('download_url') else ''
 except Exception:return ''
def modname(p):
 s=p.replace('/','.')
 for x in ('src.','python.'): s=s[len(x):] if s.startswith(x) else s
 return re.sub(r'\.(py|pyi)$','',s).replace('.__init__','')
def sig(n):
 a=n.args; pos=list(a.posonlyargs)+list(a.args); defs=[None]*(len(pos)-len(a.defaults))+list(a.defaults); out=[]
 for x,d in zip(pos,defs):
  z=x.arg
  if d is not None:
   try:z+='='+ast.unparse(d)
   except:z+='=...'
  out.append(z)
 if a.vararg:out.append('*'+a.vararg.arg)
 out += [x.arg for x in a.kwonlyargs]
 if a.kwarg:out.append('**'+a.kwarg.arg)
 return f"{n.name}({', '.join(out)})"
def ent(name,kind,signature,desc,path,exported=False):return {'name':name,'kind':kind,'signature':signature,'description':desc.strip()[:500],'source_file':path,'exported':exported}
def py_extract(path,src):
 try:t=ast.parse(src)
 except SyntaxError:return []
 m=modname(path); out=[]; exports=set()
 # __all__ and import/re-export names make package APIs visible even when implementation lives deeper.
 for n in t.body:
  if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='__all__' for x in n.targets):
   if isinstance(n.value,(ast.List,ast.Tuple,ast.Set)):
    exports.update(x.value for x in n.value.elts if isinstance(x,ast.Constant) and isinstance(x.value,str))
  if path.endswith('__init__.py') and isinstance(n,(ast.ImportFrom,ast.Import)):
   for a in n.names:
    if not a.name.startswith('_'): exports.add(a.asname or a.name.rsplit('.',1)[-1])
 for n in t.body:
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and not n.name.startswith('_'):
   d=ast.get_docstring(n) or ''; out.append(ent(f'{m}.{n.name}' if m else n.name,'function',sig(n),d.split('\n\n')[0],path,n.name in exports or path.endswith('__init__.py')))
  elif isinstance(n,ast.ClassDef) and not n.name.startswith('_'):
   d=ast.get_docstring(n) or ''; cn=f'{m}.{n.name}' if m else n.name; out.append(ent(cn,'class',n.name,d.split('\n\n')[0],path,n.name in exports or path.endswith('__init__.py')))
   for c in n.body:
    if isinstance(c,(ast.FunctionDef,ast.AsyncFunctionDef)) and not c.name.startswith('_'):
     d=ast.get_docstring(c) or ''; out.append(ent(f'{cn}.{c.name}','method',sig(c),d.split('\n\n')[0],path,False))
 return out
def cpp_extract(path,src):
 out=[]
 # Capture declarations and inline definitions from public/include/API headers, including templates and qualifiers.
 rx=re.compile(r'^[ \t]*(?:template\s*<[^;{}]+>\s*)?(?:inline\s+|static\s+|virtual\s+|constexpr\s+|explicit\s+|friend\s+)*[\w:<>,*&\s]+?\s+([A-Za-z_]\w*)\s*\(([^;{}()]*(?:\([^)]*\)[^;{}()]*)*)\)\s*(?:const\s*)?(?:noexcept(?:\([^)]*\))?\s*)?(?:override\s*)?(?:;|\{)',re.M)
 for name,args in rx.findall(src):
  if name.startswith('_') or name in {'if','for','while','switch','return'}:continue
  out.append(ent(name,'function/declaration',f"{name}({re.sub(r'\s+',' ',args).strip()})",'',path,True))
 # Public class/struct types are useful callable/API anchors in C++ projects.
 for kind,name in re.findall(r'\b(class|struct)\s+(?:\w+\s+)*([A-Za-z_]\w*)\s*(?::[^\{]+)?\{',src):
  if not name.startswith('_'):out.append(ent(name,kind,name,'',path,True))
 return out[:500]
def other_extract(path,src):
 out=[]
 if path.endswith('.java'):
  for n,a in re.findall(r'public\s+(?:static\s+)?(?:final\s+)?[\w<>\[\], ?]+\s+([A-Za-z_]\w*)\s*\(([^)]*)\)',src):out.append(ent(n,'method',f'{n}({a})','',path,True))
 else:
  for n,a in re.findall(r'export\s+(?:async\s+)?(?:function|class)\s+([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?',src):out.append(ent(n,'export',f'{n}({a})' if a else n,'',path,True))
 return out[:400]
def classify(f,rlow):
 d=f.get('description',''); short=f['name'].rsplit('.',1)[-1]; p=f['source_file'].lower(); score=0; ev=[]
 if d:score+=3;ev.append('documentation')
 if len(d)>=40:score+=1
 if f.get('exported'):score+=5;ev.append('package/public export')
 if len(short)>=4 and re.search(rf'(?<!\w){re.escape(short.lower())}(?!\w)',rlow):score+=4;ev.append('mentioned in README')
 if '/include/' in p or p.startswith('include/'):score+=3;ev.append('public header')
 if 'internal use' in d.lower() or '/internal/' in p or '/detail/' in p:score-=5;ev.append('internal hint')
 if short.lower() in GENERIC and not d and not f.get('exported'):score-=3
 return ('primary_public' if score>=7 else 'documented_public' if score>=3 else 'internal_or_low_value',score,ev)
def caps(desc,r):
 dl=(desc or '').lower(); rl=r.lower(); pri=[];sec=[];scores={}
 for cap,terms in CAPABILITY_TERMS.items():
  dh=sum(t in dl for t in terms); rh=sum(rl.count(t) for t in terms); sc=dh*5+min(rh,5)
  if sc:scores[cap]=sc
  if dh or rh>=2:pri.append(cap)
  elif rh==1:sec.append(cap)
 return pri,sec,scores
def candidates(t):
 fs=[x['path'] for x in t if x.get('type')=='blob' and x.get('size',0)<=300000]; sel=[]
 for p in fs:
  l=p.lower(); b=l.rsplit('/',1)[-1]
  if any(x in l for x in ('/test/','/tests/','/examples/','/vendor/','/third_party/','/build/')):continue
  if p.endswith(('.py','.pyi')):
   # Include package entrypoints plus likely public operator/API modules; fixes libraries such as PyLops.
   if '__init__.py' in l or '/api' in l or '/io' in l or '/tools' in l or '/core' in l or '/operators/' in l or '/optimization/' in l or '/basicoperators/' in l or l.count('/')<=4:sel.append(p)
  elif p.endswith(('.h','.hpp','.hh')) and ('include/' in l or '/api' in l or l.count('/')<=4):sel.append(p)
  elif p.endswith('.java') and ('src/main/' in l or l.count('/')<=4):sel.append(p)
  elif p.endswith(('.ts','.tsx','.js')) and 'src/' in l and ('index.' in b or 'api' in l):sel.append(p)
 # Higher allowance, but final ranking/caps keep output bounded.
 return sel[:100]
def index(repo):
 print('Indexing',repo,flush=True); m=meta(repo); branch=m.get('default_branch','main'); tr=tree(repo,branch); rd=readme(repo); rl=rd.lower(); funcs=[]
 for p in candidates(tr):
  u=f"https://raw.githubusercontent.com/{repo}/{urllib.parse.quote(branch,safe='')}/{urllib.parse.quote(p,safe='/')}"
  try:s=raw(u)
  except Exception as e:print(' skip',p,e);continue
  funcs += py_extract(p,s) if p.endswith(('.py','.pyi')) else cpp_extract(p,s) if p.endswith(('.h','.hpp','.hh')) else other_extract(p,s); time.sleep(.015)
 dd={}
 for f in funcs:
  k=(f['name'],f.get('signature',''))
  if k not in dd or (not dd[k].get('description') and f.get('description')):dd[k]=f
 counts={'primary_public':0,'documented_public':0,'internal_or_low_value':0}; usable=[]
 for f in dd.values():
  lev,sc,ev=classify(f,rl); f['api_level']=lev;f['quality_score']=sc;f['evidence']=ev;f.pop('exported',None);counts[lev]+=1
  if lev!='internal_or_low_value':usable.append(f)
 usable.sort(key=lambda x:(-x['quality_score'],0 if x.get('description') else 1,x['name']))
 # Keep a high safety ceiling, but do not truncate useful APIs at the old 300-symbol limit.
 usable=usable[:MAX_INDEXED_APIS]
 pri,sec,cs=caps(m.get('description') or '',rd[:150000])
 return {'repository':repo,'url':m.get('html_url'),'language':m.get('language'),'description':m.get('description'),'default_branch':branch,'primary_capabilities':pri,'secondary_capabilities':sec,'capability_scores':cs,'public_api_count':len(usable),'api_level_counts':counts,'functions':usable}
def choose():
 if MODE=='test':return TEST_REPOS
 r=json.loads((OUT_DIR/'radar.json').read_text(encoding='utf-8'));return sorted({x['repository'] for x in r.get('repositories',[]) if x.get('tier')=='Core' and x.get('organization') in MAJOR_ORGS})
def main():
 OUT_DIR.mkdir(parents=True,exist_ok=True); SHARD_DIR.mkdir(parents=True,exist_ok=True); indexed=[];errors=[]
 for repo in choose():
  try:indexed.append(index(repo))
  except Exception as e:print('ERROR',repo,e);errors.append({'repository':repo,'error':str(e)})
 now=datetime.now(timezone.utc).isoformat()
 # Remove stale shards so deleted/unindexed repositories cannot linger in MCP search.
 for p in SHARD_DIR.glob('*.json'):p.unlink()
 shard_map={}; search_repos=[]; full_count=0
 for x in indexed:
  shard=f"functions/{shard_name(x['repository'])}"; shard_map[x['repository']]=shard; full_count+=len(x['functions'])
  payload={'generated_at':now,'repository':x['repository'],'language':x.get('language'),'function_count':len(x['functions']),'functions':x['functions']}
  (OUT_DIR/shard).write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
  search_repos.append({'repository':x['repository'],'shard':shard,'language':x.get('language'),'description':x.get('description'),'primary_capabilities':x.get('primary_capabilities',[]),'secondary_capabilities':x.get('secondary_capabilities',[]),'public_api_count':len(x['functions']),'terms':repo_search_terms(x)})
 c={'generated_at':now,'mode':MODE,'repository_count':len(indexed),'errors':errors,'repositories':[{k:v for k,v in x.items() if k!='functions'} for x in indexed]}
 # Legacy aggregate remains intentionally bounded for backward compatibility; MCP uses shards.
 legacy={'generated_at':now,'mode':MODE,'repository_count':len(indexed),'function_count':sum(min(len(x['functions']),LEGACY_PER_REPO) for x in indexed),'legacy_per_repository_limit':LEGACY_PER_REPO,'repositories':[{'repository':x['repository'],'functions':x['functions'][:LEGACY_PER_REPO]} for x in indexed]}
 search_index={'generated_at':now,'mode':MODE,'repository_count':len(indexed),'repositories':search_repos}
 manifest={'version':1,'generated_at':now,'mode':MODE,'repository_count':len(indexed),'function_count':full_count,'shards':shard_map,'legacy_functions_file':'functions.json','search_index':'search_index.json'}
 (OUT_DIR/'capabilities.json').write_text(json.dumps(c,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 (OUT_DIR/'functions.json').write_text(json.dumps(legacy,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 (OUT_DIR/'search_index.json').write_text(json.dumps(search_index,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 (OUT_DIR/'function_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print(f"Indexed {len(indexed)} repos, {full_count} usable API symbols in shards, {legacy['function_count']} legacy symbols, {len(errors)} errors")
if __name__=='__main__':main()
