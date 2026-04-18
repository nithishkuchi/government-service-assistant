# Run this to diagnose what's in your knowledge_base folder
# python scripts/diagnose.py

import os
from pathlib import Path

KB = Path("knowledge_base")

if not KB.exists():
    print("ERROR: knowledge_base/ folder not found!")
    print(f"Current directory: {os.getcwd()}")
else:
    print(f"knowledge_base/ found at: {KB.absolute()}")
    print()
    folders = [f for f in KB.iterdir() if f.is_dir()]
    print(f"Found {len(folders)} service folders:")
    for folder in sorted(folders):
        print(f"\n  [{folder.name}]")
        for fname in ["full_guide.txt", "faq.txt", "voice_points.txt", "embeddings.json"]:
            fpath = folder / fname
            if fpath.exists():
                size = fpath.stat().st_size
                print(f"    ✅ {fname} ({size} bytes)")
            else:
                print(f"    ❌ {fname} MISSING")