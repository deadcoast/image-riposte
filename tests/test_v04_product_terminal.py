"""Actual terminal controller through sanitation, publishing and exact-byte packaging.

Only model adapters are explicit synthetic numerical fixtures. The production
controllers, worker, optimizer, storage and codecs run unchanged.
"""
import hashlib,io,json,time
from pathlib import Path
from zipfile import ZipFile
import pytest
from riposte.terminal.controller import Controller
from riposte.terminal.keyboard import Key
from riposte.terminal.output import Presentation
from riposte.terminal.service import Request,execute,image_bytes
from riposte.terminal.render import render
from riposte.terminal.state import Page
from riposte.store import catalog,state_relative
from riposte.errors import RiposteError


def settle(c):
    op=c.state.operation
    assert op is not None
    assert op.done.wait(10),'Foreground operation exceeded the fixture time bound'
    c.pump()
    return c.state.page


def type_confirm(c,word):
    c.key(Key('paste',word));c.key(Key('enter'))

@pytest.fixture
def models(monkeypatch):
    pytest.importorskip('torch')
    import riposte.models as m
    class SyntheticOracle:
        device='cpu';identity={'kind':'SYNTHETIC_V04_TEST_ORACLE','weights_sha256':'a'*64}
        def __call__(self,x):return x.square()+.15*x
    calls=[]
    monkeypatch.setattr(m,'LocalEncoder',lambda *args: calls.append(args) or SyntheticOracle())
    return calls


def cleaned_controller(root,make_image):
    raw=make_image(root/'nested'/'input.png',size=(96,80));before=raw.read_bytes()
    c=Controller(root,Presentation());c.action('organize');c.state.page.values['date_mode']='modified'
    c.key(Key('char','p'));p=settle(c)
    assert p.request.name=='organize' and raw.read_bytes()==before
    c.key(Key('char','a'));assert c.state.page.name=='confirm'
    type_confirm(c,'WRONG');assert c.state.operation is None and raw.exists()
    c.state.page.values['confirmation']='';type_confirm(c,'REPLACE');settle(c)
    assert not raw.exists() and len(catalog(root))==1
    return c


def publishing_controller(root,make_image,models):
    c=cleaned_controller(root,make_image);c.library();c.key(Key('char',' '));c.key(Key('char','p'))
    p=c.state.page;assert p.action=='publish'
    p.values.update(vae1='SYNTHETIC_LOCAL_MODEL',steps=2,restarts=1,edges=(64,))
    c.key(Key('char','p'));p=settle(c);assert p.result['outputs']==1 and not (root/'.riposte/publishing').exists()
    c.key(Key('char','r'));p=settle(c)
    assert p.name=='batch' and p.result['counts']['READY_FOR_REVIEW']==1,p
    return c


def test_interactive_clean_preview_confirmation_and_audit(root,make_image):
    c=cleaned_controller(root,make_image)
    c.action('organize');c.key(Key('char','v'));p=settle(c)
    assert p.result['checkpoint']=='COMPLETE'
    c.shutdown();assert not (root/'.riposte/operation.lock').exists()


def test_main_menu_to_real_candidate_review_and_pack(root,make_image,models):
    c=publishing_controller(root,make_image,models);b=c.state.page.batch_id
    item=c.state.page.rows[0]['id'];expected=image_bytes(root,{'batch_id':b,'item_id':item})
    c.key(Key('enter'));assert c.state.page.name=='item' and c.state.page.preview
    for key in ['b','d','c','t']:
        c.key(Key('char',key));assert c.state.page.name=='item' and c.state.page.preview
    c.key(Key('char','a'));assert c.state.page.action=='review'
    c.state.page.values.update(visual_accepted=True,acknowledge_unverified=True)
    c.key(Key('char','r'));assert c.state.page.confirm_word=='ACCEPT'
    type_confirm(c,'ACCEPT');p=settle(c);assert p.result['counts']['ACCEPTED']==1
    c.key(Key('char','p'));p=settle(c)
    data=(root/p.result['relative']).read_bytes()
    with ZipFile(io.BytesIO(data)) as z:
        assert len(z.infolist())==1 and z.read(z.namelist()[0])==expected
        assert z.namelist()[0].startswith('2025/March/SML/')
    assert not (root/'.riposte/lab').exists()
    assert len(models)==1
    assert 'SYNTHETIC_LOCAL_MODEL' not in '\n'.join(f.read_text() for f in (root/'.riposte/publishing').rglob('*.json'))
    c.shutdown()


def test_review_cannot_skip_the_two_actual_acks(root,make_image,models):
    c=publishing_controller(root,make_image,models);b=c.state.page.batch_id
    c.key(Key('enter'));c.key(Key('char','a'));c.key(Key('char','r'));type_confirm(c,'ACCEPT')
    p=settle(c);assert p.code and 'ACKNOWLEDGEMENT' in p.code
    assert execute(Request('publications',root,{'batch_id':b}))['counts']['ACCEPTED']==0
    c.shutdown()


def test_viewer_explicit_handoff_does_not_approve(root,make_image,models,monkeypatch):
    import riposte.terminal.service as service
    c=publishing_controller(root,make_image,models);b=c.state.page.batch_id;i=c.state.page.rows[0]['id']
    calls=[]
    class Exit: returncode=0
    monkeypatch.setattr(service.subprocess,'run',lambda args,**kw:calls.append((args,kw)) or Exit())
    monkeypatch.setattr(service.os,'startfile',lambda p:calls.append((p,{})),raising=False)
    result=execute(Request('open-image',root,{'batch_id':b,'item_id':i}))
    assert result['viewer']=='HANDOFF_REQUESTED' and len(calls)==1
    assert execute(Request('publications',root,{'batch_id':b}))['counts']['ACCEPTED']==0
    assert (root/result['relative']).read_bytes()==image_bytes(root,{'batch_id':b,'item_id':i})
    if isinstance(calls[0][0],list):assert calls[0][1].get('shell',False) is False
    c.shutdown()


def test_failed_publish_is_an_error_not_noise(root,make_image):
    c=cleaned_controller(root,make_image);c.library();c.key(Key('char',' '));c.action('publish')
    c.key(Key('char','r'));p=settle(c)
    assert p.code and not (root/'.riposte/publishing').exists()
    c.shutdown()


def test_ascii_inspection_uses_bound_pixel_hash(root,make_image,models):
    c=publishing_controller(root,make_image,models);b=c.state.page.batch_id;i=c.state.page.rows[0]['id']
    raw=image_bytes(root,{'batch_id':b,'item_id':i})
    target=root/state_relative(root,f'publishing/{b}/items/{i}/candidate.png');target.write_bytes(raw+b'PRIVATE')
    c.key(Key('enter'));assert c.state.page.name=='result' and c.state.page.code
    c.shutdown()


def test_model_free_fresh_workspace_choosing_exiting_is_read_only(root, monkeypatch):
    monkeypatch.setattr('riposte.terminal.paths.application_directory', lambda: root.parent / 'application')
    c=Controller(None,Presentation());assert c.state.editor is None
    c.key(Key('char','2')); assert c.state.page.name=='picker'
    c.state.page.result.enter(root);c.state.page.rows=c.state.page.result.rows();c.key(Key('enter'))
    assert c.state.root==root and not list(root.iterdir())
    c.key(Key('char','q'));c.shutdown();assert not list(root.iterdir())
