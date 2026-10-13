#!/usr/bin/env python3
"""Record a user's explicit completion/resolution statement without replacing their item."""
import argparse,json,sys,urllib.request
from ai_office_reminders import Site,ROOT
def main():
 p=argparse.ArgumentParser();p.add_argument('--id',required=True);p.add_argument('--evidence',required=True);p.add_argument('--dry-run',action='store_true');a=p.parse_args();site=Site();task=next((t for t in site.call()['tasks'] if t['id']==a.id),None)
 if not task or task['deleted']:raise RuntimeError('Task unavailable; do not create a replacement')
 if task['done']==1:print(json.dumps({'status':'already_resolved','id':a.id}));return
 body=dict(id=a.id,expectedUpdated=task['updated'],evidence=a.evidence)
 if a.dry_run:print(json.dumps({'dryRun':True,'id':a.id,'action':'mark_completed_or_resolved'}));return
 req=urllib.request.Request(site.config['site_url']+'/api/resolutions',headers=site.headers,data=json.dumps(body,ensure_ascii=False).encode())
 with site.opener.open(req,timeout=20) as response:result=json.load(response)
 current=next((t for t in site.call()['tasks'] if t['id']==a.id),None)
 if not result.get('success') or not current or current['done']!=1 or current['manual_override']!=1:raise RuntimeError('Explicit resolution readback not confirmed')
 print(json.dumps({'status':'success','id':a.id,'readbackVerified':True}))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'failed','errorType':type(e).__name__}));sys.exit(1)
