"""
เทสต์การหาโฟลเดอร์เก็บข้อมูลถาวร (ข่าว รูป สถิติ) — รันจากโฟลเดอร์ robot/:  python -m pytest test_datadir.py -q
"""
from datadir import DataDir, resolve_data_dir


def test_env_wins(tmp_path):
    want = tmp_path / "custom"
    media = tmp_path / "media" / "pi" / "USB1"
    media.mkdir(parents=True)
    path, persistent = resolve_data_dir({"TLBOT_DATA_DIR": str(want)}, [tmp_path / "media"], tmp_path / "fb")
    assert path == want and persistent is True and want.is_dir()


def test_first_writable_usb(tmp_path):
    (tmp_path / "media" / "pi" / "USB1").mkdir(parents=True)
    path, persistent = resolve_data_dir({}, [tmp_path / "media"], tmp_path / "fb")
    assert path == tmp_path / "media" / "pi" / "USB1" / "tlbot-data"
    assert persistent is True and path.is_dir()


def test_fallback_not_persistent(tmp_path):
    path, persistent = resolve_data_dir({}, [tmp_path / "no-media"], tmp_path / "fb")
    assert path == tmp_path / "fb" and persistent is False and path.is_dir()


def test_skips_unwritable_usb(tmp_path, monkeypatch):
    import datadir
    bad = tmp_path / "media" / "pi" / "AAA"
    good = tmp_path / "media" / "pi" / "BBB"
    bad.mkdir(parents=True); good.mkdir(parents=True)
    real = datadir._writable
    monkeypatch.setattr(datadir, "_writable", lambda p: False if "AAA" in str(p) else real(p))
    path, _ = resolve_data_dir({}, [tmp_path / "media"], tmp_path / "fb")
    assert path == good / "tlbot-data"


def test_datadir_path_joins(tmp_path):
    d = DataDir(tmp_path, False)
    assert d.path("stats.db") == tmp_path / "stats.db" and d.persistent is False
