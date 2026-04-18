import shutil
from pathlib import Path

kb = Path('knowledge_base')
deleted = 0
kept = 0
for svc in kb.iterdir():
    if not svc.is_dir():
        continue
    t_dir = svc / 'translations'
    if t_dir.exists():
        for lang in t_dir.iterdir():
            if lang.is_dir():
                files = list(lang.glob('*'))
                if not files:
                    shutil.rmtree(lang)
                    deleted += 1
                else:
                    kept += 1

print(f"Cleanup complete. Deleted {deleted} empty folders. Kept {kept} translated folders.")
