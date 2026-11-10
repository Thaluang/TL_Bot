"""
เทสต์คลังข่าวประชาสัมพันธ์ — รันจาก robot/:  python -m pytest web/test_news.py -q
"""
from datetime import date

import pytest

from news import CATEGORIES, NewsError, NewsStore

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100
TODAY = date(2026, 11, 10)


def make(tmp_path):
    return NewsStore(tmp_path)


def base(**kw):
    d = {"category": "event", "title": "งานเปิดบ้าน", "subtitle": "20 ธ.ค.", "detail": "มีกิจกรรมทุกสาขา"}
    d.update(kw)
    return d


def test_categories_fixed():
    assert CATEGORIES == ("admission", "event", "scholarship", "award", "general")


def test_add_and_reload(tmp_path):
    n = make(tmp_path).add(base(link="https://example.com/x"), JPEG)
    again = make(tmp_path).get(n["id"])
    assert again["title"] == "งานเปิดบ้าน" and again["link"] == "https://example.com/x"
    assert again["image"] and (tmp_path / "news" / again["image"]).read_bytes() == JPEG


def test_active_filters_and_orders(tmp_path):
    s = make(tmp_path)
    a = s.add(base(title="A"), None)
    s.add(base(title="ซ่อน", hidden=True), None)
    s.add(base(title="ยังไม่ถึง", start="2026-12-01"), None)
    s.add(base(title="หมดแล้ว", end="2026-11-09"), None)
    b = s.add(base(title="B", start="2026-11-10", end="2026-11-10"), None)
    s.reorder([b["id"], a["id"]])
    assert [n["title"] for n in s.active(TODAY)] == ["B", "A"]


def test_rejects_bad_fields(tmp_path):
    s = make(tmp_path)
    with pytest.raises(NewsError):
        s.add(base(category="party"), None)
    with pytest.raises(NewsError):
        s.add(base(title="   "), None)
    with pytest.raises(NewsError):
        s.add(base(link="javascript:alert(1)"), None)
    with pytest.raises(NewsError):
        s.add(base(start="10/11/2569"), None)


def test_trims_long_text(tmp_path):
    n = make(tmp_path).add(base(title="ก" * 200, subtitle="ข" * 200, detail="ค" * 3000), None)
    assert len(n["title"]) == 80 and len(n["subtitle"]) == 80 and len(n["detail"]) == 1000


def test_rejects_bad_images(tmp_path):
    s = make(tmp_path)
    with pytest.raises(NewsError):
        s.add(base(), b"GIF89a....")
    with pytest.raises(NewsError):
        s.add(base(), b"\xff\xd8\xff" + b"0" * (3 * 1024 * 1024))
    assert s.all() == []


def test_update_replaces_and_removes_image(tmp_path):
    s = make(tmp_path)
    n = s.add(base(), JPEG)
    old = n["image"]
    n2 = s.update(n["id"], {"title": "ใหม่"}, PNG)
    assert n2["title"] == "ใหม่" and n2["image"].endswith(".png") and not (tmp_path / "news" / old).exists()
    n3 = s.update(n["id"], {}, None, remove_image=True)
    assert n3["image"] == "" and not (tmp_path / "news" / n2["image"]).exists()


def test_delete_removes_image(tmp_path):
    s = make(tmp_path)
    n = s.add(base(), JPEG)
    assert s.delete(n["id"]) is True
    assert s.all() == [] and not (tmp_path / "news" / n["image"]).exists()
    assert s.delete("nope") is False


def test_corrupt_file_loads_empty(tmp_path):
    (tmp_path / "news.json").write_text("{broken", encoding="utf-8")
    assert make(tmp_path).all() == []


def test_image_path_blocks_traversal(tmp_path):
    s = make(tmp_path)
    n = s.add(base(), JPEG)
    assert s.image_path(n["image"]) == tmp_path / "news" / n["image"]
    assert s.image_path("../news.json") is None
    assert s.image_path("missing.jpg") is None


def test_version_changes_on_write(tmp_path):
    s = make(tmp_path)
    v0 = s.version
    s.add(base(), None)
    assert s.version != v0


def test_ai_text_only_active(tmp_path):
    s = make(tmp_path)
    s.add(base(title="งานเปิดบ้าน", detail="มีกิจกรรมทุกสาขา"), None)
    s.add(base(title="ข่าวซ่อน", hidden=True), None)
    txt = s.ai_text(TODAY, "th")
    assert "งานเปิดบ้าน" in txt and "มีกิจกรรมทุกสาขา" in txt and "ข่าวซ่อน" not in txt
    assert make(tmp_path / "empty").ai_text(TODAY, "th") == ""
