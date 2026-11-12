"""Artist limits through actual optimization, saved review and primary adapters.

Synthetic differentiable encoders exercise mechanics, never protection efficacy.
"""
import base64
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pytest
from PIL import Image, PngImagePlugin
from fastapi.testclient import TestClient
from typer.testing import CliRunner
from riposte import publication as p
from riposte.cli import app
from riposte.errors import RiposteError
from riposte.organizer import organize, plan
from riposte.policy import Policy
from riposte.quality import QualityLimits, spatial_budget, quality_report
from riposte.release_guard import ReleaseConfig, protect_release
from riposte.sanitize import png_audit
from riposte.server import create_app
from riposte.spatial import ArtistMask, checked_masks, read_map
from riposte.store import catalog, state_relative
from riposte.terminal.service import Request, execute, image_bytes


def png(array, mode='L', metadata=False):
    image = Image.fromarray(np.asarray(array, dtype=np.uint8)) if mode == 'L' else Image.new(mode, (8, 8))
    stream = io.BytesIO(); info = PngImagePlugin.PngInfo()
    if metadata: info.add_text('Comment', 'PRIVATE_MASK_METADATA')
    image.save(stream, format='PNG', pnginfo=info)
    return stream.getvalue()


def mask_for_row(row, value=255):
    pixels = np.full((row['height'], row['width']), value, dtype=np.uint8)
    pixels[:, :row['width']//3] = 0
    return ArtistMask.from_png(png(pixels), row['sha256'])


@pytest.fixture
def artwork(root, make_image):
    make_image(root/'drawing.png', size=(96, 80), color=(90, 120, 150))
    policy = Policy(date_mode='modified')
    organize(root, policy, plan_id=plan(root, policy)['plan_id'])
    return catalog(root)[0]


class Encoder:
    device = 'cpu'
    identity = {'kind': 'SYNTHETIC_SPATIAL_TEST_ONLY'}
    def __call__(self, x): return x.square() + .15 * x


@pytest.fixture
def encoder(monkeypatch):
    pytest.importorskip('torch')
    from riposte import models
    monkeypatch.setattr(models, 'LocalEncoder', lambda *args: Encoder())


def configured(row):
    return p.PublishRecipe((64, 96), ReleaseConfig(steps=2, restarts=1), masks=(mask_for_row(row),))


@pytest.mark.parametrize('size', [(3, 2), (17, 13), (2, 1), (1, 1), (7, 5)])
def test_resampling_matches_independent_overlap_minimum(size):
    source = np.array([[255, 80, 255, 0], [150, 255, 1, 255], [0, 255, 255, 255]], dtype=np.uint8)
    mask = ArtistMask('a'*64, 4, 3, source.tobytes())
    raster = mask.raster(size)
    for y in range(size[1]):
        for x in range(size[0]):
            cells = [int(source[j,i]) for j in range(3) for i in range(4)
                     if i*size[0] < (x+1)*4 and (i+1)*size[0] > x*4
                     and j*size[1] < (y+1)*3 and (j+1)*size[1] > y*3]
            assert raster[y,x] == min(cells)


def test_thin_protected_line_survives_resize_and_never_increases_automatic_limits():
    pixels = np.full((64,64),255,dtype=np.uint8); pixels[:,31]=0
    mask = ArtistMask('a'*64,64,64,pixels.tobytes())
    assert np.all(mask.raster((16,16))[:,7] == 0)
    image = Image.new('RGB',(16,16),'white')
    assert not spatial_budget(image,QualityLimits(),mask).any()
    image = Image.new('RGB',(16,16),'gray')
    assert np.all(spatial_budget(image,QualityLimits(),mask) <= spatial_budget(image,QualityLimits()))


@pytest.mark.parametrize('gray,cap', [(0,0),(1,0),(63,0),(64,1),(127,1),(128,2),(254,3),(255,4)])
def test_integer_floor_caps(gray,cap):
    mask = ArtistMask('a'*64,1,1,bytes([gray]))
    assert np.all(spatial_budget(Image.new('RGB',(16,16),'gray'),QualityLimits(),mask) == cap)


@pytest.mark.parametrize('mode', ['RGB','RGBA','P','1','I;16'])
def test_mask_rejects_ambiguous_png_modes(mode):
    with pytest.raises(RiposteError,match='ARTIST_MASK_PNG_INVALID'):
        ArtistMask.from_png(png([],mode), 'a'*64)


def test_mask_identity_strips_metadata_binds_source_and_rejects_corruption():
    source=np.full((8,8),255,dtype=np.uint8)
    a=ArtistMask.from_png(png(source,metadata=True),'a'*64)
    b=ArtistMask.from_png(png(source),'a'*64)
    assert a == b and a.identity == b.identity
    assert 'PRIVATE_MASK' not in json.dumps(a.public())
    assert replace(a,source_sha256='b'*64).identity != a.identity
    assert ArtistMask.from_dict(a.public()) == a
    for field,value in [('pixels','!'),('width',True),('sha256','a'*64),('width',4097)]:
        with pytest.raises(RiposteError): ArtistMask.from_dict({**a.public(),field:value})
    with pytest.raises(RiposteError): checked_masks((a,a))
    with pytest.raises(RiposteError): a.validate_aspect((96,32))


def test_quality_rejects_change_in_zero_region_even_within_global_epsilon():
    clean=Image.new('RGB',(32,32),(90,120,150)); changed=np.array(clean)
    changed[0,0,0]+=1
    mask=ArtistMask('a'*64,32,32,bytes([0])*1024)
    assert quality_report(clean,Image.fromarray(changed))['status']=='PASS'
    report=quality_report(clean,Image.fromarray(changed),artist_mask=mask)
    assert report['status']=='BLOCKED' and report['protected_pixels_changed']==1
    assert report['budget_violating_pixels']==1


def test_actual_optimizer_enforces_mask_and_is_deterministic(encoder):
    clean=Image.new('RGB',(32,32),(90,120,150)); pixels=np.full((32,32),255,dtype=np.uint8)
    pixels[:,:10]=0; pixels[:,10:20]=128
    mask=ArtistMask('a'*64,32,32,pixels.tobytes()); config=ReleaseConfig(steps=3,restarts=1,step_255=8)
    a,ar=protect_release(clean,[Encoder()],config,artist_mask=mask)
    b,br=protect_release(clean,[Encoder()],config,artist_mask=mask)
    delta=np.abs(np.asarray(a,dtype=int)-np.asarray(clean,dtype=int))
    assert not delta[:,:10].any() and delta[:,10:20].max()<=2 and delta.max()<=4
    assert delta.any() and a.tobytes()==b.tobytes() and ar==br
    assert ar['quality']['spatial_budget']['artist_mask_sha256']==mask.identity
    with pytest.raises(RiposteError,match='NO_EDITABLE_PIXEL_BUDGET'):
        protect_release(clean,[Encoder()],config,artist_mask=replace(mask,pixels=bytes(1024)))


def test_plan_readonly_previews_exact_caps_for_each_final_size(root,artwork):
    before={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in root.rglob('*') if f.is_file()}
    recipe=configured(artwork); result=p.publication_plan(root,[artwork['id']],recipe)
    assert len(result['budget_previews'])==2
    for item in result['budget_previews']:
        cap=Image.open(io.BytesIO(base64.b64decode(item['caps_png'])))
        assert cap.size==(item['width'],item['height'])
        assert not np.asarray(cap)[:,:item['width']//3].any()
        assert 'PRIVATE_MASK_METADATA' not in json.dumps(item)
        assert png_audit(image_bytes(root,{'budget_preview':item}))['date']==artwork['day']
    assert before=={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in root.rglob('*') if f.is_file()}
    with pytest.raises(RiposteError,match='SELECTION_MISMATCH'):
        p.publication_plan(root,[artwork['id']],replace(recipe,masks=(replace(recipe.masks[0],source_sha256='f'*64),)))


def test_real_batch_resume_review_and_date_only_pack(root,artwork,encoder):
    recipe=configured(artwork); master=(root/artwork['relative']).read_bytes()
    def stop(event):
        if event.get('item')==2: raise RiposteError('JOB_CANCELLED')
    with pytest.raises(RiposteError,match='JOB_CANCELLED'):
        p.start_publication(root,[artwork['id']],[Path('SYNTHETIC')],recipe,progress=stop)
    batch=p.publication_status(root,p.publications(root)[0]['id']); first=batch['items'][0]
    original=p.publication_pixels(root,batch['id'],first['id'])
    batch=p.resume_publication(root,batch['id'],[Path('SYNTHETIC')])
    assert batch['counts']['READY_FOR_REVIEW']==2
    assert p.publication_pixels(root,batch['id'],first['id'])==original
    assert all(item['quality']['spatial_budget']['artist_mask_sha256']==recipe.masks[0].identity for item in batch['items'])
    p.review_publication(root,batch['id'],[x['id'] for x in batch['items']],'ACCEPTED',True,True)
    with ZipFile(io.BytesIO(p.publication_zip(root,batch['id']))) as archive:
        assert len(archive.namelist())==2 and all(name.endswith('.png') for name in archive.namelist())
        for name in archive.namelist(): assert png_audit(archive.read(name))['metadata']=='DATE_ONLY'
    assert (root/artwork['relative']).read_bytes()==master


@pytest.mark.parametrize('change', ['pixels','task','remove','coherent'])
def test_changed_mask_identity_cannot_reuse_approval(root,artwork,encoder,change):
    recipe=replace(configured(artwork),edges=(64,))
    batch=p.start_publication(root,[artwork['id']],[Path('SYNTHETIC')],recipe)
    item=batch['items'][0]; assert item['status']=='READY_FOR_REVIEW'
    p.review_publication(root,batch['id'],[item['id']],'ACCEPTED',True,True)
    path=root/state_relative(root,f"publishing/{batch['id']}/request.json")
    data=json.loads(path.read_text(encoding='utf-8'))
    if change=='pixels': data['recipe']['masks'][0]['pixels']=base64.b64encode(bytes(96*80)).decode()
    elif change=='task': data['tasks'][0]['artist_mask_sha256']='a'*64
    elif change=='remove': data['recipe'].pop('masks');data['tasks'][0].pop('artist_mask_sha256')
    else:
        new=replace(recipe.masks[0],pixels=bytes([255])*(96*80))
        data['recipe']['masks']=[new.public()];data['tasks'][0]['artist_mask_sha256']=new.identity
    path.write_text(json.dumps(data),encoding='utf-8')
    with pytest.raises(RiposteError): p.publication_zip(root,batch['id'])
    with pytest.raises(RiposteError): p.resume_publication(root,batch['id'],[Path('SYNTHETIC')])


def test_cli_terminal_and_raw_intake(root,artwork,tmp_path,make_image):
    mask=mask_for_row(artwork); path=tmp_path/'mask.png';path.write_bytes(png(np.frombuffer(mask.pixels,dtype=np.uint8).reshape(80,96)))
    values={'image_ids':[artwork['id']],'budget_mask':path,'edges':[64]}
    result=execute(Request('plan',root,values)); assert result['budget_previews']
    response=CliRunner().invoke(app,['publish',str(root),'--image',artwork['id'],'--budget-mask',str(path),'--plan'])
    assert response.exit_code==0,response.output
    assert json.loads(response.output)['budget_previews']
    raw=make_image(tmp_path/'original.png',size=(96,80))
    result=execute(Request('riposte-plan',root,{'input_paths':[raw],'budget_mask':path,'edges':[64]}))
    assert result['source_mode']=='snapshot' and result['budget_previews']
    mapping=tmp_path/'map.json';mapping.write_text(json.dumps({'schema':1,'masks':[mask.public()]}),encoding='utf-8')
    assert read_map(mapping)==(mask,)
    assert execute(Request('plan',root,{'image_ids':[artwork['id']],'budget_map':mapping}))['budget_previews']


def test_authenticated_api_validates_mask_and_readonly_preview(root,artwork):
    client=TestClient(create_app(root,'spatial-token')); headers={'X-Riposte-Token':'spatial-token'}
    request={'image_id':artwork['id'],'png':base64.b64encode(png(np.full((80,96),128,dtype=np.uint8),metadata=True)).decode()}
    assert client.post('/api/artist-mask',json=request).status_code==401
    response=client.post('/api/artist-mask',json=request,headers=headers)
    assert response.status_code==200,response.text
    assert 'no-store' in response.headers['cache-control']
    mask=response.json()['mask']; assert 'PRIVATE' not in json.dumps(mask)
    preview=client.post('/api/publish',headers=headers,json={'image_ids':[artwork['id']],'masks':[mask],'edges':[64],'plan_only':True})
    assert preview.status_code==200,preview.text
    assert preview.json()['budget_previews'][0]['maximum_channel_change_255']==2
    assert not (root/'.riposte/publishing').exists()
    assert client.post('/api/artist-mask',headers=headers,json={**request,'png':'!!'}).status_code==400


def test_mask_invalid_before_combined_sort_mutation(root,make_image,tmp_path):
    source=make_image(root/'drawing.png',size=(96,80)); before=source.read_bytes()
    mask=tmp_path/'mask.png';mask.write_bytes(png(np.full((8,8),255,dtype=np.uint8)))
    # Square versus 96x80 does not pass the one-cell aspect tolerance at this scale.
    bad=tmp_path/'bad.json';bad.write_text(json.dumps({'schema':1,'masks':[ArtistMask('f'*64,8,8,bytes([255])*64).public()]}),encoding='utf-8')
    with pytest.raises(RiposteError,match='SELECTION_MISMATCH'):
        execute(Request('sort-riposte-plan',root,{'all_images':True,'budget_map':bad}))
    assert source.read_bytes()==before and not (root/'.riposte').exists()


def test_large_mask_api_and_streamed_limits(root,artwork):
    client=TestClient(create_app(root,'spatial-token'));client.headers['X-Riposte-Token']='spatial-token'
    pixels=np.random.default_rng(17).integers(0,256,(320,384),dtype=np.uint8)
    request={'image_id':artwork['id'],'png':base64.b64encode(png(pixels)).decode()}
    assert len(json.dumps(request))>32768
    response=client.post('/api/artist-mask',json=request);assert response.status_code==200,response.text
    body={'image_ids':[artwork['id']],'masks':[response.json()['mask']],'plan_only':True,'edges':[64]}
    response=client.post('/api/publish',json=body);assert response.status_code==200,response.text
    for endpoint,limit in [('/api/artist-mask',2_800_000),('/api/publish',6_000_000),('/api/recipes',32768)]:
        response=client.post(endpoint,content=(b' '*(limit//2+1) for _ in range(2)),headers={'content-type':'application/json'})
        assert response.status_code==413
    assert not (root/'.riposte/publishing').exists()


def test_large_batch_previews_are_paged_and_start_skips_preview_work(root,artwork,make_image,monkeypatch):
    make_image(root/'second.png',size=(96,80),color=(120,100,80))
    policy=Policy(date_mode='modified');organize(root,policy,plan_id=plan(root,policy)['plan_id'])
    rows=catalog(root);recipe=p.PublishRecipe((64,80,96),masks=tuple(mask_for_row(row) for row in rows))
    calls=[];original=p._budget_previews
    def render(*args):
        result=original(*args);calls.extend(result);return result
    monkeypatch.setattr(p,'_budget_previews',render)
    first=p.publication_plan(root,[row['id'] for row in rows],recipe)
    assert len(calls)==3 and first['budget_preview_total']==6 and first['budget_preview_offset']==0
    calls.clear();second=p.publication_plan(root,[row['id'] for row in rows],recipe,budget_offset=3)
    assert len(calls)==3 and second['budget_preview_offset']==3
    assert {r['image_id'] for r in first['budget_previews']}.isdisjoint({r['image_id'] for r in second['budget_previews']})
    with pytest.raises(RiposteError,match='ARTIST_MASK_PREVIEW_REQUIRED'):
        p.publication_plan(root,[row['id'] for row in rows],recipe,budget_offset=6)
    calls.clear()
    with pytest.raises(RiposteError,match='NO_MODEL_NO_PROTECTION'):
        p.start_publication(root,[row['id'] for row in rows],[],recipe)
    assert not calls and not (root/'.riposte/publishing').exists()


def test_saved_mask_file_change_requires_new_terminal_preview(root,artwork,tmp_path):
    path=tmp_path/'mask.png';path.write_bytes(png(np.full((80,96),255,dtype=np.uint8)))
    values={'image_ids':[artwork['id']],'budget_mask':path,'edges':[64]}
    preview=execute(Request('plan',root,values));values['budget_revision']=preview['budget_revision']
    path.write_bytes(png(np.full((80,96),128,dtype=np.uint8)))
    with pytest.raises(RiposteError,match='ARTIST_MASK_PREVIEW_CHANGED'):
        execute(Request('publish',root,values))
    assert not (root/'.riposte/publishing').exists()


def test_combined_mask_bound_before_source_replacement(root,make_image,tmp_path,monkeypatch):
    source=make_image(root/'drawing.png',size=(96,80));before=source.read_bytes()
    path=tmp_path/'mask.png';path.write_bytes(png(np.full((80,96),128,dtype=np.uint8)))
    values={'all_images':True,'budget_mask':path,'edges':[64]}
    preview=execute(Request('sort-riposte-plan',root,values))
    assert preview['recipe']['masks']
    path.write_bytes(png(np.full((80,96),255,dtype=np.uint8)))
    values['plan_id']=preview['plan_id']
    with pytest.raises(RiposteError,match='SORT_PREVIEW_CHANGED'):
        execute(Request('sort-riposte',root,values))
    assert source.read_bytes()==before and not (root/'.riposte').exists()


def test_terminal_mask_preview_control_uses_existing_viewer(root,artwork,tmp_path,monkeypatch):
    from riposte.terminal.controller import Controller
    from riposte.terminal.keyboard import Key
    from riposte.terminal.state import Presentation, Page
    from riposte.terminal.render import render
    path=tmp_path/'mask.png';path.write_bytes(png(np.full((80,96),128,dtype=np.uint8)))
    request=Request('plan',root,{'image_ids':[artwork['id']],'budget_mask':path,'edges':[64]})
    result=execute(request);ctl=Controller(root,Presentation())
    ctl.show(Page('result','Publishing plan',request=request,result=result));ctl.state.width=72;ctl.state.height=24
    assert 'Mask preview' in render(ctl.state,72,24).plain()
    opened=[];monkeypatch.setattr(ctl,'run',opened.append)
    ctl.key(Key('char','m'))
    assert opened[0].name=='open-image' and opened[0].values['budget_preview']==result['budget_previews'][0]
    ctl.shutdown()


def test_spatial_browser_native(root,make_image):
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
    
    for n in range(2):make_image(root/f'art-{n}.png',size=(96,80),color=(30+n*10,90,150))
    policy=Policy(date_mode='modified');organize(root,policy,plan_id=plan(root,policy)['plan_id'])
    before={str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen()
    server=uvicorn.Server(uvicorn.Config(create_app(root,'spatial-native'),log_level='error'))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True);thread.start()
    try:
        for _ in range(100):
            if server.started:break
            time.sleep(.02)
        assert server.started
        args=[node,str(Path(__file__).with_name('spatial_browser.cjs')),browser]
        if os.environ.get('RIPOSTE_SPATIAL_SCREENSHOTS'):args.append(os.environ['RIPOSTE_SPATIAL_SCREENSHOTS'])
        run=subprocess.run(args,env={**os.environ,'RIPOSTE_MASK_PNG':base64.b64encode(png(np.tile(np.array([0]*32+[255]*64,dtype=np.uint8),(80,1)))).decode(),'RIPOSTE_SORT_LIVE':f'http://127.0.0.1:{listener.getsockname()[1]}/#token=spatial-native'},
                           capture_output=True,text=True,encoding='utf-8',timeout=90)
        assert run.returncode==0,run.stdout+run.stderr
        assert run.stdout.strip()=='PASS spatial_browser'
        assert {str(f):f.read_bytes() for f in root.rglob('*') if f.is_file()}==before
        assert not (root/'.riposte/publishing').exists()
    finally:server.should_exit=True;thread.join(10);listener.close()
