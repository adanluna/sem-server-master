from pathlib import Path


def size_kb(path: str | None) -> float:
    if not path:
        return 0.0
    try:
        p = Path(path)
        if p.exists():
            return round(p.stat().st_size / 1024, 2)
    except:
        pass
    return 0.0
