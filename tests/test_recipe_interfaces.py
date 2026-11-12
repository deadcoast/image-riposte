"""Real command/HTTP/controller integration; no pretrained-model efficacy claim."""
import json
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner
from riposte.cli import app
from riposte.errors import RiposteError
from riposte.recipes import defaults, inspect_recipes, save_recipe
from riposte.server import create_app
from riposte.terminal.actions import request_argv
from riposte.terminal.controller import Controller
from riposte.terminal.keyboard import Key
from riposte.terminal.output import Presentation
from riposte.terminal.render import render
from riposte.terminal.service import Request, execute


def saved(root, **edits):
    return save_recipe(root,'Print',{**defaults(), 'edges':[768,1536], 'seed':91, 'preserve_white':False, **edits},expected_revision=inspect_recipes(root)['revision'])


def cli(*args):
    result=CliRunner().invoke(app,['--json',*map(str,args)])
    assert result.exit_code==0,result.output
    return json.loads(result.stdout)


def test_cli_preview_save_and_explicit_overrides(root,make_image):
    image=make_image(root/'drawing.png');before=image.read_bytes()
    draft=cli('recipes',root,'Print','--preview','--edge','768','--seed','91','--no-preserve-white')
    assert not (root/'.riposte').exists()
    result=cli('recipes',root,'Print','--save','--edge','768','--seed','91','--no-preserve-white','--expected-revision',draft['revision'])
    assert result['settings']['seed']==91
    assert cli('recipes',root)['recipes'][0]['name']=='Print'
    for command in ['publish','protect','riposte']:
        plan=cli(command,root,'--input',image,'--recipe','Print','--plan')
        assert plan['recipe']['edges']==[768]
        assert plan['recipe']['guard']['seed']==91 and plan['recipe']['quality']['preserve_white'] is False
        edited=cli(command,root,'--input',image,'--recipe','Print','--seed','7','--preserve-white','--plan')
        assert edited['recipe']['guard']['seed']==7 and edited['recipe']['quality']['preserve_white'] is True
    assert image.read_bytes()==before
    refused=CliRunner().invoke(app,['--json','riposte',str(root),'--input',str(image),'--recipe','Print'])
    assert refused.exit_code!=0 # Saved settings do not provide a local model or start fallback protection.


def test_api_auth_preview_save_and_catalog_recipe_resolution(root,make_image):
    make_image(root/'drawing.png')
    from riposte.organizer import organize,plan
    from riposte.policy import Policy
    from riposte.store import catalog
    policy=Policy(date_mode='modified');organize(root,policy,plan_id=plan(root,policy)['plan_id'])
    image=catalog(root)[0]['id']
    with TestClient(create_app(root,'recipes-test')) as client:
        assert client.get('/api/recipes').status_code==401
        client.headers['X-Riposte-Token']='recipes-test'
        draft=client.post('/api/recipes',json={'name':'Print','settings':{'seed':91,'edges':[768]}}).json()
        result=client.post('/api/recipes',json={'name':'Print','settings':draft['settings'],'save':True,'expected_revision':draft['revision']})
        assert result.status_code==200,result.text
        stored=result.json()
        assert client.get('/api/state').json()['jobs']==[]
        assert client.post('/api/recipes',json={'name':'Print','root':'private'}).status_code==422
        assert client.post('/api/recipes',json={'name':'Print','settings':{'visual_accepted':True}}).status_code==400
        assert client.post('/api/publish',json={'image_ids':[],'recipe_name':'Print','plan_only':True}).status_code==422
        preview=client.post('/api/publish',json={'image_ids':[image],'recipe_name':'Print','plan_only':True})
        assert preview.status_code==200,preview.text
        assert preview.json()['recipe']['guard']['seed']==91
        preview=client.post('/api/publish',json={'image_ids':[image],'recipe_name':'Print','seed':7,'plan_only':True})
        assert preview.json()['recipe']['guard']['seed']==7
        saved(root,seed=92)
        refused=client.post('/api/publish',json={'image_ids':[image],'recipe_name':'Print','recipe_revision':stored['recipe_revision'],'plan_only':True})
        assert refused.status_code==400 and refused.json()['code']=='RECIPE_CHANGED'
        stale=client.post('/api/recipes',json={'name':'Print','settings':draft['settings'],'save':True,'expected_revision':draft['revision']})
        assert stale.json()['code']=='RECIPE_LIBRARY_CHANGED'


@pytest.mark.parametrize('pinned',[False,True])
def test_changed_recipe_blocks_combined_apply_before_models_or_sort(root,make_image,monkeypatch,pinned):
    source=make_image(root/'drawing.png');before=source.read_bytes();stored=saved(root)
    values={'all_images':True,'date_mode':'modified','recipe_name':'Print','vae_dirs':['LOCAL']}
    if pinned:values['recipe_revision']=stored['recipe_revision']
    preview=execute(Request('sort-riposte-plan',root,values))
    assert preview['recipe']['guard']['seed']==91
    saved(root,seed=92)
    monkeypatch.setattr('riposte.publication._models',lambda *a:pytest.fail('models loaded before stale preview refusal'))
    with pytest.raises(RiposteError,match='RECIPE_CHANGED' if pinned else 'SORT_PREVIEW_CHANGED'):
        execute(Request('sort-riposte',root,{**values,'plan_id':preview['plan_id']}))
    assert source.read_bytes()==before


def test_terminal_load_preview_save_preserves_nonrecipe_choices(root):
    saved(root)
    controller=Controller(root,Presentation(no_animation=True))
    try:
        controller.action('riposte',{'input1':str(root),'vae1':'PRIVATE_MODEL','device':'cpu'})
        controller.key(Key('char','l'))
        assert controller.state.page.name=='recipes'
        assert 'Load settings' in render(controller.state,72,24).plain()
        controller.key(Key('enter'))
        form=controller.state.page
        assert form.values['seed']==91 and form.values['edges']==[768,1536]
        assert form.values['vae1']=='PRIVATE_MODEL' and form.values['device']=='cpu'
        assert controller.state.operation is None
        form.values['seed']=88
        controller.key(Key('char','s'));controller.state.editor.value='Another'
        controller.key(Key('enter'))
        assert controller.state.page.result['status']=='DRAFT'
        assert 'Save recipe' in render(controller.state,72,24).plain()
        assert len(inspect_recipes(root)['recipes'])==1
        controller.key(Key('char','s'))
        assert controller.state.operation.done.wait(10);controller.pump()
        assert inspect_recipes(root,'Another')['settings']['seed']==88
        assert controller.state.operation is None
        assert not (root/'.riposte/publishing').exists()
    finally:controller.shutdown()


def test_terminal_stale_list_retains_form(root):
    saved(root);controller=Controller(root,Presentation(no_animation=True))
    try:
        controller.action('riposte');form=controller.state.page;controller.recipes()
        saved(root,seed=92)
        with pytest.raises(RiposteError,match='RECIPE_CHANGED'):controller.load_recipe()
        assert form.values['seed']==7
    finally:controller.shutdown()


def test_recipe_save_respects_job_and_shutdown_boundary(root):
    application=create_app(root,'recipes-test')
    with TestClient(application) as client:
        client.headers['X-Riposte-Token']='recipes-test'
        application.state.jobs.data['busy']={'state':'running'}
        body={'name':'Print','settings':defaults(),'save':True,'expected_revision':'missing'}
        assert client.post('/api/recipes',json=body).json()['code']=='JOB_ALREADY_RUNNING'
        application.state.jobs.data.clear();application.state.jobs.closed=True
        assert client.post('/api/recipes',json=body).json()['code']=='JOB_MANAGER_CLOSED'
        assert not list(root.iterdir())


def test_command_lens_roundtrips_recipe_save_and_explicit_white_override(root,make_image):
    settings={**defaults(),'preserve_white':False}
    request=Request('recipes-save',root,{'recipe_name':'Print','recipe_settings':settings,'expected_revision':'missing'})
    result=cli(*request_argv(request)[1:]);assert result['settings']==settings
    source=make_image(root/'drawing.png')
    request=Request('riposte-plan',root,{'input_paths':[source],'recipe_name':'Print','preserve_white':True,'recipe_overrides':['preserve_white']})
    assert cli(*request_argv(request)[1:])['recipe']['quality']['preserve_white'] is True


def test_recipe_browser_native(root,make_image):
    import os
    from pathlib import Path
    import shutil
    import socket
    import subprocess
    import threading
    import time
    import uvicorn
    from riposte.organizer import organize,plan
    from riposte.policy import Policy
    node=shutil.which('node')
    browser=next((p for p in [os.environ.get('RIPOSTE_TEST_BROWSER',''),shutil.which('chromium'),
        'C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'] if p and Path(p).is_file()),None)
    if not node or not browser:pytest.skip('Local Node and Chromium required')
    make_image(root/'drawing.png');policy=Policy(date_mode='modified')
    organize(root,policy,plan_id=plan(root,policy)['plan_id'])
    before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*.png')}
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen()
    server=uvicorn.Server(uvicorn.Config(create_app(root,'recipe-native'),log_level='error'))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True);thread.start()
    try:
        for _ in range(100):
            if server.started:break
            time.sleep(.02)
        assert server.started
        args=[node,str(Path(__file__).with_name('recipes_browser.cjs')),browser]
        if os.environ.get('RIPOSTE_RECIPE_SCREENSHOTS'):args.append(os.environ['RIPOSTE_RECIPE_SCREENSHOTS'])
        run=subprocess.run(args,env={**os.environ,'RIPOSTE_SORT_LIVE':f'http://127.0.0.1:{listener.getsockname()[1]}/#token=recipe-native'},
                           capture_output=True,text=True,encoding='utf-8',timeout=90)
        assert run.returncode==0,run.stdout+run.stderr
        assert run.stdout.strip()=='PASS recipes_browser'
        assert before=={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*.png')}
        assert not (root/'.riposte/publishing').exists()
    finally:server.should_exit=True;thread.join(10);listener.close()
