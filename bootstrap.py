#!/usr/bin/env python3
"""Prepare a new private installation. Never start services or register schedules."""
from pathlib import Path
import argparse,json,shutil,plistlib,sys
PACKAGE=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--root',default=str(Path.home()/'.codex/ai-office'))
p.add_argument('--wiki-root');p.add_argument('--docs-root');p.add_argument('--codex-root',default=str(Path.home()/'.codex'));p.add_argument('--history-root',default='');p.add_argument('--reminders-list-id',default='');p.add_argument('--node',default=shutil.which('node') or 'node');p.add_argument('--python',default=sys.executable);p.add_argument('--dry-run',action='store_true');a=p.parse_args()
root=Path(a.root).expanduser().resolve()
if root.exists():raise RuntimeError('Target already exists; preserve current data, use a new directory')
if a.dry_run:print(json.dumps({'root':str(root),'registered':False}));raise SystemExit
shutil.copytree(PACKAGE,root,ignore=shutil.ignore_patterns('.git','node_modules','dist','.wrangler','.dev.vars','.selfhost-owner.json','.sites-runtime','__pycache__','*.pyc','*.tsbuildinfo'))
for sub in ['work','outputs','launchd','automation','inputs/wiki/business/projects','inputs/wiki/business/companies','inputs/wiki/business/decisions','inputs/wiki/business/meetings','inputs/wiki/business/cases','inputs/wiki/system/memory/ops','inputs/documents']:(root/sub).mkdir(parents=True,exist_ok=True)
codex=Path(a.codex_root).expanduser();cfg={'site_url':'http://127.0.0.1:5199','codex_root':str(codex),'codex_db':str(codex/'state_5.sqlite'),'wiki_root':str(Path(a.wiki_root).expanduser()) if a.wiki_root else str(root/'inputs/wiki'),'wps_root':str(Path(a.docs_root).expanduser()) if a.docs_root else str(root/'inputs/documents'),'history_root':a.history_root,'reminders_list_id':a.reminders_list_id,'exclude_thread':'','proxy':'','local_service_file':str(root/'local-site/.selfhost-owner.json')}
(root/'config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n');(root/'config.json').chmod(0o600)
shutil.copy2(root/'docs/MODEL_TASK.md',root/'automation/prompt.md')
for label,args,extra in [('com.ai-office.local',[a.node,str(root/'local-site/scripts/run-selfhost.mjs')],{'KeepAlive':True,'WorkingDirectory':str(root/'local-site')}),('com.ai-office.sync',[a.python,str(root/'scripts/ai_office_sync.py')],{'StartInterval':1800,'ProcessType':'Background','WorkingDirectory':str(root)})]:
 data={'Label':label,'ProgramArguments':args,'RunAtLoad':True,'StandardOutPath':str(root/'work'/(label+'.stdout.log')),'StandardErrorPath':str(root/'work'/(label+'.stderr.log')),**extra}
 (root/'launchd'/(label+'.plist')).write_bytes(plistlib.dumps(data))
print(json.dumps({'prepared':str(root),'credentialsCreated':False,'servicesRegistered':False,'modelTaskRegistered':False}))
