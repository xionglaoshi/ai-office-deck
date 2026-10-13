#!/usr/bin/env python3
"""Advance model review checkpoint only after saved curation and Reminders readback."""
import hashlib,json,pathlib,subprocess,sys
from ai_office_reminders import ROOT,Site,atomic,stamp
def main():
 result=subprocess.run(['/usr/bin/python3',str(ROOT/'scripts/ai_office_access.py'),'read'],capture_output=True,text=True,timeout=60)
 if result.returncode:raise RuntimeError('Board readback unavailable')
 data=json.loads(result.stdout);curated=data.get('curated') or {};native=Site().call().get('reminders') or {};last=json.loads((ROOT/'reminders-last-result.json').read_text())
 if curated.get('coverageComplete') is False or not curated.get('updated') or native.get('status')!='success' or not last.get('readbackVerified') or last.get('status')!='success' or stamp(native.get('syncedAt'))<stamp(curated['updated']):raise RuntimeError('Full successful review and synchronization not confirmed')
 previous=ROOT/'model-review-checkpoint.json'
 old=json.loads(previous.read_text()) if previous.exists() else {}
 if stamp(old.get('reviewedThrough'))>=stamp(curated['updated']):print(json.dumps({'status':'unchanged'}));return
 value={'reviewedThrough':curated['updated'],'snapshotAt':curated.get('snapshotAt'),'remindersSyncedAt':native['syncedAt'],'taskIds':[t['id'] for t in data.get('items',[]) if not t.get('deleted')],'sourceIdsDigest':hashlib.sha256(json.dumps(sorted(t['id'] for t in data.get('sync',{}).get('candidates',[]))).encode()).hexdigest()}
 atomic(previous,value);print(json.dumps({'status':'success','reviewedThrough':value['reviewedThrough']}))
if __name__=='__main__':
 try:main()
 except Exception as e:print(json.dumps({'status':'failed','errorType':type(e).__name__}));sys.exit(1)
