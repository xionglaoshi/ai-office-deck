#!/usr/bin/env python3
"""Output application artwork metadata only. Never launch apps or read app data."""
import json,pathlib,plistlib,sys
roots=[pathlib.Path('/Applications'),pathlib.Path.home()/'Applications',pathlib.Path('/System/Applications'),pathlib.Path('/System/Library/CoreServices')]
apps=[]
def visit(root,depth=0):
    if not root.is_dir() or depth>3:return
    try:entries=list(root.iterdir())
    except OSError:return
    for p in entries:
        if p.suffix=='.app':
            info=p/'Contents/Info.plist'
            if not info.is_file():continue
            try:d=plistlib.loads(info.read_bytes())
            except Exception:continue
            bid=d.get('CFBundleIdentifier','')
            if bid:apps.append({'id':bid,'name':d.get('CFBundleDisplayName') or d.get('CFBundleName') or p.stem,'path':str(p)})
        elif p.is_dir() and not p.name.startswith('.') and not p.is_symlink():visit(p,depth+1)
for root in roots:visit(root)
print(json.dumps(apps,ensure_ascii=False,indent=2))
