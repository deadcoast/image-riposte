"""Real POSIX pseudo-terminal plus platform-adapter contract checks."""
import io,os,sys,signal
from pathlib import Path
from types import SimpleNamespace
import pytest
from riposte.terminal.keyboard import TerminalKeys,Key

@pytest.mark.skipif(os.name=='nt',reason='POSIX pseudo-terminal contract')
@pytest.mark.parametrize('exit_mode',['q','interrupt','sigterm','resize'])
def test_actual_native_rich_pty_restores_terminal(root,exit_mode):
    pexpect=pytest.importorskip('pexpect')
    import riposte
    source=str(Path(riposte.__file__).parent.parent)
    code="""import sys,termios
from riposte.cli import main
before=termios.tcgetattr(0)
status=main(['ui',sys.argv[1]])
assert termios.tcgetattr(0)==before
print('TERMINAL_RESTORED='+str(status),flush=True)
"""
    env={**os.environ,'PYTHONPATH':source,'TERM':'xterm-256color'}
    child=pexpect.spawn(sys.executable,['-c',code,str(root)],env=env,encoding='utf-8',timeout=10,dimensions=(34,100))
    capture=io.StringIO();child.logfile_read=capture
    try:
        child.expect('ACTION DECK')
        child.send('\x1bOQ');child.send('\x1bOR') # freeze motion and light palette
        child.send('2');child.expect('CLEAN LIBRARY')
        child.send('/nothing-matches\r');child.expect('No matching clean images')
        child.send('\x1b');child.expect('ACTION DECK')
        if exit_mode=='q':child.send('q')
        elif exit_mode=='interrupt':child.sendcontrol('c')
        elif exit_mode=='sigterm':os.kill(child.pid,signal.SIGTERM)
        else:
            child.setwinsize(18,60);child.expect('compact terminal');child.send('3')
            child.setwinsize(24,79);child.expect('ACTION DECK');child.send('q')
        child.expect('TERMINAL_RESTORED='+('143' if exit_mode=='sigterm' else '0'))
        child.expect(pexpect.EOF)
    finally:child.close(force=True)
    text=capture.getvalue()
    assert '\x1b[?1049h' in text and '\x1b[?1049l' in text
    assert '\x1b[?2004h' in text and '\x1b[?2004l' in text and '\x1b[?25h' in text
    assert not list(root.iterdir())
    assert child.exitstatus==0

@pytest.mark.parametrize('special,expected',[('H','up'),('P','down'),(';','f1'),('<','f2'),('=','f3'),('>','f4')])
def test_windows_console_key_adapter(special,expected,monkeypatch):
    import riposte.terminal.keyboard as keyboard
    queue=['\xe0',special]
    monkeypatch.setattr(keyboard,'os',SimpleNamespace(name='nt'))
    monkeypatch.setitem(sys.modules,'msvcrt',SimpleNamespace(kbhit=lambda:bool(queue),getwch=lambda:queue.pop(0)))
    output=io.StringIO();stream=SimpleNamespace(isatty=lambda:True)
    with TerminalKeys(stream=stream,output=output) as keys:assert keys.read(.1)==Key(expected)
    assert output.getvalue().endswith('\x1b[?2004l\x1b[?25h')


def test_keyboard_cleanup_on_output_exception(monkeypatch):
    import riposte.terminal.keyboard as k
    monkeypatch.setattr(k,'os',SimpleNamespace(name='nt'))
    class Broken:
        def write(self,*a):raise OSError('fixture')
        def flush(self):pass
    keys=TerminalKeys(stream=SimpleNamespace(isatty=lambda:True),output=Broken())
    with pytest.raises(OSError):keys.__enter__()
    assert not keys.active
