"""Optional synthetic-oracle UI QA artifacts. NEVER pretrained efficacy evidence.

Run only in the synthetic demo created by make_demo.py. This writes no real
artwork. The marker check is intentional; do not relax it for a user collection.
"""
from pathlib import Path
import json
import argparse
from PIL import Image, ImageEnhance
from riposte.store import workspace_lock,catalog,state_relative,safe_child
from riposte.sanitize import social_render
from riposte.lab import _store_trial
from riposte.coupled import protect_coupled,CoupledConfig
from riposte.qualification import qualify_trial
from riposte.generation import controlled_generation
import riposte.models as models
import riposte.generation as generation

def run(root:Path):
    if not (root / state_relative(root, "DEMO")).is_file():
        raise RuntimeError("SYNTHETIC_DEMO_WORKSPACE_REQUIRED")
    import torch
    torch.set_num_threads(1)
    marker=safe_child(root,state_relative(root,'DEMO'))
    if marker.read_text()!='SYNTHETIC_FIXTURES\n':raise RuntimeError('SYNTHETIC_DEMO_REQUIRED')
    class SyntheticEncoder:
        device='cpu';identity={'kind':'SYNTHETIC_TEST_ORACLE_NOT_PRETRAINED','weights_sha256':'a'*64}
        def __init__(self,*args,**kwargs):pass
        def __call__(self,x):return torch.nn.functional.avg_pool2d(x,4)
    class SyntheticGenerator:
        identity={'kind':'SYNTHETIC_TEST_ADAPTER_NOT_PRETRAINED'}
        def __init__(self,*args,**kwargs):pass
        def __call__(self,image,seed,steps):
            # Deterministic identity-like outputs test synchronized review only.
            return [ImageEnhance.Contrast(image).enhance(1.05),ImageEnhance.Contrast(image).enhance(1.1)]
    with workspace_lock(root):
        row=catalog(root)[0]
        with Image.open(safe_child(root,row['relative'])) as image:
            clean=social_render(image,256)
        candidate,report=protect_coupled(clean,[SyntheticEncoder()],CoupledConfig(steps=3))
        report['fixture']='SYNTHETIC_ORACLE_ONLY_NOT_AI_PROTECTION_EVIDENCE'
        trial=_store_trial(root,row,clean,candidate,report)
    old_encoder=models.LocalEncoder;old_generator=generation.LocalGenerator
    try:
        models.LocalEncoder=SyntheticEncoder
        result=qualify_trial(root,trial['id'],[Path('synthetic-oracle')])
        result['fixture']='SYNTHETIC_ORACLE_ONLY'
        safe_child(root,state_relative(root,f"lab/{trial['id']}/evaluations/{result['id']}/report.json")).write_text(json.dumps(result,indent=2))
        generation.LocalGenerator=SyntheticGenerator
        generated=controlled_generation(root,trial['id'],Path('synthetic-adapter'),task='video',seeds=(7,),views=('identity','jpeg70'),steps=1)
        generated['fixture']='SYNTHETIC_STUB_ONLY'
        safe_child(root,state_relative(root,f"generations/{generated['id']}/report.json")).write_text(json.dumps(generated,indent=2))
    finally:
        models.LocalEncoder=old_encoder;generation.LocalGenerator=old_generator
    print(json.dumps({'trial':trial['id'],'qualification':result['id'],'generation':generated['id'],
                      'scope':'SYNTHETIC_ORACLE_AND_STUB_QA_ONLY'},indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);run(parser.parse_args().root)
