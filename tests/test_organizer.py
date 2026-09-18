import hashlib
import os
from pathlib import Path
import pytest
from riposte.errors import RiposteError
from riposte.policy import Policy
from riposte.organizer import plan,organize,audit_workspace
from riposte.store import catalog,safe_child,workspace_lock

POLICY=Policy(date_mode='modified')
def test_plan_has_no_writes(root,make_image):
    path=make_image(root/'mess'/'source.png');before=path.read_bytes();r=plan(root,POLICY)
    assert r['counts']['images_to_migrate']==1;assert path.read_bytes()==before;assert not (root/'.riposte').exists()
def test_full_migration_idempotence(root,make_image):
    make_image(root/'old'/'private_filename.png');make_image(root/'random.jpg',day='2024-01-01');make_image(root/'other'/'extless',fmt='PNG',day='2023-12-01')
    r=organize(root,POLICY);assert r['checkpoint']=='COMPLETE';assert r['counts']['migrated']==3
    expected={'2025/March/img/SML/SML01.png','2024/January/img/SML/SML01.png','EVERYTHING_ELSE/December/img/SML/SML01.png'}
    assert {x['relative'] for x in catalog(root)}==expected;assert not (root/'old').exists();assert not (root/'2024'/'July').exists();assert not (root/'2025'/'March'/'MED').exists()
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*.png')}
    again=organize(root,POLICY);assert again['counts']['already_clean']==3;assert again['checkpoint']=='COMPLETE'
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*.png')}
    assert audit_workspace(root)['checkpoint']=='COMPLETE'
def test_catalog_does_not_record_original_name(root,make_image):
    make_image(root/'PRIVATE_SOURCE_NAME.png');organize(root,POLICY)
    for p in (root/'.riposte').rglob('*'):
        # Undo is the explicitly private exception: original names and bytes are
        # necessary to restore a sort. Catalogs and generated images stay clean.
        if 'sort-history' in p.relative_to(root/'.riposte').parts:continue
        if p.is_file():assert b'PRIVATE_SOURCE_NAME' not in p.read_bytes();assert b'PRIVATE_FIXTURE_PAYLOAD' not in p.read_bytes()
def test_no_overwrite_and_existing_layout_translated(root,make_image):
    make_image(root/'2025'/'March'/'SML'/'SML01.png');make_image(root/'new.png',color=(22,24,88))
    assert organize(root,POLICY)['checkpoint']=='COMPLETE';rows=catalog(root);assert len(rows)==2;assert len({r['sha256'] for r in rows})==2
    make_image(root/'third.png',color=(7,9,18));organize(root,POLICY);assert len(catalog(root))==3
@pytest.mark.parametrize('suffix',['.xmp','.exif','.iptc','.aae'])
def test_sidecars_never_imported(root,make_image,suffix):
    make_image(root/'x.png');side=root/('x'+suffix);side.write_text('PRIVATE_FIXTURE_PAYLOAD')
    assert organize(root,POLICY)['checkpoint']=='INCOMPLETE';assert side.exists()
    r=organize(root,Policy(date_mode='modified',discard_sidecars=True));assert r['checkpoint']=='COMPLETE';assert not side.exists()
def test_unknown_data_not_deleted(root,make_image):
    make_image(root/'x.png');other=root/'notes.json';other.write_text('not image data')
    assert organize(root,POLICY)['checkpoint']=='INCOMPLETE';assert other.exists()
def test_corrupt_image_retained(root):
    path=root/'bad.png';path.write_bytes(b'not an image');r=organize(root,POLICY);assert r['checkpoint']=='INCOMPLETE';assert path.exists();assert not list(root.glob('2025'))
def test_source_kept_on_encode_failure(root,make_image,monkeypatch):
    path=make_image(root/'x.png')
    def fail(*a,**k):raise RiposteError('TEST_ENCODE_FAIL')
    monkeypatch.setattr('riposte.organizer.encode_clean',fail)
    assert organize(root,POLICY)['checkpoint']=='INCOMPLETE';assert path.exists();assert not catalog(root)
def test_source_change_prevents_deletion(root,make_image,monkeypatch):
    path=make_image(root/'x.png');monkeypatch.setattr('riposte.organizer.same_file_state',lambda a,b:False)
    r=organize(root,POLICY);assert r['checkpoint']=='INCOMPLETE';assert path.exists();assert len(catalog(root))==1
def test_tampered_master_not_silently_accepted(root,make_image):
    make_image(root/'x.png');organize(root,POLICY);row=catalog(root)[0];path=root/row['relative'];path.write_bytes(path.read_bytes()+b'private')
    assert audit_workspace(root)['checkpoint']=='INCOMPLETE';assert organize(root,POLICY)['checkpoint']=='INCOMPLETE'
def test_missing_master_detected(root,make_image):
    make_image(root/'x.png');organize(root,POLICY);(root/catalog(root)[0]['relative']).unlink();assert audit_workspace(root)['checkpoint']=='INCOMPLETE'
def test_lock(root):
    with workspace_lock(root):
        with pytest.raises(RiposteError,match='LOCKED'):
            with workspace_lock(root):pass
@pytest.mark.parametrize('relative',['../escape','/tmp/escape','hello/../escape','a\\b'])
def test_path_escape_rejected(root,relative):
    with pytest.raises(RiposteError):safe_child(root,relative)
def test_reserved_directory_not_ignored(root,make_image):
    make_image(root/'.riposte'/'source.png')
    with pytest.raises(RiposteError,match='CONFLICT'):plan(root,POLICY)
def test_symlink_not_followed(root,tmp_path,make_image):
    target=make_image(tmp_path/'outside.png');link=root/'link.png'
    try:link.symlink_to(target)
    except OSError:pytest.skip('Symlinks unavailable')
    assert organize(root,POLICY)['checkpoint']=='INCOMPLETE';assert target.exists()
def test_hardlink_not_migrated(root,tmp_path,make_image):
    target=make_image(tmp_path/'outside.png')
    try:os.link(target,root/'link.png')
    except OSError:pytest.skip('Hardlinks unavailable')
    assert organize(root,POLICY)['checkpoint']=='INCOMPLETE';assert target.exists()

def test_missing_catalog_blocks_plan_and_apply(root,make_image):
    from riposte.store import catalog
    make_image(root/'input.png');organize(root,Policy(date_mode='modified'))
    (root/catalog(root)[0]['relative']).unlink()
    assert plan(root)['blockers']['CATALOG_FILE_MISSING']==1
    assert organize(root)['checkpoint']=='INCOMPLETE'
