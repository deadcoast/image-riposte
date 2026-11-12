"""Check PAC-042 evidence and prepare separate source-bound PACER acceptance."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import tarfile
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
import zipfile
from typer.main import get_command
from riposte.cli import app

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).parent


def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def previous():
    spec=importlib.util.spec_from_file_location('documentation_basis',ROOT/'evidence/documentation-contracts/verify.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def manifest():
    result=previous().manifest();result['generator']='evidence/private-library-search/verify.py --manifest'
    return result


def counts(name):
    suites=ET.parse(HERE/name).getroot().findall('testsuite')
    result={k:sum(int(s.attrib[k]) for s in suites) for k in ('tests','failures','errors','skipped')}
    result['passed']=result['tests']-result['failures']-result['errors']-result['skipped']
    return result


def documentation():
    basis=previous();group=get_command(app);examples=[];links=0
    for name in basis.CURRENT:
        path=ROOT/name
        for number,argv in basis.examples(path):
            try:
                with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()),group.make_context('riposte',argv[1:]) as ctx:
                    rest=[*ctx._protected_args,*ctx.args]
                    if rest:
                        command_name,command,tail=group.resolve_command(ctx,rest)
                        with command.make_context(command_name,tail,parent=ctx):pass
            except Exception as exc:
                assert type(exc).__name__=='Exit' and getattr(exc,'exit_code',None)==0 and set(argv)&{'--help','--version'},(name,number,exc)
            examples.append({'document':name,'line':number,'argv':argv})
        for target in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)',path.read_text(encoding='utf-8')):
            target=target.split(' "',1)[0].strip('<>');parts=urlsplit(target)
            if parts.scheme or parts.netloc:continue
            linked=(path.parent/unquote(parts.path)).resolve() if parts.path else path
            assert linked.exists(),(name,target);links+=1
            if parts.fragment and linked.suffix=='.md':assert unquote(parts.fragment) in basis.anchors(linked),(name,target)
    inventory=set(re.findall(r'^\| `([a-z][a-z-]*)\b',(ROOT/'docs/CLI.md').read_text(encoding='utf-8'),re.M))
    assert inventory==set(group.commands)
    with zipfile.ZipFile(basis.HERE/'before.zip') as baseline:
        for name in basis.ARCHIVES:assert baseline.read(name)==(ROOT/name).read_bytes(),name
        for name,marker in basis.WRAPPERS.items():
            old=baseline.read(name);new=(ROOT/name).read_bytes();needle=marker.encode()
            assert old[old.index(needle):]==new[new.index(needle):],name
    result={'result':'PASS','parsed_examples':examples,'commands':sorted(inventory),'links':links,
            'historical_payloads':len(basis.ARCHIVES)+len(basis.WRAPPERS),
            'scope':'Shipping parser and links; examples are not executed as media/model operations.'}
    (HERE/'documentation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def verify():
    source=read(ROOT/'typing/evidence/source-reviewed-private-library-search.json')
    assert all(digest(ROOT/p)==sha for p,sha in source.items())
    before=read(HERE/'source-before.json')
    changed=sorted(p for p in source.keys()|before.keys() if source.get(p)!=before.get(p))
    assert changed==read(HERE/'contract-review.json')['owners']
    assert read(ROOT/'RELEASE-MANIFEST.json')==manifest(),'development manifest drift'
    contracts=read(ROOT/'typing/evidence/verification.json')
    assert len(contracts['results'])==7 and all(contracts['results'].values())
    assert contracts['source_files']==len(source)==81
    for file in ['focused.xml','suite.xml','native.xml']:
        result=counts(file);assert result['tests'] and result['failures']==result['errors']==0,(file,result)
    assert counts('native.xml')['passed']==6 and counts('native.xml')['skipped']==0
    raw=(HERE/'raw-source.txt').read_text(encoding='utf-8-sig')
    summary=re.search(r'Found \d+ errors in \d+ files \(checked \d+ source files\)',raw).group(0)
    assert 'library_search.py:' not in raw,'new private search module has a raw typing diagnostic'
    dist=ROOT/'.tmp/private-library-search/dist'
    with zipfile.ZipFile(next(dist.glob('*.whl'))) as wheel,tarfile.open(next(dist.glob('*.tar.gz'))) as sdist:
        prefix=sdist.getnames()[0].split('/')[0]
        for path,sha in source.items():
            assert hashlib.sha256(wheel.read(path.removeprefix('src/'))).hexdigest()==sha,path
            assert hashlib.sha256(sdist.extractfile(prefix+'/'+path).read()).hexdigest()==sha,path
        for path in previous().CURRENT:
            assert sdist.extractfile(prefix+'/'+path).read()==(ROOT/path).read_bytes(),path
    docs=documentation()
    result={'result':'PASS','application_files':len(source),'changed_application_files':changed,
            'focused':counts('focused.xml'),'suite':counts('suite.xml'),'native':counts('native.xml'),
            'contracts':contracts['results'],'packages_match':True,'strict_source_typing':'FAIL: '+summary,
            'documentation':{'commands':len(docs['commands']),'examples':len(docs['parsed_examples']),'links':docs['links']},
            'limits':['Existing Windows dependencies; no clean-install, different OS or user VS Code host qualification.',
                      'Synthetic media and existing synthetic/tiny-random CPU engine tests; no pretrained-model efficacy or independent human/accessibility acceptance.',
                      'Native private search test uses the real authenticated local server for original-title lookup, paging and selection; delayed/offline and composition events are explicitly injected.',
                      'Initial focused failures came from undeclared fixture categories and a changed-image fixture with invalid metadata. Native testing exposed hidden invalid-field focus, which was fixed; a harness selector error was also retained.',
                      'Strict source typing remains failing; external declarations pass separately. Static UI findings have scoped dispositions, not a global pass.']}
    (HERE/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def acceptance(pacer_source):
    sys.path.insert(0,str(pacer_source))
    from pacer_mcp.service import Service
    current=verify();assert read(ROOT/'typing/evidence/pacer-inventory.json')['result']=='PASS'
    csv.field_size_limit(100000000)
    with (ROOT/'organism.PACER.csv').open(encoding='utf-8-sig',newline='') as f:requirements=list(csv.DictReader(f))
    with (ROOT/'overlord.PACER.csv').open(encoding='utf-8-sig',newline='') as f:assets=list(csv.DictReader(f))
    decisions=read(ROOT/'evidence/pacer-resumption/decisions.json')
    decisions.update({
        'OGM-023':{'tests':['test_browser_scan_jobs']},'OGM-024':{'tests':['test_category_sort_interfaces']},
        'OGM-025':{'tests':['test_recovery_guidance']},'OGM-026':{'tests':['test_workflows','test_sort_recovery','test_float_sort','test_sanitize']},
        'OGM-027':{'tests':['test_recipes','test_recipe_interfaces','test_sort_preview_binding','test_model_configuration_identity','test_publication_review_snapshots']}, 'OGM-028':{'tests':['test_workspace_health','test_workspace_lease','test_sort_recovery']}, 'OGM-029':{'tests':['test_library_search']}})
    cases=[case for name in ['suite.xml','native.xml'] for case in ET.parse(HERE/name).getroot().iter('testcase')]
    reviews=read(HERE/'requirement-review.json')
    service=Service(ROOT);next_id=max(int(r['ID'].split('-')[1]) for r in assets)+1;operations=[];summaries=[]
    for row in sorted(requirements,key=lambda r:r['ID']):
        observed=service.evaluate(row['ID'])
        if observed['freshness']=='CURRENT':continue
        previous_path=next((ROOT/'evidence'/stage/(row['ID']+suffix) for stage in ('workspace-health','publishing-recipes','documentation-contracts','recovery-guidance','guided-category-editing','pacer-resumption') for suffix in ('-final.json','.json') if (ROOT/'evidence'/stage/(row['ID']+suffix)).exists()),None)
        old=read(previous_path) if previous_path else {}
        changed=sorted(p for p in observed['sources'] if old.get('sources',{}).get(p)!=observed['sources'][p])
        modules=decisions.get(row['ID'],{}).get('tests',[]);coverage={}
        for module in modules:
            selected=[c for c in cases if c.get('classname')=='tests.'+module]
            assert selected and all(c.find('failure') is None and c.find('error') is None for c in selected),module
            coverage[module]={'passed':sum(c.find('skipped') is None for c in selected),'skipped':sum(c.find('skipped') is not None for c in selected)}
        review=reviews[row['ID']]
        report={'requirement':row['ID'],'meaning':observed['meaning'],'sources':observed['sources'],'result':'PASS',
                'command':['.venv/Scripts/python.exe evidence/private-library-search/verify.py',
                           '.venv/Scripts/python.exe -m pytest -q -k "not browser_native and not native_browser and not browser_review_in_real_chromium" --junitxml=evidence/private-library-search/suite.xml',
                           '.venv/Scripts/python.exe -m pytest -q -k "browser_native or native_browser or browser_review_in_real_chromium" --junitxml=evidence/private-library-search/native.xml',
                           'uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py'],
                'review':review,'changed_sources_since_previous_acceptance':changed,'executed_modules':coverage,
                'previous_review_artifact':previous_path.relative_to(ROOT).as_posix() if previous_path else None,
                'previous_review_sha256':digest(previous_path) if previous_path else None,'scope_limits':current['limits']}
        path='evidence/private-library-search/'+row['ID']+'.json'
        assert not (ROOT/path).exists(),'never overwrite acceptance'
        (ROOT/path).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        artifact=f'OVR-{next_id:03d}';next_id+=1
        operations += [{'op':'add','register':'overlord','row':{'ID':artifact,'AssetType':'FILE','Path':path,'Purpose':'PAC-042 scoped private search integration acceptance for '+row['ID'],'PACRefs':'PAC-042','Tags':'#acceptance #private-library-search'}},
                       {'op':'verify','id':row['ID'],'artifact':artifact,'evidence':'PAC-042 source-bound storage inspection integration review and executed regressions: '+path}]
        summaries.append({'id':row['ID'],'changed_sources':changed,'review':review})
    (HERE/'acceptance-operations.json').write_text(json.dumps(operations,indent=2)+'\n',encoding='utf-8')
    (HERE/'acceptance-review.json').write_text(json.dumps(summaries,indent=2)+'\n',encoding='utf-8')
    return {'requirements':len(summaries),'operations':len(operations)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',action='store_true');parser.add_argument('--documentation',action='store_true');parser.add_argument('--pacer-source',type=Path);args=parser.parse_args()
    if args.manifest:(ROOT/'RELEASE-MANIFEST.json').write_text(json.dumps(manifest(),indent=2)+'\n',encoding='utf-8')
    elif args.documentation:print(json.dumps(documentation(),indent=2))
    elif args.pacer_source:print(json.dumps(acceptance(args.pacer_source),indent=2))
    else:print(json.dumps(verify(),indent=2))
