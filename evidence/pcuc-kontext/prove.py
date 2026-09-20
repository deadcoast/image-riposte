"""Check exact bucket choice, latent lattice and the installed area formula."""
from fractions import Fraction
import hashlib,json,math,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from riposte.kontext import RESOLUTIONS,target_size

cases=0
for width in range(1,65):
    for height in range(1,65):
        selected=target_size(width,height)
        error=abs(Fraction(width,height)-Fraction(*selected))
        assert error==min(abs(Fraction(width,height)-Fraction(*bucket)) for bucket in RESOLUTIONS)
        cases+=1
for width,height in (*RESOLUTIONS,(1,100000),(100000,1)):
    assert target_size(width,height) in RESOLUTIONS
    cases+=1
for width,height in RESOLUTIONS:
    assert width%16==height%16==0
    assert target_size(width,height)==(width,height)
    ratio=width/height;area=width*height
    # Same operation ordering as the actual installed pipeline.
    assert (round((area*ratio)**.5)//16*16,round((area/ratio)**.5)//16*16)==(width,height)
from diffusers.pipelines.flux.pipeline_flux_kontext import PREFERRED_KONTEXT_RESOLUTIONS
assert tuple(PREFERRED_KONTEXT_RESOLUTIONS)==RESOLUTIONS
sources={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
         for p in (ROOT/'src/riposte').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
result={'result':'PASS','aspect_cases':cases,'lattice_and_area_cases':len(RESOLUTIONS),
        'installed_buckets_equal':True,'sources':sources,
        'scope':'Exact finite bucket selection and packing geometry; not image quality or efficacy'}
Path(__file__).with_name('proof.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='sources'},indent=2))
