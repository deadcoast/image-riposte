"""Exercise the real Windows START launcher and raw keyboard loop through ConPTY.

No application/controller mocks and no line-input mode. Uses synthetic folders;
runs read-only duplicate analysis on synthetic text files. Run from the repository root on Windows 10+.
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


def main(entry='powershell'):
    root = Path(__file__).resolve().parents[2]
    evidence = Path(__file__).parent
    fixture = Path(tempfile.mkdtemp(prefix='riposte-duplicates-console-'))
    (fixture / 'Pictures' / 'sample folder').mkdir(parents=True, exist_ok=True)
    (fixture / 'Pictures' / 'original.txt').write_bytes(b'synthetic unchanged input')
    (fixture / 'Pictures' / 'copy.txt').write_bytes(b'synthetic unchanged input')
    before = {str(p.relative_to(fixture)): p.read_bytes() for p in fixture.rglob('*') if p.is_file()}
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
    command = c.create_unicode_buffer(subprocess.list2cmdline(args))
    environment = {**os.environ, 'USERPROFILE': str(fixture), 'TERM': 'xterm-256color'}
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
        expect('MAIN MENU'); assert 'value (/cancel)>' not in plain()
        expect('Duplicate Finder')
        offset=send('d');expect('EDIT / SCAN FOLDER',offset)
        offset=send(str(fixture/'Pictures')+'\r');expect('DUPLICATE FINDER',offset)
        passed.append('START opens the raw terminal; d selects Duplicate Finder and pasted path works')
        offset=send('r');expect('CONFIDENCE / FILE RELATIONSHIPS',offset);expect('100 / DUPLICATE / 2 files',offset)
        passed.append('Read-only scan finishes with an exact duplicate group')
        offset=send('3');expect('No findings match',offset)
        offset=send('2');expect('100 / DUPLICATE',offset)
        offset=send('/');expect('FIND /',offset)
        offset=send('original.txt\r');expect('original.txt',offset)
        offset=send('\r');expect('MATCH EVIDENCE',offset);expect('BYTE_EQUAL',offset)
        offset=send('\x1b');expect('CONFIDENCE / FILE RELATIONSHIPS',offset)
        offset=send('t');expect('SCAN COVERAGE',offset)
        offset=send('\x1b');expect('CONFIDENCE / FILE RELATIONSHIPS',offset)
        passed.append('Classification filters, path search, evidence and coverage return to the same findings')
        offset=send('g');expect('EDIT / SCAN FOLDER',offset)
        offset=send(str(fixture/'Pictures')+'\r');expect('DUPLICATE FINDER',offset)
        offset=send('\x1b');expect('CONFIDENCE / FILE RELATIONSHIPS',offset)
        passed.append('g reopens folder entry while retaining the prior report in navigation history')
        send('q')
        assert kernel.WaitForSingleObject(process.hProcess, 15000) == 0
        code = w.DWORD(); checked(kernel.GetExitCodeProcess(process.hProcess, c.byref(code)))
        assert code.value == 0, code.value
        assert b'\x1b[?25h' in b''.join(chunks)
        assert before == {str(p.relative_to(fixture)): p.read_bytes() for p in fixture.rglob('*') if p.is_file()}
        passed.append('Quit restores the cursor, exits zero, and leaves synthetic inputs unchanged')
        (evidence / f'native-console-{entry}.json').write_text(json.dumps({'result':'PASS','host':'Windows ConPTY','entry':entry,'checks':passed,'timings':timings}, indent=2)+'\n')
        print(json.dumps({'result':'PASS','checks':passed}, indent=2))
    finally:
        (evidence / f'native-console-{entry}.txt').write_text(plain(), encoding='utf-8')
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
    main(parser.parse_args().entry)
