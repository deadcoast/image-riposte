import numpy as np
import pytest
from PIL import Image
from riposte.policy import Policy
from riposte.organizer import organize
from riposte.store import catalog
from riposte.errors import RiposteError
from riposte.metrics import fidelity,transform,transport_report,TRANSFORMS
from riposte.lab import compare_external,export_candidate,create_candidate

@pytest.mark.parametrize('name',TRANSFORMS)
def test_identical_transport_is_zero(name):
    im=Image.new('RGB',(64,48),(44,91,148));result=transport_report(im,im)
    row=next(r for r in result['rows'] if r['transform']==name);assert row['rmse_255']==0
    assert result['ai_protection']=='UNVERIFIED'
def test_difference_budget():
    a=Image.new('RGB',(32,32),(44,55,66));b=Image.new('RGB',(32,32),(45,56,67));r=fidelity(a,b)
    assert r['max_channel_delta_255']==1;assert r['rmse_255']==1
def test_compare_and_export(root,tmp_path,make_image):
    make_image(root/'a.png');organize(root,Policy(date_mode='modified'));row=catalog(root)[0]
    external=make_image(tmp_path/'external.png',color=(31,91,151));report=compare_external(root,row['id'],external)
    assert report['ai_protection']=='UNVERIFIED';assert report['evidence_level']=='PIXEL_TRANSPORT_ONLY';assert len(report['transport']['rows'])==8
    with pytest.raises(RiposteError,match='ACKNOWLEDGE'):export_candidate(root,report['id'])
    exported=export_candidate(root,report['id'],True);assert (root/exported['relative']).exists();assert external.exists()
    assert export_candidate(root,report['id'],True)==exported

def test_external_size_mismatch(root,tmp_path,make_image):
    make_image(root/'a.png');organize(root,Policy(date_mode='modified'));row=catalog(root)[0]
    external=make_image(tmp_path/'external.png',size=(22,22))
    with pytest.raises(RiposteError,match='SIZE_MISMATCH'):compare_external(root,row['id'],external)
def test_no_backend_no_random_fallback(root,make_image):
    make_image(root/'a.png');organize(root,Policy(date_mode='modified'));row=catalog(root)[0]
    with pytest.raises(RiposteError,match='NO_MODEL'):create_candidate(root,row['id'],[])
def test_checkpoint_required(root,tmp_path,make_image):
    make_image(root/'a.png');organize(root,Policy(date_mode='modified'));row=catalog(root)[0]
    (root/'secret.xmp').write_text('PRIVATE_FIXTURE_PAYLOAD');external=make_image(tmp_path/'candidate.png')
    with pytest.raises(RiposteError,match='CHECKPOINT'):compare_external(root,row['id'],external)
def test_candidate_tamper_rejected(root,tmp_path,make_image):
    make_image(root/'a.png');organize(root,Policy(date_mode='modified'));row=catalog(root)[0]
    external=make_image(tmp_path/'candidate.png');report=compare_external(root,row['id'],external)
    from riposte.sanitize import encode_clean
    (root/f".riposte/lab/{report['id']}/candidate.png").write_bytes(encode_clean(Image.new('RGB',(64,48),'red'),report['date']))
    with pytest.raises(RiposteError,match='CANDIDATE_CHANGED'):export_candidate(root,report['id'],True)
