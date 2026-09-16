import binascii
import io
import os
import struct
import numpy as np
import pytest
from PIL import Image, PngImagePlugin, ImageCms
from riposte.errors import RiposteError
from riposte.policy import Policy
from riposte.sanitize import decode_clean,encode_clean,png_audit,social_render

def chunk(kind,payload):return struct.pack(">I",len(payload))+kind+payload+struct.pack(">I",binascii.crc32(kind+payload)&0xffffffff)

def test_strip_png_text(root,make_image):
    path=make_image(root/"original.png");clean=decode_clean(path,Policy(date_mode="modified"));data=encode_clean(clean.pixels,clean.day)
    assert b"PRIVATE_FIXTURE_PAYLOAD" not in data
    assert png_audit(data)["date"]=="2025-03-12"
    with Image.open(io.BytesIO(data)) as im:assert im.info=={"Creation Time":"2025-03-12"}

def test_orientation_exif_and_private_comment(root):
    im=Image.new("RGB",(30,50));exif=Image.Exif();exif[274]=6;exif[270]="PRIVATE_FIXTURE_PAYLOAD";exif[306]="2024:06:01 12:30:00";exif[34853]={0:bytes([2,3,0,0])}
    path=root/"photo.jpg";im.save(path,exif=exif)
    clean=decode_clean(path,Policy(date_mode="embedded"));assert clean.pixels.size==(50,30);assert clean.day=="2024-06-01"
    data=encode_clean(clean.pixels,clean.day);assert b"PRIVATE_FIXTURE" not in data;assert b"Exif" not in data;png_audit(data)

def test_hidden_rgb_erased(root):
    arr=np.zeros((40,40,4),dtype=np.uint8);arr[:,:,:3]=[123,74,201];arr[:20,:,3]=255
    path=root/"alpha.png";Image.fromarray(arr).save(path)
    clean=decode_clean(path);a=np.asarray(clean.pixels)
    assert np.all(a[20:,:,:3]==0);assert np.all(a[:20,:,:3]==arr[:20,:,:3])
    png_audit(encode_clean(clean.pixels,clean.day))

@pytest.mark.parametrize("kind,payload",[(b"tEXt",b"Comment\x00private"),(b"iTXt",b"private"),(b"eXIf",b"private"),(b"iCCP",b"private"),(b"zTXt",b"private")])
def test_reject_extra_chunks(kind,payload):
    data=encode_clean(Image.new("RGB",(32,32)),"2025-01-01")
    malicious=data[:-12]+chunk(kind,payload)+data[-12:]
    with pytest.raises(RiposteError):png_audit(malicious)
@pytest.mark.parametrize("tail",[b"x",b"\x00",b"PRIVATE_FIXTURE_PAYLOAD"])
def test_trailing_data_rejected(tail):
    data=encode_clean(Image.new("RGB",(32,32)),"2025-01-01")
    with pytest.raises(RiposteError):png_audit(data+tail)
def test_crc_rejected():
    data=bytearray(encode_clean(Image.new("RGB",(32,32)),"2025-01-01"));data[29]^=1
    with pytest.raises(RiposteError):png_audit(bytes(data))
@pytest.mark.parametrize("fmt,suffix",[("PNG",".png"),("JPEG",".jpg"),("WEBP",".webp"),("BMP",".bmp"),("TIFF",".tiff"),("GIF",".gif")])
def test_supported_flat_formats(root,make_image,fmt,suffix):
    clean=decode_clean(make_image(root/("file"+suffix),fmt=fmt));png_audit(encode_clean(clean.pixels,clean.day))
def test_icc_converted_not_copied(root):
    profile=ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    path=root/"color.png";Image.new("RGB",(32,32),(120,40,50)).save(path,icc_profile=profile)
    clean=decode_clean(path);assert "icc_profile" not in clean.pixels.info
    assert b"iCCP" not in encode_clean(clean.pixels,clean.day)
def test_bad_icc_not_silently_removed(root):
    path=root/"bad.png";Image.new("RGB",(32,32)).save(path,icc_profile=b"invalid")
    with pytest.raises(RiposteError,match="COLOR_PROFILE"):decode_clean(path)
def test_animation_blocked(root):
    path=root/"animation.gif";a=Image.new("RGB",(20,20),"red");b=Image.new("RGB",(20,20),"blue");a.save(path,save_all=True,append_images=[b])
    with pytest.raises(RiposteError,match="MULTIFRAME"):decode_clean(path)
def test_16bit_rejected(root):
    path=root/"depth.png";Image.fromarray(np.full((20,20),5000,dtype=np.uint16)).save(path)
    with pytest.raises(RiposteError,match="HIGH_BIT_DEPTH"):decode_clean(path)
def test_limits(root,make_image):
    path=make_image(root/"x.png")
    with pytest.raises(RiposteError,match="PIXEL_LIMIT"):decode_clean(path,Policy(max_pixels=1))
    with pytest.raises(RiposteError,match="FILE_LIMIT"):decode_clean(path,Policy(max_file_bytes=1))
def test_no_upscale():
    assert social_render(Image.new("RGB",(128,64)),1024).size==(128,64)
def test_palette_transparency(root):
    im=Image.new("P",(32,32));im.putpalette([255,0,0]+[0,0,0]*255);im.info['transparency']=0
    path=root/"pal.png";im.save(path)
    clean=decode_clean(path);assert clean.pixels.mode=='RGBA';assert np.all(np.asarray(clean.pixels)==0)

def test_palette_transparency_survives_color_conversion(tmp_path):
    from PIL import ImageCms
    path=tmp_path/'palette.png'
    im=Image.new('P',(32,32),0)
    palette=[255,0,0,0,180,0]+[0]*762
    im.putpalette(palette);im.putpixel((10,10),1)
    profile=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    im.save(path,transparency=0,icc_profile=profile)
    cleaned=decode_clean(path)
    assert cleaned.pixels.mode=='RGBA'
    assert cleaned.pixels.getpixel((0,0))==(0,0,0,0)
    assert cleaned.pixels.getpixel((10,10))[3]==255
    png_audit(encode_clean(cleaned.pixels,cleaned.day))
