"""Compare fresh distributions and exercise source/installed shared-view solver and operation contracts."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / ".tmp/pcuc-cohorts/dist"
INSTALLED = ROOT / ".tmp/pcuc-cohorts/installed"

PROGRAM = r'''
import json,sys
from pathlib import Path
from PIL import Image
from fastapi.testclient import TestClient
from typer.testing import CliRunner
import riposte.store as store
from riposte.cli import app
from riposte.errors import RiposteError
from riposte.server import create_app
from riposte.terminal.service import Request,execute

imports,workspace=map(Path,sys.argv[1:])
assert Path(store.__file__).resolve()==imports/'riposte/store.py'
from riposte.records import RequestValues, ImageInfo
assert type(RequestValues()) is dict
first,second=Request('doctor'),Request('doctor')
first.values['plan_id']='a'*64
assert second.values=={} and first.values is not second.values
assert 'relative' in ImageInfo.__optional_keys__
assert {'mode','viewer','date','width','height','chunks','metadata','sha256'} <= ImageInfo.__required_keys__

source=workspace/'original.png';Image.new('RGB',(24,16),(30,60,100)).save(source)
before=source.read_bytes(),source.stat().st_mtime_ns
runner=CliRunner();args=['--json','sort',str(workspace),'--date-mode','modified']
preview=runner.invoke(app,args);assert preview.exit_code==0,preview.output
plan=json.loads(preview.stdout);assert len(plan['plan_id'])==64 and plan['files'][0]['action']=='SORT'
assert sorted(p.name for p in workspace.iterdir())==['original.png']
missing=runner.invoke(app,[*args,'--apply'])
assert missing.exit_code==2 and json.loads(missing.stderr)['error']=='SORT_PREVIEW_REQUIRED'
late=workspace/'new.png';late.write_bytes(before[0])
stale=runner.invoke(app,[*args,'--apply','--plan-id',plan['plan_id']])
assert stale.exit_code==2 and json.loads(stale.stderr)['error']=='SORT_PREVIEW_CHANGED'
assert not (workspace/'.riposte').exists() and not (workspace/'.riposte-operation.lease').exists()
late.unlink()
# A removed-and-restored directory entry requires a fresh inspection.
preview=runner.invoke(app,args);plan=json.loads(preview.stdout)
assert runner.invoke(app,[*args,'--apply','--plan-id',plan['plan_id']]).exit_code==0
assert store.catalog(workspace)[0]['relative']==plan['files'][0]['destination']
row=store.catalog(workspace)[0]
from unittest.mock import patch
with patch.object(store,'catalog',side_effect=AssertionError('indexed lookup must not materialize catalog')):
    assert store.find_image(workspace,row['id'])==row
from riposte.catalog_guard import CatalogGuard
from contextlib import closing
with closing(CatalogGuard(workspace,'SORT_PREVIEW_CHANGED')) as guard:
    with guard.write() as db:
        db.execute('UPDATE images SET date_source=? WHERE id=?',('embedded',row['id']))
        db.commit()
    guard.check()
    with closing(store.connect(workspace)) as other:
        other.execute('UPDATE images SET date_source=? WHERE id=?',(row['date_source'],row['id']))
        other.commit()
    try:guard.check()
    except RiposteError as exc:assert exc.code=='SORT_PREVIEW_CHANGED'
    else:raise AssertionError('external commit was not detected')
from riposte.organizer import audit_workspace
assert audit_workspace(workspace)['checkpoint']=='COMPLETE'

undo=execute(Request('undo-sort',workspace))
assert execute(Request('undo-sort-apply',workspace,{'sort_id':undo['sort_id']}))['checkpoint']=='COMPLETE'
assert (source.read_bytes(),source.stat().st_mtime_ns)==before

api=create_app(workspace,token='test')
with TestClient(api) as client:
    def job(body):
        response=client.post('/api/organize',headers={'x-riposte-token':'test'},json=body)
        assert response.status_code==200,response.text
        api.state.jobs.pool.submit(lambda:None).result(timeout=15)
        return next(j for j in api.state.jobs.snapshot() if j['id']==response.json()['job_id'])
    options={'date_mode':'modified'}
    result=job(options);assert result['state']=='done'
    applied=job({**options,'apply':True,'acknowledge_source_removal':True,'plan_id':result['result']['plan_id']})
    assert applied['state']=='done',applied
undo=execute(Request('undo-sort',workspace))
assert execute(Request('undo-sort-apply',workspace,{'sort_id':undo['sort_id']}))['checkpoint']=='COMPLETE'
assert (source.read_bytes(),source.stat().st_mtime_ns)==before

options={'all_images':True,'date_mode':'modified'}
combined=execute(Request('sort-riposte-plan',workspace,options))
for token,error in ((None,'SORT_PREVIEW_REQUIRED'),(combined['sorting']['plan_id'],'SORT_PREVIEW_CHANGED'),(combined['plan_id'],'NO_MODEL_NO_PROTECTION')):
    try:execute(Request('sort-riposte',workspace,{**options,'plan_id':token}))
    except RiposteError as exc:assert exc.code==error,(exc.code,error)
    else:raise AssertionError('unapproved or unconfigured protection executed')
assert (source.read_bytes(),source.stat().st_mtime_ns)==before

from riposte.release_guard import ReleaseConfig, protect_release
class NumericalEncoder:
    device='cpu'
    def __call__(self,x): return x.square()+.15*x
clean=Image.new('RGB',(32,24),(90,120,150))
selected,proof=protect_release(clean,[NumericalEncoder()],ReleaseConfig(steps=2,restarts=1))
assert proof['search_policy']['gradient']=='SHARED_VIEW_STREAMED_VJP'
assert proof['quality']['status']=='PASS' and proof['ai_protection']=='UNVERIFIED'
assert min(row['score'] for row in proof['contexts'])>proof['selection']['initial_min_context_score']

from riposte.organizer import organize, plan
from riposte.policy import Policy
from riposte.lab import compare_external
from riposte.generation import controlled_generation
import riposte.generation as generation_module
from riposte.experiment import ENDPOINTS
policy=Policy(date_mode='modified')
organize(workspace,policy,plan_id=plan(workspace,policy)['plan_id'])
row=store.catalog(workspace)[0]
trial=compare_external(workspace,row['id'],workspace/row['relative'])
class SyntheticGenerator:
    identity={'kind':'SYNTHETIC_PACKAGE_SMOKE'}
    def __init__(self,*args): pass
    def __call__(self,image,seed,steps):
        assert list((workspace/'.riposte/experiments').glob('*/protocol.json'))
        return [image.copy()]
with patch.object(generation_module,'LocalGenerator',SyntheticGenerator):
    run=controlled_generation(workspace,trial['id'],workspace,seeds=(7,),views=('identity',),steps=1)
status=execute(Request('experiment',workspace,{'run_id':run['id']}))
assert status['outcome']['status']=='COMPLETE'
packet=runner.invoke(app,['--json','experiment-packet',str(workspace),run['id']])
assert packet.exit_code==0,packet.output
from zipfile import ZipFile
with ZipFile(workspace/json.loads(packet.stdout)['relative']) as archive:
    ratings=json.loads(archive.read('ratings.json'))
    assert len(ratings['ratings'])==5
    assert not any('candidate' in name for name in archive.namelist())
for row in ratings['ratings'].values():
    row.update(dict.fromkeys(ENDPOINTS,True))
ratings_path=workspace/'.riposte/ratings-smoke.json'
ratings_path.write_text(json.dumps(ratings))
review=runner.invoke(app,['--json','experiment-review',str(workspace),run['id'],'--ratings',str(ratings_path)])
assert review.exit_code==0,review.output
assert json.loads(review.stdout)['analysis']['contrast']['value']==0
assert execute(Request('experiment',workspace,{'run_id':run['id']}))['reviews']

import tempfile
from riposte.cohort import cohort_challenge,cohort_status
with tempfile.TemporaryDirectory(prefix='riposte-cohort-package-') as folder:
    cohort_root=Path(folder)
    for index in range(2):
        Image.new('RGB',(24,16),(70+30*index,90,120)).save(cohort_root/f'{index}.png')
    organize(cohort_root,policy,plan_id=plan(cohort_root,policy)['plan_id'])
    trials=[compare_external(cohort_root,row['id'],cohort_root/row['relative']) for row in store.catalog(cohort_root)]
    class CohortGenerator:
        identity={'kind':'SYNTHETIC_COHORT_PACKAGE_SMOKE'}
        def __init__(self,*args):pass
        def __call__(self,image,seed,steps):
            assert list((cohort_root/'.riposte/cohorts').glob('*/protocol.json'))
            return [image.copy()]
    with patch.object(generation_module,'LocalGenerator',CohortGenerator):
        cohort=cohort_challenge(cohort_root,[trial['id'] for trial in trials],cohort_root,2,seeds=(7,),views=('identity',),steps=1)
    assert cohort['summary']['bounds']['lower']['value']==-1
    assert cohort['summary']['bounds']['upper']['value']==1
    for member in cohort['members']:
        status=execute(Request('experiment',cohort_root,{'run_id':member['run_id']}))
        ratings={'protocol_sha256':status['sha256'],'ratings':{sample:dict.fromkeys(ENDPOINTS,True) for group in status['protocol']['groups'] for sample in group['samples'].values()}}
        ratings_path=cohort_root/'.riposte/cohort-smoke-ratings.json';ratings_path.write_text(json.dumps(ratings))
        execute(Request('experiment-review',cohort_root,{'run_id':member['run_id'],'ratings':ratings_path}))
    inspected=runner.invoke(app,['--json','cohort',str(cohort_root),cohort['protocol']['id']])
    assert inspected.exit_code==0,inspected.output
    assert json.loads(inspected.stdout)['summary']['mean']['value']==0
    assert cohort_status(cohort_root,cohort['protocol']['id'])['summary']['scored_artworks']==2

print(json.dumps({'cohort_commit_generation_review_bounds':'PASS','committed_experiment_packet_review':'PASS','shared_view_production_solver':'PASS','typed_record_defaults_and_keys':'PASS','indexed_lookup':'PASS','owned_and_external_commits':'PASS','catalog_audit':'PASS','ordinary_cli':'PASS','stale_no_initial_state':'PASS','api':'PASS','exact_undo':'PASS','combined_receipt_and_model_gate':'PASS'}))
'''


def main():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    name = f"riposte_studio-{version}"
    sources = {p.relative_to(ROOT / "src").as_posix(): p.read_bytes()
               for p in (ROOT / "src/riposte").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    with ZipFile(DIST / f"{name}-py3-none-any.whl") as wheel, tarfile.open(DIST / f"{name}.tar.gz") as sdist:
        assert {p for p in wheel.namelist() if p.startswith("riposte/")} == set(sources)
        assert {p.relative_to(INSTALLED).as_posix() for p in (INSTALLED / "riposte").rglob("*")
                if p.is_file() and "__pycache__" not in p.parts} == set(sources)
        for path, data in sources.items():
            assert wheel.read(path) == sdist.extractfile(f"{name}/src/{path}").read() == (INSTALLED / path).read_bytes() == data
        for path in ("INSTALL.ps1", "INSTALL.sh", "START.ps1", "START.sh", "START.cmd", "riposte.cmd", "uv.lock",
                     "README.md", "docs/DESIGN.md", "docs/UX-CONTRACT.md", "docs/CLI.md", "docs/REBUILD.md", "docs/PCUC.md"):
            assert sdist.extractfile(f"{name}/{path}").read() == (ROOT / path).read_bytes()
    checks = {}
    for key, imports in (("source", ROOT / "src"), ("installed", INSTALLED)):
        with tempfile.TemporaryDirectory(prefix="riposte-pcuc-package-") as directory:
            run = subprocess.run([sys.executable, "-c", PROGRAM, str(imports), directory], cwd=directory,
                                 env={**os.environ, "PYTHONPATH": str(imports), "PYTHONDONTWRITEBYTECODE": "1"},
                                 capture_output=True, text=True, encoding="utf-8", timeout=60)
            assert run.returncode == 0, run.stdout + run.stderr
            checks[key] = json.loads(run.stdout)
    return {"result": "PASS", "version": version, "application_files": len(sources), "checks": checks,
            "artifact_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DIST.iterdir()) if p.suffix in {".whl", ".gz"}},
            "scope": "Fresh source/sdist/wheel/isolated-target equality, committed cohort/generation/primary-review/bounds and experiment/packet/review workflows with synthetic generators and real shared-view production solver with synthetic encoder, record defaults/optional keys, indexed lookup, owned/external revision checks, audit and CLI/API/service preview/apply/exact-undo checks. Combined missing/stale receipt and missing-model gates. Existing Windows dependencies; not clean bootstrap, real-model execution or native Linux/macOS qualification."}


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
