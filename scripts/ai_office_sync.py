#!/usr/bin/env python3
"""Read local work signals and synchronize the owner-private office Site.
No WIKI/WPS/session writes. Service credential is read from macOS Keychain.
"""
import argparse,datetime,hashlib,json,os,pathlib,re,sqlite3,subprocess,sys,urllib.request,uuid,fcntl
from ai_office_history import collect_history
from ai_office_risks import collect_risks
from ai_office_sources import files_under, collect_reports, collect_documents
ROOT=pathlib.Path(__file__).resolve().parent.parent
CONFIG=ROOT/'config.json'
TZ=datetime.timezone(datetime.timedelta(hours=8))
EXCLUDE=re.compile(r'凭证|密码|protected|credential|secret|token|备份|归档|历史|_archive',re.I)
NAMESPACE=uuid.UUID('d10f6e54-7d95-48c0-bc50-8520b870689e')
def clean(value,limit=1000):
 value=re.sub(r'<oai-mem-citation>[\s\S]*?</oai-mem-citation>','',value)
 value=re.sub(r'```([A-Za-z0-9_-]*)\s*\n([\s\S]*?)```',lambda m:m[2] if m[1] in ('json','text') else '[代码省略]',value)
 value=re.sub(r':::?codex[^\n]*','',value)
 value=re.sub(r'(?:sk-[A-Za-z0-9_-]{15,}|Bearer\s+[A-Za-z0-9._-]{15,})','[已隐藏]',value)
 value=re.sub(r'(?im)^.*(?:api[_ -]?key|access[_ -]?token|password|密码|凭证)\s*[:=：].*$','[敏感行省略]',value)
 return value.strip()[:limit]
def item(key,title,source,project,note,kind='attention',due='',url=''):
 return dict(id=str(uuid.uuid5(NAMESPACE,key)),title=clean(title,200),kind=kind,priority='normal',due=due,project=clean(project,100),note=clean(note,20000),source=source,url=url,sourceVersion=hashlib.sha256(clean(note,20000).encode()).hexdigest(),excerptOnly=len(note)>20000)
def latest_text(path):
 # Bound memory for long transcripts; final messages are near the tail.
 with open(path,'rb') as f:
  f.seek(0,2);size=f.tell();f.seek(max(0,size-1500000));raw=f.read().decode('utf-8',errors='replace')
 messages=[];completed=False
 for line in raw.splitlines():
  try:d=json.loads(line)
  except ValueError:continue
  p=d.get('payload',{})
  if d.get('type')=='response_item' and p.get('type')=='message':
   if p.get('role')=='user':messages=[];completed=False
   if p.get('role')=='assistant':messages.append(''.join(x.get('text','') for x in p.get('content',[]) if x.get('type') in ('output_text','text')))
  if d.get('type')=='event_msg' and p.get('type')=='task_complete':completed=True
 return clean(messages[-1],20000) if messages and completed else '',completed

def collect(config):
 now=datetime.datetime.now(TZ);cutoff=(now-datetime.timedelta(days=14)).timestamp();items=[];activity=[];sources=[]
 titles={}
 try:
  for line in pathlib.Path(config['codex_root'],'session_index.jsonl').read_text().splitlines():
   try:d=json.loads(line);titles[d['id']]=d.get('thread_name') or d.get('title') or ''
   except (ValueError,KeyError):pass
 except OSError:pass
 try:
  connection=sqlite3.connect('file:'+str(pathlib.Path(config.get('codex_db') or str(pathlib.Path(config['codex_root'],'state_5.sqlite'))))+'?mode=ro',uri=True)
  rows=connection.execute('SELECT id,title,rollout_path,updated_at FROM threads WHERE archived=0 AND updated_at>=? AND (agent_path IS NULL OR agent_path="/root") ORDER BY updated_at DESC',(cutoff,)).fetchall();connection.close();n=0;read_errors=0
  for tid,title,path,updated in rows:
   title=titles.get(tid) or (title or '未命名会话').splitlines()[0]
   if tid==config.get('exclude_thread','') or EXCLUDE.search(title) or title.startswith('Automation:'):continue
   try:summary,completed=latest_text(path)
   except OSError:read_errors+=1;continue
   title=clean(title,100);n+=1
   activity.append(dict(title=title,source='Codex',path='Codex 会话 '+tid,updated=datetime.datetime.fromtimestamp(updated,TZ).isoformat(),summary=clean(summary,20000) or '最近有会话活动，尚无本轮完成汇报。'))
   signals=[line.strip(' -*#\t') for line in summary.splitlines() if re.search(r'尚未|仍未|未完成|未解决|待.{0,15}验收|待.{0,15}绑定|需要你|请你|失败|阻塞',line) and not re.search(r'无需|不需要|并非|不是|已修复|已解决',line)]
   if signals:items.append(item('codex:'+tid,'待核对：'+title,'Codex',title,'最近会话的未解决线索（需结合原会话确认）：\n'+'\n'.join(signals)+'\n原始会话：'+tid))
  sources.append(dict(name='Codex',status='error' if read_errors else 'success',count=n,message='近14天会话；'+('部分会话无法读取' if read_errors else '未解决表述作为待核对线索')))
 except Exception as e:sources.append(dict(name='Codex',status='error',count=0,message='本机会话读取失败：'+type(e).__name__))
 try:
  wiki=pathlib.Path(config['wiki_root']);assert wiki.is_dir();count=0;read_errors=0;files_read=0
  for folder in ('projects','companies','decisions','meetings'):
   root=wiki/folder
   if not root.is_dir():raise FileNotFoundError('Expected WIKI section missing')
   for path in files_under(root):
    if EXCLUDE.search(str(path.relative_to(wiki))):continue
    try:text=path.read_text();stat=path.stat();files_read+=1
    except (OSError,UnicodeError):read_errors+=1;continue
    status=re.search(r'^status:\s*["\']?([^\n"\']+)',text,re.M)
    if status and re.search(r'archived|deprecated|superseded|historical|closed',status.group(1),re.I):continue
    heading=re.search(r'^#\s+(.+)',text,re.M);title=heading.group(1) if heading else path.parent.name if path.stem=='README' else path.stem
    date=re.search(r'^updated:\s*["\']?(\d{4}-\d{2}-\d{2})',text,re.M);verified_date=date.group(1) if date else '未标注';section='';seen=0
    for lineno,line in enumerate(text.splitlines(),1):
     if line.startswith('#'):section=line.strip('# ').strip()
     m=re.match(r'^\s*[-*]\s+\[ \]\s+(.+)',line)
     if not m or EXCLUDE.search(m.group(1)):continue
     content=clean(m.group(1),12000)
     if len(content)<4:continue
     key='wiki:'+str(path.relative_to(wiki))+':'+content
     note='WIKI 未勾选事项；是否仍有效、由谁处理需核对。\n原文：'+content+'\n所属章节：'+section+'\n来源口径日期：'+verified_date+'（文件修改时间不代表业务状态已确认）\n原始位置：'+str(path)+':'+str(lineno)
     items.append(item(key,'核对：'+content,'WIKI',title,note));count+=1;seen+=1

    if seen:activity.append(dict(title=title,source='WIKI',path=str(path),updated=(verified_date+'T00:00:00+08:00') if date else datetime.datetime.fromtimestamp(stat.st_mtime,TZ).isoformat(),summary='提取 '+str(seen)+' 条未勾选线索；口径日期 '+verified_date+'，尚未确认当前业务状态。'))
  if files_read==0:raise ValueError('No WIKI files read')
  sources.append(dict(name='WIKI',filesRead=files_read,status='error' if read_errors else 'success',count=count,message='项目、公司、决定、会议中的未勾选线索；'+('部分文件读取失败' if read_errors else '历史口径需核对')))
 except Exception as e:sources.append(dict(name='WIKI',status='error',count=0,message='WIKI读取失败：'+type(e).__name__))
 try:
  wps=pathlib.Path(config['wps_root']);assert wps.is_dir();files=[]
  for root,dirs,names in os.walk(wps,onerror=lambda error: (_ for _ in ()).throw(error)):
   dirs[:]=[d for d in dirs if d!='WIKI' and not d.startswith('.') and not EXCLUDE.search(d)]
   for name in names:
    p=pathlib.Path(root,name)
    if p.suffix.lower() not in ('.docx','.xlsx','.pptx','.md','.pdf') or EXCLUDE.search(name) or name.startswith('~$'):continue
    try:modified=p.stat().st_mtime
    except OSError:continue
    if modified>=cutoff:files.append((modified,p))
  files.sort(key=lambda x:x[0],reverse=True)
  for modified,p in files:activity.append(dict(title=clean(p.stem,200),source='WPS',path=str(p),updated=datetime.datetime.fromtimestamp(modified,TZ).isoformat(),summary='仅文件元数据；未读取正文，不代表云端最新版或新增工作。'))
  if not files:raise ValueError('No recent local metadata; coverage must be checked')
  sources.append(dict(name='WPS',status='success',count=len(files),filesRead=len(files),message='近14天文件元数据；未读正文；实时工作邮件未接入'))
 except Exception as e:sources.append(dict(name='WPS',status='error',count=0,message='WPS材料读取失败：'+type(e).__name__))
 try:
  risks,risk_source=collect_risks(config['wiki_root'],item,clean,now);items.extend(risks);sources.append(risk_source)
 except Exception as e:sources.append(dict(name='WIKI问题与风险',status='error',count=0,message='风险正文读取失败：'+type(e).__name__))
 # All candidates remain normal priority with no invented deadlines.
 for entry in items:
  entry['sourceGroup']='WIKI问题与风险' if entry.get('subjectKey','').startswith('wiki-risk:') else entry['source']
 # Source modules are read-only. Never authenticate or fetch live mail here.
 additions=[('WIKI日报',lambda:collect_reports(config['wiki_root'],item,clean,now)),
 ('WIKI部署与关注',lambda:collect_documents(pathlib.Path(config['wiki_root']),tuple(config.get('focus_folders',['meetings','assistant-notes'])),'WIKI部署与关注',item,clean,now,days=90)),
 ('WIKI研究',lambda:collect_documents(pathlib.Path(config['wiki_root']),('reports','industry'),'WIKI研究',item,clean,now,days=30,signal=r'舆情|负面|行业|调研|研究|趋势')),
 ('WIKI邮件',lambda:collect_documents(pathlib.Path(config['wiki_root']),('wecom/mail',),'WIKI邮件',item,clean,now,days=30))]
 for name,reader in additions:
  try:
   found,status=reader();items.extend(found);sources.append(status)
  except Exception as error:
   sources.append(dict(name=name,status='error',count=0,complete=False,message='正文覆盖未确认：'+type(error).__name__+'；服务保留上次有效候选，不代表没有事项'))
 for status in sources:status.setdefault('complete',status['status']=='success')
 activity=sorted(activity,key=lambda x:x['updated'],reverse=True)
 payload=dict(items=items,sources=sources,activity=activity,collectedAt=now.astimezone(datetime.timezone.utc).isoformat().replace('+00:00','Z'))
 try:
  payload['computerHistory'],history_source=collect_history(clean,now);sources.append(history_source)
 except Exception as e:sources.append(dict(name='电脑历史记录',status='error',count=0,message='电脑历史摘要读取失败：'+type(e).__name__+'；保留上次记录'))
 return payload

def send(config,payload):
 token=json.loads(pathlib.Path(config['local_service_file']).read_text())['serviceToken'];url=config['site_url']+'/api/sync';headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Accept':'application/json'}
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':config.get('proxy',''),'https':config.get('proxy','')}))
 request=urllib.request.Request(url,data=json.dumps(payload,ensure_ascii=False).encode(),headers=headers,method='POST')
 with opener.open(request,timeout=45) as response:result=json.load(response)
 if not result.get('success'):raise RuntimeError('Site did not confirm synchronization')
 with opener.open(urllib.request.Request(url,headers=headers),timeout=45) as response:readback=json.load(response)
 if readback.get('sync',{}).get('updated')!=payload['collectedAt']:raise RuntimeError('Synchronization readback mismatch')
 ids={x['id'] for x in readback.get('sync',{}).get('candidates',[])}
 if any(x['id'] not in ids for x in payload['items']):raise RuntimeError('Synchronized item missing')
 if 'computerHistory' in payload and readback.get('sync',{}).get('computerHistory')!=payload['computerHistory']:raise RuntimeError('Computer History readback mismatch')
 return dict(updated=payload['collectedAt'],received=readback['sync']['received'],sources=readback['sync']['sources'],coverageComplete=readback['sync'].get('coverageComplete',False),readbackVerified=True)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--collect-only',action='store_true');parser.add_argument('--dry-run',action='store_true');args=parser.parse_args();config=json.loads(CONFIG.read_text())
 if args.dry_run:
  payload=collect(config);print(json.dumps({'dry_run':True,'target':config['site_url']+'/api/sync','items':len(payload['items']),'activity':len(payload['activity']),'sources':payload['sources']},ensure_ascii=False));return 0
 ROOT.mkdir(exist_ok=True)
 lock=open(ROOT/'sync.lock','a');
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:return 0
 payload=collect(config)
 if args.collect_only:print(json.dumps(payload,ensure_ascii=False));return 0
 try:result=send(config,payload)
 except Exception as e:
  # No response bodies, transcript text, request headers, or credentials in logs.
  status={'status':'failed','time':datetime.datetime.now(TZ).isoformat(),'errorType':type(e).__name__};(ROOT/'last-attempt.json').write_text(json.dumps(status));print(json.dumps(status));return 1
 (ROOT/'last-success.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));status={'status':'success' if result.get('coverageComplete') else 'partial','time':datetime.datetime.now(TZ).isoformat(),'updated':result['updated'],'received':result['received'],'coverageComplete':result.get('coverageComplete',False),'readbackVerified':True};(ROOT/'last-attempt.json').write_text(json.dumps(status));print(json.dumps(status));return 0
if __name__=='__main__':sys.exit(main())
