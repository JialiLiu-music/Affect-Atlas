"""Mechanical manuscript audit: references, figures, required results and no accidental placeholders."""
from pathlib import Path
import re, json
root=Path(__file__).resolve().parents[1]; p=root/'manuscript_en.md'; text=p.read_text(encoding='utf-8')
assert len(text.splitlines()) > 350
refs=re.findall(r'^\[(\d+)\] ',text,re.M); assert refs==[str(i) for i in range(1,15)]
used={int(n) for n in re.findall(r'\[(\d+)\]',text)}; assert used==set(range(1,15))
for fig in ['fig01_protocol.png','fig02_source_baselines.png','fig03_external_methods.png','fig04_paired_intervals.png','fig05_pool_stability.png','fig06_deam_expansion.png']:
 assert (root/'figures'/fig).exists(),fig
for token in ['13.50%','0.130907451','0.113240858','−0.017666593','334','237','60','20','40,650','291,626']:
 assert token in text,token
for forbidden in ['TODO','TBD','PLACEHOLDER','citation needed','<placeholder>']:
 assert forbidden.lower() not in text.lower(),forbidden
# Check markdown tables have consistent cell counts.
lines=text.splitlines(); tables=0
for i,line in enumerate(lines[:-1]):
 if line.startswith('|') and lines[i+1].startswith('|') and set(lines[i+1].replace('|','').replace('-','').replace(':','').strip())==set():
  n=len(line.strip().strip('|').split('|')); j=i+2
  while j<len(lines) and lines[j].startswith('|'):
   assert len(lines[j].strip().strip('|').split('|'))==n,(i+1,j+1)
   j+=1
  tables+=1
assert tables>=8
manifest=json.loads((root/'figures'/'figure_manifest.json').read_text(encoding='utf-8'))
assert manifest['source_sha256_unchanged_after_generation'] is True
print(json.dumps({'status':'PASS','lines':len(lines),'references':len(refs),'figures':6,'tables':tables},indent=2))
