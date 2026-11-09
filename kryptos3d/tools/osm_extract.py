"""Regenerate the inlined <script id="site"> JSON in ../index.html from OpenStreetMap.

1. curl -A "kryptos-model/1.0" "https://api.openstreetmap.org/api/0.6/map.json?bbox=-77.1510,38.9485,-77.1405,38.9560" -o map.json
2. python3 osm_extract.py map.json   -> writes site.json (metres, origin = OSM Kryptos node 10009124744, x east, z south)
3. Paste site.json into the <script id="site"> tag. NHB sections missing from OSM are added in index.html itself.
"""
import json, math, sys
d=json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'map.json'))['elements']
nodes={e['id']:(e['lat'],e['lon']) for e in d if e['type']=='node'}
ways={e['id']:e for e in d if e['type']=='way'}
LAT,LON=38.952256,-77.1457484
k=111320; kc=k*math.cos(math.radians(LAT))
R=430
def xz(n): la,lo=nodes[n]; return [round((lo-LON)*kc,1), round(-(la-LAT)*k,1)]
def ring(ids): return [xz(n) for n in ids if n in nodes]
def join(segs):
  segs=[s[:] for s in segs if s]; rings=[]
  while segs:
    r=segs.pop(0)
    changed=True
    while r[0]!=r[-1] and changed:
      changed=False
      for i,s in enumerate(segs):
        if s[0]==r[-1]: r+=s[1:]; segs.pop(i); changed=True; break
        if s[-1]==r[-1]: r+=s[::-1][1:]; segs.pop(i); changed=True; break
    rings.append(r)
  return rings
def inside(p,poly):
  x,z=p; c=False
  for i in range(len(poly)):
    x1,z1=poly[i]; x2,z2=poly[i-1]
    if (z1>z)!=(z2>z) and x < (x2-x1)*(z-z1)/(z2-z1)+x1: c=not c
  return c
def near(poly): return any(abs(x)<R and abs(z)<R for x,z in poly)
feats=[]
def add(kind,outer,holes,t):
  if len(outer)<3 or not near(outer): return
  f={'k':kind,'o':outer}
  if holes: f['h']=holes
  if kind=='b':
    h=t.get('height'); lv=t.get('building:levels')
    mh=t.get('min_height'); ml=t.get('building:min_level')
    f['ht']=round(float(h.split()[0]),1) if h else (round(float(lv)*4.0,1) if lv else 8.0)
    if mh: f['mh']=float(mh)
    elif ml: f['mh']=float(ml)*4.0
    f['part']=1 if 'building:part' in t else 0
    for key in ('building:colour','roof:colour','building:material','roof:shape','name','man_made','building:shape'):
      if key in t: f[key.split(':')[-1] if key!='building:colour' else 'bc']=t[key]
  if kind=='hw': f['w']=t['highway']
  feats.append(f)
def classify(t):
  if 'building' in t or 'building:part' in t:
    if t.get('building')=='roof': return None
    return 'b'
  if t.get('amenity') in('parking',) : return 'park'
  if t.get('natural') in ('wood','scrub'): return 'wood'
  if t.get('natural')=='water' or t.get('leisure')=='swimming_pool': return 'water'
  if t.get('landuse') in ('grass','flowerbed') or t.get('leisure') in('garden','common','park'): return t.get('landuse') if t.get('landuse')=='flowerbed' else 'grass'
  if t.get('natural') in('sand','shingle'): return 'sand'
  if t.get('area')=='yes' or t.get('area:highway'): return 'pave'
  return None
used=set()
for e in d:
  if e['type']!='relation': continue
  t=e.get('tags',{}); kind=classify(t)
  if not kind: continue
  outs=join([ring(ways[m['ref']]['nodes']) for m in e['members'] if m['type']=='way' and m['role']=='outer' and m['ref'] in ways])
  ins=join([ring(ways[m['ref']]['nodes']) for m in e['members'] if m['type']=='way' and m['role']=='inner' and m['ref'] in ways])
  for o in outs: add(kind,o,[i for i in ins if i and inside(i[0],o)],t)
  for m in e['members']: used.add(m['ref']) if kind=='b' else None
for w in ways.values():
  t=w.get('tags',{}); 
  if 'highway' in t and t['highway'] in ('service','footway','unclassified','residential','path','pedestrian','steps','secondary','tertiary','primary','trunk'):
    pts=ring(w['nodes'])
    if near(pts) and not t.get('area'): feats.append({'k':'hw','w':t['highway'],'p':pts}); continue
  kind=classify(t)
  if kind and not (kind=='b' and w['id'] in used): add(kind,ring(w['nodes']),[],t)
# drop building outlines that have parts inside
parts=[f for f in feats if f['k']=='b' and f['part']]
for f in feats:
  if f['k']=='b' and not f['part']:
    cs=[(sum(p[0] for p in q['o'])/len(q['o']), sum(p[1] for p in q['o'])/len(q['o'])) for q in parts]
    if any(inside(c,f['o']) for c in cs): f['skipOutline']=1
feats=[f for f in feats if not f.get('skipOutline')]
for f in feats: f.pop('part',None)
from collections import Counter
print(Counter(f['k'] for f in feats), file=sys.stderr)
for f in feats:
  if f['k']=='b' and any(abs(x)<120 and abs(z)<120 for x,z in f['o']): print(f.get('name',''),f['ht'],f.get('mh',0),len(f['o']),f.get('bc',''),f.get('material',''), f['o'][0], file=sys.stderr)
for f in feats:
  if f['k']!='b' and f['k']!='hw' and f['o'] and inside([0,0],f['o']): print('KRYPTOS IN',f['k'],file=sys.stderr)
for n in d:
  if n['type']=='node' and n.get('tags',{}).get('natural')=='tree':
    p=[round((n['lon']-LON)*kc,1), round(-(n['lat']-LAT)*k,1)]
    if abs(p[0])<R and abs(p[1])<R:
      t=n['tags']; f={'k':'tree','p':p}
      if 'leaf_type' in t: f['lt']=t['leaf_type'][0]
      if 'height' in t: f['ht']=float(t['height'].split()[0])
      feats.append(f)
print('trees',sum(1 for f in feats if f['k']=='tree'),file=sys.stderr)
json.dump(feats,open('site.json','w'),separators=(',',':'))
