import json
import os
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path('src').resolve()))
from PIL import Image
from riposte.sanitize import decode_clean

keys=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns')
with tempfile.TemporaryDirectory(dir='typing/.cache') as name:
    for i in range(6):
        path=Path(name)/f'fixture{i}.png'
        Image.new('RGB',(64,64),(80,90,100)).save(path)
        source=decode_clean(path).source_stat
        current=path.stat()
        print(json.dumps({'case':i,'differences':{key:[getattr(source,key),getattr(current,key)] for key in keys if getattr(source,key)!=getattr(current,key)}}))
        os.utime(path, (1741780800,1741780800))
        source=decode_clean(path).source_stat
        current=path.stat()
        print(json.dumps({'case':i,'fixed_timestamp_differences':{key:[getattr(source,key),getattr(current,key)] for key in keys if getattr(source,key)!=getattr(current,key)}}))
