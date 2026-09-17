import hashlib
from pathlib import Path
import pytest
from riposte.errors import RiposteError
from riposte.organizer import organize, plan
from riposte.policy import Policy
from riposte.store import (SIGNATURE,LEGACY_SIGNATURE,legacy_workspace,upgrade_workspace,check_root,
                          state_relative,catalog,workspace_lock,atomic_json_write)
from riposte.lab import compare_external,trials,trial_pixels,export_candidate

def legacy(root):
    (root/'.riposte').rename(root/'.shroud');(root/'.shroud/WORKSPACE').write_text(LEGACY_SIGNATURE)

def snapshot(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

def test_legacy_read_is_nonmutating_then_upgrade_keeps_art_ids(root,tmp_path,make_image):
    make_image(root/'former/a.png');organize(root,Policy(date_mode='modified'))
    candidate=make_image(tmp_path/'external.png',color=(31,91,150))
    original=catalog(root);trial=compare_external(root,original[0]['id'],candidate);legacy(root)
    before=snapshot(root)
    assert legacy_workspace(root) and state_relative(root,'lab').startswith('.shroud/')
    assert catalog(root)==original and trials(root)[0]['id']==trial['id']
    assert trial_pixels(root,trial['id'],'candidate')
    plan(root,Policy(date_mode='modified'));assert snapshot(root)==before
    result=upgrade_workspace(root)
    assert result['artwork_rewritten']==0 and not legacy_workspace(root)
    assert catalog(root)==original and trials(root)[0]['id']==trial['id']
    after=snapshot(root)
    for name,digest in before.items():
        if name!='.shroud/WORKSPACE':assert after[name.replace('.shroud/','.riposte/')]==digest
    assert export_candidate(root,trial['id'],True)['relative'].startswith('.riposte/')

def test_empty_root_upgrade_has_no_scaffold(root):
    assert upgrade_workspace(root)['status']=='ALREADY_CURRENT'
    assert not list(root.iterdir())

def test_interrupted_marker_upgrade_finishes(root,make_image):
    make_image(root/'a.png');organize(root,Policy(date_mode='modified'))
    (root/'.riposte/WORKSPACE').write_text(LEGACY_SIGNATURE)
    assert legacy_workspace(root)
    assert upgrade_workspace(root)['status']=='UPGRADED'
    assert (root/'.riposte/WORKSPACE').read_text()==SIGNATURE

def test_namespace_conflict_no_mutation(root,make_image):
    make_image(root/'a.png');organize(root,Policy(date_mode='modified'))
    (root/'.shroud').mkdir();(root/'.shroud/WORKSPACE').write_text(LEGACY_SIGNATURE)
    before=snapshot(root)
    with pytest.raises(RiposteError,match='NAMESPACE_CONFLICT'):upgrade_workspace(root)
    assert snapshot(root)==before

def test_locked_legacy_cannot_upgrade(root,make_image):
    make_image(root/'a.png');organize(root,Policy(date_mode='modified'));legacy(root)
    with workspace_lock(root):
        with pytest.raises(RiposteError,match='LOCKED'):upgrade_workspace(root)
    assert not (root/'.riposte').exists()

@pytest.mark.parametrize('name',['.riposte','.shroud'])
def test_unknown_state_not_silently_adopted(root,name):
    (root/name).mkdir();(root/name/'WORKSPACE').write_text('UNRELATED')
    with pytest.raises(RiposteError,match='CONFLICT'):check_root(root)

def test_atomic_report_no_overwrite_no_nan_no_temporary_files(root):
    from riposte.store import state_dir
    state_dir(root);atomic_json_write(root,'.riposte/a.json',{'a':1})
    with pytest.raises(RiposteError,match='DESTINATION_EXISTS'):atomic_json_write(root,'.riposte/a.json',{'a':2})
    with pytest.raises(ValueError):atomic_json_write(root,'.riposte/b.json',{'a':float('nan')})
    assert not list(root.rglob('*.tmp'))
