import os
import datetime as dt
import pytest
from PIL import Image, PngImagePlugin

@pytest.fixture
def root(tmp_path):
    path=tmp_path/"workspace";path.mkdir();return path

@pytest.fixture
def make_image():
    def create(path, size=(64,48), color=(30,90,150), day="2025-03-12", fmt=None, metadata=True):
        path.parent.mkdir(parents=True,exist_ok=True)
        im=Image.new("RGB",size,color)
        if (fmt or path.suffix.lower()) in {"PNG",".png"} and metadata:
            info=PngImagePlugin.PngInfo();info.add_text("Comment","PRIVATE_FIXTURE_PAYLOAD")
            im.save(path,format=fmt,pnginfo=info)
        else:
            im.save(path,format=fmt)
        date=dt.datetime.fromisoformat(day+"T12:00:00").timestamp();os.utime(path,(date,date))
        return path
    return create
