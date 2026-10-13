#!/usr/bin/env python3
"""Owner-private, ID-based, completion-only Reminders reconciliation. No daemon."""
import argparse,datetime,fcntl,json,pathlib,re,subprocess,sys,tempfile,urllib.request,uuid
from ai_office_sync import clean
ROOT=pathlib.Path(__file__).resolve().parent.parent
SCRIPT=ROOT/'scripts/ai_office_reminders.jxa'
STATE=ROOT/'reminders-state.json'
APPROVED_LIST=json.loads((ROOT/'config.json').read_text()).get('reminders_list_id','')
SEED_BOARD=''
SEED_REMINDER=''
NAMESPACE=uuid.UUID('717ebf5b-b097-451a-9fb9-2b2216579c29')
UTC=datetime.timezone.utc
LOCAL=datetime.timezone(datetime.timedelta(hours=8))
class SyncError(RuntimeError):pass
def now():return datetime.datetime.now(UTC).isoformat().replace('+00:00','Z')
def atomic(path,data):
 with tempfile.NamedTemporaryFile('w',dir=path.parent,delete=False) as f:
  json.dump(data,f,ensure_ascii=False,indent=2);temp=pathlib.Path(f.name)
 temp.replace(path)
def permission():
 if not APPROVED_LIST:raise SyncError('approved_list_not_configured')
 # false means no OS permission request. A failure stops before Apple Events.
 code='import Foundation; import AppKit; import Carbon; let t=NSAppleEventDescriptor(bundleIdentifier:"com.apple.reminders"); print(AEDeterminePermissionToAutomateTarget(t.aeDesc,typeWildCard,typeWildCard,false))'
 r=subprocess.run(['/usr/bin/swift','-module-cache-path','/tmp/reminder-sync-module-cache','-e',code],capture_output=True,text=True,timeout=20)
 if not r.returncode and r.stdout.strip()=='-600':
  # Target is not running; launch without requesting or changing permissions.
  launch=subprocess.run(['/usr/bin/open','-g','-a','Reminders'],capture_output=True,text=True,timeout=10)
  if launch.returncode:raise SyncError('reminders_launch_failed')
  import time
  for _ in range(5):
   time.sleep(1)
   r=subprocess.run(['/usr/bin/swift','-module-cache-path','/tmp/reminder-sync-module-cache','-e',code],capture_output=True,text=True,timeout=20)
   if r.stdout.strip()!='-600':break
 if r.returncode:raise SyncError('automation_permission_probe_failed')
 if r.stdout.strip()=='-600':raise SyncError('reminders_not_running')
 if r.stdout.strip()!='0':raise SyncError('existing_automation_access_unavailable')
def native(op,data=None):
 d=dict(data or {});d['listId']=APPROVED_LIST
 path=None
 try:
  with tempfile.NamedTemporaryFile('w',dir=ROOT/'work',delete=False) as f:
   json.dump(d,f,ensure_ascii=False);path=pathlib.Path(f.name)
  r=subprocess.run(['/usr/bin/osascript','-l','JavaScript',str(SCRIPT),op,str(path)],capture_output=True,text=True,timeout=20)
  if r.returncode:raise SyncError('native_operation_not_confirmed_or_concurrent_edit')
  return json.loads(r.stdout)
 finally:
  if path:path.unlink(missing_ok=True)
class Site:
 def __init__(self):
  self.config=json.loads((ROOT/'config.json').read_text())
  if self.config.get('reminders_list_id') not in (None,APPROVED_LIST):raise SyncError('configured_list_not_approved')
  token=json.loads(pathlib.Path(self.config['local_service_file']).read_text())['serviceToken']
  self.headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Accept':'application/json'}
  self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':self.config.get('proxy',''),'https':self.config.get('proxy','')}))
 def call(self,data=None):
  req=urllib.request.Request(self.config['site_url']+'/api/reminders',headers=self.headers,data=json.dumps(data,ensure_ascii=False).encode() if data is not None else None)
  with self.opener.open(req,timeout=20) as response:return json.load(response)
def stamp(value):
 try:return datetime.datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
 except (ValueError,AttributeError):return 0
def direction(board,reminder,baseline=None):
 if board.get('deleted') or board['done']==2:return 'hold'
 bd=board['done'];rd=int(reminder['completed'])
 if bd not in (0,1):return 'hold'
 if bd==rd:return 'same'
 return 'to-reminder' if bd==1 else 'to-board'
def reminder_fields(r):
 due=r.get('dueDate') or r.get('alldayDueDate');date='';note=(r.get('body') or '').strip()
 if due:
  local=datetime.datetime.fromisoformat(due.replace('Z','+00:00')).astimezone(LOCAL)
  date=local.strftime('%Y-%m-%d');label='原提醒时间：'+local.strftime('%Y-%m-%d %H:%M')+'（Asia/Shanghai）' if r.get('dueDate') else '原提醒日期：'+date
  note+=('\n' if note else '')+label
 note+=('\n' if note else '')+'来源：macOS 提醒事项；原生 ID '+r['id']+'；清单 ID '+APPROVED_LIST
 return dict(title=clean(r['name'],200),due=date,note=clean(note,4000),done=int(r['completed']),priority='urgent' if r.get('priority') in (1,5) else 'normal')
def indexed(snapshot):
 if not isinstance(snapshot,dict) or not isinstance(snapshot.get('tasks'),list):raise SyncError('invalid_site_snapshot')
 ids=[t['id'] for t in snapshot['tasks']]
 if len(ids)!=len(set(ids)):raise SyncError('duplicate_site_ids')
 return {t['id']:t for t in snapshot['tasks']}
def native_index():
 lists=native('read')
 if not isinstance(lists,list):raise SyncError('invalid_native_snapshot')
 selected=[l for l in lists if l['id']==APPROVED_LIST]
 if len(selected)!=1:raise SyncError('approved_list_unavailable')
 rows=selected[0]['items'];ids=[r['id'] for r in rows]
 if len(ids)!=len(set(ids)):raise SyncError('duplicate_native_ids')
 return {r['id']:r for r in rows}
def excluded(t):return t.get('deleted') or t.get('done')==2 or t.get('title','').startswith('AI办公台同步验证·')
def reconcile(site,dry_run=False):
 state=json.loads(STATE.read_text()) if STATE.exists() else {'links':{}}
 if not isinstance(state.get('links'),dict):raise SyncError('invalid_sync_ledger')
 links=state['links'];rem=native_index();tasks=indexed(site.call());counts={'imported':0,'created':0,'toBoard':0,'toReminders':0,'matched':0};warnings=[];actions=[]
 state.setdefault('onboardedAt',now());state['schemaVersion']=2;state['calendarId']=APPROVED_LIST
 def save():
  if not dry_run:atomic(STATE,state)
 def link(bid,rid,proof):
  if bid in links and links[bid]['reminderId']!=rid:raise SyncError('conflicting_stable_link')
  if any(b!=bid and l['reminderId']==rid for b,l in links.items()):raise SyncError('duplicate_stable_link')
  links.setdefault(bid,{'reminderId':rid,'proof':proof});links[bid]['calendarId']=APPROVED_LIST;save()
 # Explicit human-authorized initial pair; never title matching.
 if SEED_BOARD in tasks:
  if SEED_REMINDER in rem:link(SEED_BOARD,SEED_REMINDER,'human_verified_initial_pair')
  elif SEED_BOARD not in links:warnings.append('已确认会议提醒原生ID暂不可用，保留办公台原项，不重复创建')
 for bid,l in links.items():
  if l.get('calendarId',APPROVED_LIST)!=APPROVED_LIST:raise SyncError('ledger_list_not_approved')
  l['calendarId']=APPROVED_LIST
 if len({l['reminderId'] for l in links.values()})!=len(links):raise SyncError('duplicate_stable_link')
 marker_prefix=site.config['site_url'].rstrip('/')+'/#task='
 marker_re=re.compile(re.escape(marker_prefix)+r'([0-9a-fA-F-]{36})(?=\s|$)')
 marked={}
 for rid,r in rem.items():
  for bid in set(marker_re.findall(r.get('body') or '')):marked.setdefault(bid,[]).append(rid)
 blocked=set()
 for bid,rids in marked.items():
  if bid not in tasks:continue
  if len(rids)!=1:
   warnings.append('多个提醒带同一来源ID，暂停关联：'+bid);blocked.add(bid);continue
  link(bid,rids[0],'unique_exact_source_id')
 known={l['reminderId'] for l in links.values()}
 # Recover deterministic imported IDs, including deletion tombstones, before import.
 for rid,r in rem.items():
  if rid in known:continue
  bid=str(uuid.uuid5(NAMESPACE,rid))
  if bid in tasks:link(bid,rid,'deterministic_native_id');known.add(rid)
 for rid,r in list(rem.items()):
  if rid in known or r.get('name','').startswith('AI办公台同步验证·'):continue
  if r['completed'] and stamp(r.get('creationDate'))<stamp(state['onboardedAt']):continue
  same=[t for t in tasks.values() if t.get('title','').strip()==r['name'].strip()]
  if same:
   blocked.update(t['id'] for t in same);warnings.append('同名事项未自动关联，需确认稳定ID：'+rid);continue
  bid=str(uuid.uuid5(NAMESPACE,rid));actions.append({'action':'import','siteId':bid,'reminderId':rid});counts['imported']+=1
  if dry_run:known.add(rid);continue
  payload=dict(action='import',id=bid,**reminder_fields(r))
  try:result=site.call(payload)
  except Exception:
   # Unknown write outcome: read back the same deterministic ID, never blind replay.
   tasks=indexed(site.call());t=tasks.get(bid)
   if not t:raise SyncError('unknown_import_outcome_not_retried')
   result={'success':True,'created':True}
  if not result.get('success'):raise SyncError('import_not_confirmed')
  tasks=indexed(site.call());t=tasks.get(bid)
  if not t:raise SyncError('import_readback_missing')
  if t.get('deleted'):counts['imported']-=1
  link(bid,rid,'deterministic_native_id');known.add(rid)
 for bid,t in list(tasks.items()):
  if excluded(t) or bid in blocked:continue
  if bid not in links:
   if t['done']!=0 or t.get('kind','task') not in ('task','tracking') or not t.get('remind',t.get('kind')=='task'):continue
   if bid==SEED_BOARD:continue
   collision=[r for rid,r in rem.items() if rid not in known and r['name'].strip()==t['title'].strip()]
   if collision:warnings.append('同名提醒未自动关联或创建，需确认稳定ID：'+bid);continue
   counts['created']+=1;actions.append({'action':'create','siteId':bid})
   if dry_run:continue
   marker=marker_prefix+bid;body=clean(t.get('note') or '',3000)+'\n\n来源：AI办公台\n'+marker
   try:r=native('create',dict(title=t['title'],body=body,due=t.get('due') or '',marker=marker,priority=1 if t.get('priority')=='urgent' else 0))
   except Exception:
    current=native_index();found=[x for x in current.values() if marker in (x.get('body') or '').splitlines()]
    if len(found)!=1:raise SyncError('unknown_native_create_outcome_not_retried')
    r=found[0]
   rem[r['id']]=r;link(bid,r['id'],'unique_exact_source_id');known.add(r['id'])
  l=links[bid];r=rem.get(l['reminderId'])
  if not r:warnings.append('关联提醒已移除，保留原状，不重建：'+bid);continue
  decision=direction(t,r,l)
  if decision=='to-board':
   counts['toBoard']+=1;actions.append({'action':'complete-board','siteId':bid,'reminderId':r['id']})
   if not dry_run:
    try:result=site.call(dict(action='status',id=bid,done=1,expectedUpdated=t['updated']))
    except Exception:
     current=indexed(site.call()).get(bid)
     if not current or current.get('deleted') or current['done']!=1:raise SyncError('unknown_completion_outcome_not_retried')
     result={'success':True,'task':current}
    if not result.get('success'):raise SyncError('board_completion_not_confirmed')
    t.update(result['task'])
  elif decision=='to-reminder':
   counts['toReminders']+=1;actions.append({'action':'complete-reminder','siteId':bid,'reminderId':r['id']})
   if not dry_run:
    try:r=native('status',dict(id=r['id'],completed=True,expectedCompleted=r['completed'],expectedModified=r.get('modificationDate')))
    except Exception:
     actual=native_index().get(r['id'])
     if not actual or not actual['completed']:raise SyncError('unknown_native_completion_outcome_not_retried')
     r=actual
  if not dry_run:l.update(boardDone=t['done'],reminderDone=int(r['completed']));save()
 result=dict(status='partial' if warnings else 'success',counts=counts,dryRun=dry_run,warnings=list(dict.fromkeys(warnings)),actions=actions,calendarId=APPROVED_LIST)
 summary='新增到看板 '+str(counts['imported'])+' 项，新增提醒 '+str(counts['created'])+' 项，完成状态同步 '+str(counts['toBoard']+counts['toReminders'])+' 项。';result['summary']=summary
 if not dry_run:
  actual_rem=native_index();actual_tasks=indexed(site.call());verified=[]
  for bid,l in links.items():
   t=actual_tasks.get(bid);r=actual_rem.get(l['reminderId'])
   if not t or excluded(t) or bid in blocked or not r:continue
   if t['done']!=int(r['completed']):raise SyncError('completion_readback_mismatch')
   l.update(boardDone=t['done'],reminderDone=int(r['completed']))
   verified.append({'siteId':bid,'reminderId':r['id'],'done':t['done']})
  state.update(lastAttemptAt=now(),lastWarnings=result['warnings'])
  if not warnings:state['lastSuccessAt']=state['lastAttemptAt']
  save();report=dict(action='report',status=result['status'],summary=summary+(' '+ '；'.join(result['warnings']) if warnings else ''),syncedAt=now())
  try:site.call(report)
  except Exception:pass
  if site.call().get('reminders',{}).get('syncedAt')!=report['syncedAt']:raise SyncError('report_readback_mismatch')
  result.update(readbackVerified=True,verifiedPairs=verified,syncedAt=report['syncedAt']);atomic(ROOT/'reminders-last-result.json',result)
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument('--dry-run',action='store_true');a=p.parse_args();lock=open(ROOT/'reminders.lock','a')
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:print(json.dumps({'status':'already_running'}));return 0
 try:
  permission();site=Site();result=reconcile(site,a.dry_run);print(json.dumps(result,ensure_ascii=False));return 0 if result['status']=='success' else 2
 except Exception as e:
  error=str(e) if isinstance(e,SyncError) else type(e).__name__
  result=dict(status='failed',time=now(),error=error)
  if not a.dry_run:atomic(ROOT/'reminders-last-attempt.json',result)
  print(json.dumps(result,ensure_ascii=False));return 1
if __name__=='__main__':sys.exit(main())
