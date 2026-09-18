"""Exercise launcher decisions without installing dependencies or opening a UI.

Real Python evaluates the version/source checks. Launch is recorded by a process
adapter. Stale installs must request explicit INSTALL, never install during START.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('shell', ['powershell', 'bash'])
@pytest.mark.parametrize('checkout', [False, True])
@pytest.mark.parametrize('with_root', [False, True])
def test_launcher_requires_explicit_install_and_allows_menu_first(tmp_path, shell, checkout, with_root):
    project = tmp_path / 'application with spaces'
    project.mkdir()
    artwork = tmp_path / 'artwork with spaces'
    artwork.mkdir()
    original = artwork / 'keep.txt'
    original.write_bytes(b'UNCHANGED')
    (project / 'pyproject.toml').write_text('[project]\nversion = "0.5.0"\n')
    source = project / 'src' if checkout else tmp_path / 'copied-install'
    (source / 'riposte').mkdir(parents=True)
    (source / 'riposte/__init__.py').write_text('')
    calls = tmp_path / 'calls.jsonl'
    env = {**os.environ, 'PYTHONPATH': str(source), 'RIPOSTE_LAUNCH_TEST_LOG': str(calls)}
    if shell == 'powershell':
        host = shutil.which('pwsh') or shutil.which('powershell')
        if host is None:
            pytest.skip('PowerShell is unavailable')
        shutil.copyfile(ROOT / 'START.ps1', project / 'START.ps1')
        python = project / '.venv/Scripts/python.exe'
        python.parent.mkdir(parents=True)
        python.touch()
        # PowerShell resolves a function named with the exact command path.
        # Only the subprocess boundary is adapted; execute the real launcher.
        def quoted(value):
            return "'" + str(value).replace("'", "''") + "'"
        script = tmp_path / 'invoke.ps1'
        script.write_text(f'''
$shim = {{
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$tokens)
    if ($tokens[0] -eq '-c') {{
        & {quoted(sys.executable)} @tokens
        $global:LASTEXITCODE = $LASTEXITCODE
    }} else {{
        ConvertTo-Json -InputObject @($tokens) -Compress | Add-Content -LiteralPath $env:RIPOSTE_LAUNCH_TEST_LOG
        $global:LASTEXITCODE = 0
    }}
}}
Set-Item -LiteralPath {quoted('Function:' + str(python))} -Value $shim
& {quoted(project / 'START.ps1')} {'-ArtworkFolder ' + quoted(artwork) if with_root else ''} -Linear -NoAnimation
''')
        result = subprocess.run([host, '-NoProfile', '-File', str(script)], env=env, capture_output=True, text=True, timeout=30)
    else:
        host = shutil.which('bash') if os.name != 'nt' else 'C:/Program Files/Git/bin/bash.exe'
        if not host or not Path(host).is_file():
            pytest.skip('An executable Bash host is unavailable')
        shutil.copyfile(ROOT / 'START.sh', project / 'START.sh')
        python = project / '.venv/bin/python'
        python.parent.mkdir(parents=True)
        import shlex
        real = shlex.quote(Path(sys.executable).as_posix())
        python.write_text(f'''#!/usr/bin/env bash
if [[ "$1" == '-c' ]]; then exec {real} "$@"; fi
exec {real} -c 'import json,os,sys;open(os.environ["RIPOSTE_LAUNCH_TEST_LOG"],"a").write(json.dumps(sys.argv[1:])+"\\n")' "$@"
''', newline='\n')
        python.chmod(0o755)
        shim = tmp_path / 'shims'
        shim.mkdir()
        (shim / 'python3').write_text(f'#!/usr/bin/env bash\nexec {real} "$@"\n', newline='\n')
        (shim / 'python3').chmod(0o755)
        env['PATH'] = str(shim) + os.pathsep + env['PATH']
        result = subprocess.run([host, str(project / 'START.sh'), *([str(artwork)] if with_root else []), '--linear', '--no-animation'], env=env, capture_output=True, text=True, timeout=30)
    if not checkout:
        assert result.returncode != 0
        assert 'INSTALL' in result.stdout + result.stderr
        assert not calls.exists()
        assert original.read_bytes() == b'UNCHANGED'
        return
    assert result.returncode == 0, result.stdout + result.stderr
    commands = [json.loads(line) for line in calls.read_text(encoding='utf-8-sig').splitlines()]
    installs = [args for args in commands if args[:2] == ['-m', 'pip']]
    assert not installs
    assert commands[-1][:2] == ['-m', 'riposte']
    assert '--plain' in commands[-1] and 'ui' in commands[-1]
    assert (commands[-1][-1] == 'ui') is (not with_root)
    assert original.read_bytes() == b'UNCHANGED' and list(artwork.iterdir()) == [original]


@pytest.mark.parametrize('shell', ['powershell', 'bash'])
@pytest.mark.parametrize('lab', [False, True])
def test_installer_uses_existing_uv_without_requesting_images_or_launching(tmp_path, shell, lab):
    project=tmp_path/'app with spaces';project.mkdir()
    calls=tmp_path/'install.jsonl'
    env={**os.environ, 'RIPOSTE_LAUNCH_TEST_LOG':str(calls)}
    if shell=='powershell':
        host=shutil.which('pwsh') or shutil.which('powershell')
        if not host:pytest.skip('PowerShell unavailable')
        shutil.copyfile(ROOT/'INSTALL.ps1',project/'INSTALL.ps1')
        script=tmp_path/'install.ps1'
        script.write_text('''function uv {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$tokens)
    ConvertTo-Json -InputObject @($tokens) -Compress | Add-Content -LiteralPath $env:RIPOSTE_LAUNCH_TEST_LOG
    $global:LASTEXITCODE=0
}
& '''+"'"+str(project/'INSTALL.ps1').replace("'","''")+"'"+(' -Lab' if lab else ''))
        result=subprocess.run([host,'-NoProfile','-File',str(script)],env=env,input='',capture_output=True,text=True,timeout=30)
    else:
        host=shutil.which('bash') if os.name!='nt' else 'C:/Program Files/Git/bin/bash.exe'
        if not host or not Path(host).is_file():pytest.skip('Bash unavailable')
        shutil.copyfile(ROOT/'INSTALL.sh',project/'INSTALL.sh')
        shim=tmp_path/'shims';shim.mkdir()
        import shlex
        (shim/'uv').write_text('#!/usr/bin/env bash\nexec '+shlex.quote(Path(sys.executable).as_posix())+''' -c 'import json,os,sys;open(os.environ["RIPOSTE_LAUNCH_TEST_LOG"],"a").write(json.dumps(sys.argv[1:])+"\\n")' "$@"
''',newline='\n')
        (shim/'uv').chmod(0o755)
        env['PATH']=str(shim)+os.pathsep+env['PATH']
        result=subprocess.run([host,str(project/'INSTALL.sh'),*(['--lab'] if lab else [])],env=env,input='',capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    commands=[json.loads(line) for line in calls.read_text(encoding='utf-8-sig').splitlines()]
    assert len(commands)==1 and commands[0][:3]==['sync','--frozen','--inexact']
    assert ('--extra' in commands[0]) is lab
    assert 'Installed.' in result.stdout and not (project/'.riposte').exists()
