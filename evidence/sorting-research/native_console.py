"""Exercise the real Windows START launcher and raw keyboard loop through ConPTY.

No application/controller mocks and no line-input mode. Uses synthetic folders;
runs sorting and undo only on its own generated image fixture. Run from the repository root on Windows 10+.
"""
import ctypes as c
from ctypes import wintypes as w
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
import tempfile


class COORD(c.Structure):
    _fields_ = [('X', c.c_short), ('Y', c.c_short)]


class STARTUPINFO(c.Structure):
    _fields_ = [('cb', w.DWORD), ('lpReserved', w.LPWSTR), ('lpDesktop', w.LPWSTR),
                ('lpTitle', w.LPWSTR), ('dwX', w.DWORD), ('dwY', w.DWORD),
                ('dwXSize', w.DWORD), ('dwYSize', w.DWORD), ('dwXCountChars', w.DWORD),
                ('dwYCountChars', w.DWORD), ('dwFillAttribute', w.DWORD),
                ('dwFlags', w.DWORD), ('wShowWindow', w.WORD), ('cbReserved2', w.WORD),
                ('lpReserved2', c.POINTER(c.c_byte)), ('hStdInput', w.HANDLE),
                ('hStdOutput', w.HANDLE), ('hStdError', w.HANDLE)]


class STARTUPINFOEX(c.Structure):
    _fields_ = [('StartupInfo', STARTUPINFO), ('lpAttributeList', c.c_void_p)]


class PROCESSINFO(c.Structure):
    _fields_ = [('hProcess', w.HANDLE), ('hThread', w.HANDLE),
                ('dwProcessId', w.DWORD), ('dwThreadId', w.DWORD)]


def main(entry='powershell', trace=False, motion=False):
    root = Path(__file__).resolve().parents[2]
    evidence = Path(__file__).parent
    label = entry + ('-motion' if motion else '-still') + ('-trace' if trace else '')
    fixture = Path(tempfile.mkdtemp(prefix='riposte-sorter-console-'))
    (fixture / 'Pictures' / 'sample folder').mkdir(parents=True, exist_ok=True)
    (fixture / 'Pictures' / 'sample.png').write_bytes(b'synthetic unchanged input')
    for n in range(40): (fixture / 'Pictures' / f'folder-{n:02d}').mkdir()
    (fixture / 'Pictures' / 'folder-39' / 'painting.xmp').write_text('synthetic retained metadata')
    (fixture / 'Pictures' / 'folder-39' / '__float__').mkdir()
    from PIL import Image
    artwork = fixture / 'actual sort'
    artwork.mkdir()
    for name in ('femaleSoldierSniperDesert.png', 'maleSoldierUniform.png', 'soldierArmorWinter.png', 'factoryPipeRust.png', 'factoryBrokenWall.png', 'factoryFloorMachinery.png', 'forestOakAutumn.png', 'forestPineSnow.png', 'forestRockMoss.png', 'SML01.png', 'holiday.png'):
        Image.new('RGB', (48, 36), (38, 85, 121)).save(artwork / name)
    held = artwork / '__float__' / 'SML03.png'
    held.parent.mkdir()
    Image.new('RGB', (48, 36), (91, 22, 71)).save(held)
    before = {p.name: p.read_bytes() for p in artwork.glob('*.png')}
    held_before = held.read_bytes()
    kernel = c.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'CreatePipe': ([c.POINTER(w.HANDLE), c.POINTER(w.HANDLE), c.c_void_p, w.DWORD], w.BOOL),
        'CreatePseudoConsole': ([COORD, w.HANDLE, w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)], c.c_long),
        'InitializeProcThreadAttributeList': ([c.c_void_p, w.DWORD, w.DWORD, c.POINTER(c.c_size_t)], w.BOOL),
        'UpdateProcThreadAttribute': ([c.c_void_p, w.DWORD, c.c_size_t, c.c_void_p, c.c_size_t, c.c_void_p, c.c_void_p], w.BOOL),
        'CreateProcessW': ([w.LPCWSTR, w.LPWSTR, c.c_void_p, c.c_void_p, w.BOOL, w.DWORD, c.c_void_p, w.LPCWSTR, c.POINTER(STARTUPINFOEX), c.POINTER(PROCESSINFO)], w.BOOL),
        'ReadFile': ([w.HANDLE, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p], w.BOOL),
        'WriteFile': ([w.HANDLE, c.c_void_p, w.DWORD, c.POINTER(w.DWORD), c.c_void_p], w.BOOL),
        'WaitForSingleObject': ([w.HANDLE, w.DWORD], w.DWORD),
        'GetExitCodeProcess': ([w.HANDLE, c.POINTER(w.DWORD)], w.BOOL),
        'CloseHandle': ([w.HANDLE], w.BOOL),
        'ClosePseudoConsole': ([w.HANDLE], None),
        'DeleteProcThreadAttributeList': ([c.c_void_p], None),
        'TerminateProcess': ([w.HANDLE, w.UINT], w.BOOL),
    }
    for name, (args, result) in signatures.items():
        function = getattr(kernel, name); function.argtypes = args; function.restype = result

    def checked(result):
        if not result: raise c.WinError(c.get_last_error())

    input_read, input_write, output_read, output_write, console = (w.HANDLE() for _ in range(5))
    checked(kernel.CreatePipe(c.byref(input_read), c.byref(input_write), None, 0))
    checked(kernel.CreatePipe(c.byref(output_read), c.byref(output_write), None, 0))
    hr = kernel.CreatePseudoConsole(COORD(100, 34), input_read, output_write, 0, c.byref(console))
    if hr: raise RuntimeError(f'CreatePseudoConsole HRESULT {hr}')
    kernel.CloseHandle(input_read); kernel.CloseHandle(output_write)
    size = c.c_size_t()
    kernel.InitializeProcThreadAttributeList(None, 1, 0, c.byref(size))
    attributes = c.create_string_buffer(size.value)
    checked(kernel.InitializeProcThreadAttributeList(attributes, 1, 0, c.byref(size)))
    checked(kernel.UpdateProcThreadAttribute(attributes, 0, 0x20016, console, c.sizeof(console), None, None))
    startup = STARTUPINFOEX(); startup.StartupInfo.cb = c.sizeof(startup)
    # Prevent the test runner's redirected standard handles leaking into ConPTY.
    # https://github.com/microsoft/terminal/discussions/15814
    startup.StartupInfo.dwFlags = 0x100  # STARTF_USESTDHANDLES, null handles
    startup.lpAttributeList = c.addressof(attributes)
    process = PROCESSINFO()
    args = ['cmd.exe', '/c', str(root / 'START.cmd'), '-NoAnimation'] if entry == 'cmd' else [
        'powershell.exe', '-NoProfile', '-File', str(root / 'START.ps1'), '-NoAnimation']
    if motion: args.pop()
    if trace:
        trace_path = evidence / ('after-input-' + label + '.jsonl')
        trace_path.write_text('')
        probe = """import json,msvcrt,sys,time
from pathlib import Path
from riposte.cli import main
original = msvcrt.getwch
def traced():
    char = original()
    with Path(sys.argv[1]).open('a') as stream:
        stream.write(json.dumps({'char': char, 'kbhit_after_read': bool(msvcrt.kbhit())}) + '\\n')
    return char
msvcrt.getwch = traced
raise SystemExit(main(['--no-animation', 'ui']))
"""
        args = [str(root / '.venv/Scripts/python.exe'), '-c', probe, str(trace_path)]
    command = c.create_unicode_buffer(subprocess.list2cmdline(args))
    cache = root / '.tmp' / 'optional-categories'
    cache.mkdir(parents=True, exist_ok=True)
    environment = {**os.environ, 'USERPROFILE': str(fixture), 'TERM': 'xterm-256color',
                   'PSModuleAnalysisCachePath': str(cache / 'module-cache')}
    envblock = c.create_unicode_buffer('\0'.join(f'{k}={v}' for k, v in sorted(environment.items())) + '\0\0')
    checked(kernel.CreateProcessW(None, command, None, None, False, 0x80000 | 0x400,
                                  envblock, str(root), c.byref(startup), c.byref(process)))
    chunks = []

    def read():
        buffer = c.create_string_buffer(65536); count = w.DWORD()
        while kernel.ReadFile(output_read, buffer, len(buffer), c.byref(count), None) and count.value:
            chunks.append(buffer.raw[:count.value])

    thread = threading.Thread(target=read, daemon=True); thread.start()

    def plain(start=0):
        data = b''.join(chunks)[start:].decode('utf-8', 'replace')
        return re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', data)

    def expect(value, start=0):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if value in plain(start): return
            if kernel.WaitForSingleObject(process.hProcess, 0) == 0: break
            time.sleep(.05)
        raise AssertionError(f'Missing native screen: {value}\n{plain(start)[-1500:]}')

    def send(value):
        start = len(b''.join(chunks)); raw = value.encode(); count = w.DWORD()
        checked(kernel.WriteFile(input_write, raw, len(raw), c.byref(count), None))
        return start

    passed = []
    timings = {}
    try:
        expect('MAIN MENU')
        offset = send('1'); expect('1. Sort', offset)
        offset = send('g'); expect('EDIT / ENTER PATH', offset)
        offset = send(str(artwork) + '\r'); expect('SORT ACTIONS', offset)
        offset = send('1'); expect('SORT PREVIEW', offset); expect('[Enter] Confirm sort', offset)
        assert not (artwork / '.riposte').exists()
        passed.append('Default Sort previews supported corpus categories and ordinary fallback without saved rules or workspace writes')
        offset = send('\r'); expect('TYPE REPLACE TO CONTINUE', offset)
        assert all((artwork / name).exists() for name in before)
        offset = send('REPLACE\r'); expect('SORT RESULT', offset); expect('[COMPLETE]', offset)
        from riposte.store import catalog
        rows = catalog(artwork)
        outputs = [artwork / row['relative'] for row in rows]
        assert sum('/img/SML/' in row['relative'] for row in rows) == 2
        assert {row['relative'].split('/')[3] for row in rows} == {'SML', 'forest', 'factory', 'soldier'}
        assert len(outputs) == 11 and not list(artwork.glob('*.png'))
        assert held.read_bytes() == held_before
        assert not any(p.name == 'uncategorized' for p in artwork.rglob('*'))
        from riposte.sanitize import png_audit
        for output in outputs: png_audit(output.read_bytes())
        passed.append('REPLACE sorts nine images into corpus categories and two into ordinary date/media/size; float storage is untouched')
        offset = send('\r'); expect('SORT ACTIONS', offset)
        offset = send('1'); expect('[NO CHANGES]', offset); expect('[Enter] Return', offset)
        offset = send('\r'); expect('SORT ACTIONS', offset)
        passed.append('Repeat sorting recognizes numbered outputs without category setup')
        offset = send('u'); expect('UNDO LAST SORT', offset); expect('[Enter] Confirm undo', offset)
        offset = send('\r'); expect('TYPE UNDO TO CONTINUE', offset)
        offset = send('UNDO\r'); expect('[COMPLETE]', offset)
        assert {p.name: p.read_bytes() for p in artwork.glob('*.png')} == before
        assert held.read_bytes() == held_before
        offset = send('\r'); expect('SORT ACTIONS', offset)
        passed.append('UNDO restores every original byte and name and returns to the sorter')
        send('q')
        assert kernel.WaitForSingleObject(process.hProcess, 15000) == 0
        code = w.DWORD(); checked(kernel.GetExitCodeProcess(process.hProcess, c.byref(code)))
        assert code.value == 0, code.value
        assert b'\x1b[?25h' in b''.join(chunks)
        passed.append('Actual launcher exits zero and restores the cursor')
        (evidence / f'native-console-{label}.json').write_text(json.dumps({'result':'PASS','host':'Windows ConPTY','entry':entry,'motion':motion,'trace':trace,'checks':passed,'timings':timings}, indent=2)+'\n')
        print(json.dumps({'result':'PASS','checks':passed}, indent=2))
    finally:
        (evidence / f'native-console-{label}.txt').write_text(plain(), encoding='utf-8')
        (evidence / f'native-console-{label}.ansi').write_bytes(b''.join(chunks))
        if kernel.WaitForSingleObject(process.hProcess, 0) != 0: kernel.TerminateProcess(process.hProcess, 99)
        kernel.CloseHandle(input_write)
        kernel.ClosePseudoConsole(console)
        kernel.CloseHandle(output_read)
        kernel.CloseHandle(process.hThread); kernel.CloseHandle(process.hProcess)
        kernel.DeleteProcThreadAttributeList(attributes)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entry', choices=['powershell','cmd'], default='powershell')
    parser.add_argument('--trace', action='store_true')
    parser.add_argument('--motion', action='store_true')
    args = parser.parse_args()
    main(args.entry, args.trace, args.motion)
