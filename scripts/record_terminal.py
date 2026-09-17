"""Record a read-only navigation rehearsal from a real Rich POSIX terminal.

Requires pexpect and a dedicated developer fixture workspace. The recording is
asciinema v2 output, not a Windows/macOS screenshot or model-efficacy result.
"""
from pathlib import Path
import argparse,io,json,os,sys,time
import pexpect


def record(root,out):
    if out.exists():raise SystemExit('Refusing to overwrite a recording.')
    events=[];start=time.monotonic()
    class Sink:
        def write(self,text):events.append([round(time.monotonic()-start,4),'o',text])
        def flush(self):pass
    child=pexpect.spawn(sys.executable,['-m','riposte','ui',str(root)],env={**os.environ,'TERM':'xterm-256color','COLORTERM':'truecolor'},encoding='utf-8',dimensions=(38,112),timeout=10)
    child.logfile_read=Sink()
    try:
        child.expect('ACTION DECK')
        # Keep reading during motion; never fabricate a progress event.
        for _ in range(14):
            try:child.read_nonblocking(65536,timeout=.12)
            except pexpect.TIMEOUT:pass
        child.send('2');child.expect('CLEAN LIBRARY')
        child.send('\r');child.send('i');child.expect('ASCII COMPOSITION PREVIEW')
        for _ in range(5):
            try:child.read_nonblocking(65536,timeout=.12)
            except pexpect.TIMEOUT:pass
        child.send('p');child.expect('PUBLISHING EDGES')
        child.send('\x1bOS');child.expect('DIRECT COMMAND / INSPECT ONLY')
        child.send('\x1b');child.expect('PUBLISHING EDGES')
        child.send('\x1bOR');child.send('\x1bOP');child.expect('CONTEXTUAL HELP')
        child.send('\x1b');child.expect('PUBLISHING EDGES');child.send('q');child.expect(pexpect.EOF)
    finally:child.close(force=True)
    assert child.exitstatus==0
    out.write_text(json.dumps({'version':2,'width':112,'height':38,'title':'RIPOSTE 0.5 / real POSIX Rich terminal / synthetic art / read-only navigation','env':{'TERM':'xterm-256color','COLORTERM':'truecolor'}})+'\n'+'\n'.join(json.dumps(e) for e in events)+'\n')
    return {'exit_status':child.exitstatus,'events':len(events),'seconds':round(time.monotonic()-start,2),'native_pty':True,'artwork':'SYNTHETIC_GEOMETRIC_FIXTURES','writes_requested':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(record(a.root,a.output),indent=2))
