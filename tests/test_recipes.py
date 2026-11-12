"""Saved publishing settings: privacy, read-only previews and atomic stale-write refusal."""
import json
import os
import pytest
from riposte import recipes as r
from riposte.errors import RiposteError
from riposte.store import state_relative, workspace_lock


def save(root, name='Print', **changes):
    return r.save_recipe(root, name, {**r.defaults(), **changes}, expected_revision=r.load_library(root).revision)


def library(root):
    return root / state_relative(root, 'publishing-recipes.json')


def test_preview_is_read_only_and_save_has_only_supported_settings(root, make_image):
    source=make_image(root/'_float_'/'private.png'); before=source.read_bytes()
    assert r.inspect_recipes(root)['recipes']==[]
    draft=r.inspect_recipes(root,'Print',settings={'edges':[768,1536], 'seed':99})
    assert draft['revision']=='missing' and not (root/'.riposte').exists()
    assert draft['processing_started'] is False and draft['writes'] is False
    saved=r.save_recipe(root,'Print',draft['settings'],expected_revision=draft['revision'])
    document=json.loads(library(root).read_bytes())
    assert set(document)=={'version','recipes'} and document['version']==1
    assert set(document['recipes'][0])=={'name','settings'}
    assert set(document['recipes'][0]['settings'])==r.SETTINGS
    assert source.read_bytes()==before and not (root/'.riposte/catalog.sqlite').exists()
    assert r.inspect_recipes(root,'print')['settings']['seed']==99
    assert saved['writes'] and not saved['processing_started']


@pytest.mark.parametrize('key',['root','input_paths','image_ids','device','vae_dirs','pipeline_directory','model_identity','approved','visual_accepted','recipe_revision'])
def test_private_and_unknown_fields_rejected_before_state_creation(root,key):
    with pytest.raises(RiposteError,match='RECIPE_SETTINGS_INVALID'):
        r.save_recipe(root,'Print',{**r.defaults(),key:'secret'},expected_revision='missing')
    assert not list(root.iterdir())


@pytest.mark.parametrize('changes',[
    {'edges':[]},{'edges':[True]},{'edges':[64,64]},{'edges':[64,128,256,512]},
    {'edges':[[64]]},{'edges':[4097]},{'epsilon':True},{'seed':-1},{'seed':2**32},
    {'steps':1001},{'restarts':0},{'preserve_white':1},{'rms_fraction':float('nan')},
    {'delta_e76_p95':float('inf')},{'rms_fraction':10**1000},{'epsilon':'4'}])
def test_strict_invalid_settings(root,changes):
    with pytest.raises(RiposteError,match='RECIPE_SETTINGS_INVALID'):
        r.inspect_recipes(root,'Print',settings=changes)
    assert not list(root.iterdir())


@pytest.mark.parametrize('name',['','../Print','C:\\Private','a/b','x.txt','<img>','a\nname','_hidden','a'*65])
def test_names_cannot_contain_paths_or_controls(root,name):
    with pytest.raises(RiposteError,match='RECIPE_NAME_INVALID'):save(root,name)


def test_unicode_identity_and_unrelated_saves_preserve_selected_revision(root):
    first=save(root,' Café ',edges=[2048,768])
    assert first['name']=='Café'
    save(root,'Other')
    assert r.resolve_recipe(root,'CAFÉ',revision=first['recipe_revision']).edges==(2048,768)
    replacement=save(root,'Ｃａｆé',seed=99)
    assert len(replacement['recipes'])==2
    with pytest.raises(RiposteError,match='RECIPE_CHANGED'):
        r.resolve_recipe(root,'Café',revision=first['recipe_revision'])


def test_revision_required_and_stale_saves_preserve_bytes(root):
    with pytest.raises(RiposteError,match='RECIPE_REVISION_REQUIRED'):
        r.save_recipe(root,'A',r.defaults(),expected_revision='')
    assert not list(root.iterdir())
    save(root);before=library(root).read_bytes()
    with pytest.raises(RiposteError,match='RECIPE_LIBRARY_CHANGED'):
        r.save_recipe(root,'Other',r.defaults(),expected_revision='missing')
    assert library(root).read_bytes()==before


@pytest.mark.parametrize('damage',['syntax','version','duplicate_keys','duplicate_names','unknown','directory','oversized','hardlink'])
def test_corrupt_library_never_overwritten(root,damage):
    first=save(root);p=library(root);raw=p.read_bytes();document=json.loads(raw)
    if damage=='syntax':p.write_bytes(b'{')
    if damage=='version':document['version']=2;p.write_text(json.dumps(document))
    if damage=='duplicate_keys':p.write_bytes(b'{"version":1,"version":1,"recipes":[]}')
    if damage=='duplicate_names':document['recipes']*=2;p.write_text(json.dumps(document))
    if damage=='unknown':document['recipes'][0]['settings']['model']='private';p.write_text(json.dumps(document))
    if damage=='directory':p.unlink();p.mkdir()
    if damage=='oversized':p.write_bytes(b' '* (r.MAX_BYTES+1))
    if damage=='hardlink':os.link(p,root/'linked.json')
    before=p.read_bytes() if p.is_file() else None
    with pytest.raises(RiposteError):
        r.save_recipe(root,'Print',r.defaults(),expected_revision=first['revision'])
    assert (p.read_bytes() if p.is_file() else None)==before


def test_atomic_replace_failure_preserves_library_and_cleans_temporary(root,monkeypatch):
    save(root);before=library(root).read_bytes()
    def fail(*args):raise PermissionError()
    monkeypatch.setattr(r.os,'replace',fail)
    with pytest.raises(RiposteError,match='RECIPE_SAVE_FAILED'):save(root,seed=88)
    assert library(root).read_bytes()==before
    assert not list(library(root).parent.glob('.publishing-recipes-*.tmp'))


def test_revision_rechecked_after_temporary_write(root,monkeypatch):
    original=save(root);replacement=library(root).read_bytes().replace(b'24',b'25')
    monkeypatch.setattr(r.os,'fsync',lambda fd:library(root).write_bytes(replacement))
    with pytest.raises(RiposteError,match='RECIPE_LIBRARY_CHANGED'):
        r.save_recipe(root,'Print',r.defaults(),expected_revision=original['revision'])
    assert library(root).read_bytes()==replacement
    assert not list(library(root).parent.glob('.publishing-recipes-*.tmp'))


def test_workspace_lease_and_limit(root,monkeypatch):
    save(root,'A');before=library(root).read_bytes()
    with workspace_lock(root):
        with pytest.raises(RiposteError,match='WORKSPACE_LOCKED'):save(root,'B')
    monkeypatch.setattr(r,'MAX_RECIPES',1)
    with pytest.raises(RiposteError,match='RECIPE_LIBRARY_FULL'):save(root,'B')
    assert library(root).read_bytes()==before
    assert save(root,'A',seed=9)['settings']['seed']==9


def test_legacy_workspace_uses_its_existing_namespace(root):
    from riposte.store import LEGACY_SIGNATURE
    folder=root/'.shroud';folder.mkdir();(folder/'WORKSPACE').write_text(LEGACY_SIGNATURE)
    result=save(root)
    assert result['writes'] and (folder/'publishing-recipes.json').is_file()
    assert not (root/'.riposte').exists()


def test_linked_library_refused(root):
    save(root);original=library(root);outside=root/'keep.json';original.rename(outside)
    try:original.symlink_to(outside)
    except OSError:pytest.skip('Symlink privilege unavailable on this Windows account')
    before=outside.read_bytes()
    with pytest.raises(RiposteError):save(root)
    assert outside.read_bytes()==before
