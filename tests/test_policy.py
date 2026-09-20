import datetime as dt
from types import SimpleNamespace
import pytest
from PIL import Image
from riposte.errors import RiposteError
from riposte.policy import size_bin, folder_for, valid_day, canonical_path, extract_day, Policy, MONTHS

@pytest.mark.parametrize("w,h,expected",[(1,1,"SML"),(999,1000,"SML"),(1000,1000,"MED"),(1999,2000,"MED"),(2000,2000,"LRG"),(3999,4000,"LRG"),(4000,4000,"XTL"),(16000,10,"SML")])
def test_bins(w,h,expected):assert size_bin(w,h)==expected
@pytest.mark.parametrize("month",range(1,13))
@pytest.mark.parametrize("year",[2023,2024,2025,2026,2027])
def test_folders(month,year):
    folder=folder_for(f"{year}-{month:02d}-02",100,100)
    assert folder.parts==(str(year),MONTHS[month-1],"SML")
@pytest.mark.parametrize("value",["2025-02-29","2026-13-01","2026-1-01","2026-01-01T00:00","private",123,None,"2026-01-01;payload"])
def test_bad_date(value):
    with pytest.raises(RiposteError):valid_day(value)
@pytest.mark.parametrize("value",["../x","2025/March/SML/MED01.png","2025/March/SML/SML01.jpg","0000/March/SML/SML01.png","2025/March/SML/SML1.png"])
def test_bad_canonical(value):
    with pytest.raises(RiposteError):canonical_path(value)
def test_modified_fallback():
    stamp=dt.datetime(2024,1,12,12).timestamp()
    day,source=extract_day(Image.new("RGB",(1,1)),SimpleNamespace(st_mtime=stamp,st_ctime=stamp),"modified")
    assert (day,source)==("2024-01-12","filesystem_modified")
def test_birth_precedence():
    s=SimpleNamespace(st_mtime=dt.datetime(2024,1,12,12).timestamp(),st_birthtime=dt.datetime(2025,3,12,12).timestamp())
    assert extract_day(Image.new("RGB",(1,1)),s,"download")==("2025-03-12","filesystem_creation")
def test_invalid_policy():
    with pytest.raises(RiposteError):Policy(date_mode="GPS")

def test_month_names_are_rigid_english():
    from riposte.policy import MONTHS
    assert MONTHS==('January','February','March','April','May','June','July','August','September','October','November','December')
