"""Read Codex Computer History presentation summaries; never upload raw events."""
import datetime, json, pathlib, re

CONFIG=pathlib.Path(__file__).resolve().parent.parent/'config.json'
UTC=datetime.timezone.utc
SYSTEM_APPS={'com.apple.dock','com.apple.dock.helper','com.apple.notificationcenterui','com.apple.UserNotificationCenter','com.apple.SecurityAgent','com.apple.loginwindow','com.apple.coreservices.uiagent','com.apple.campo'}

def field(frontmatter,name):
 match=re.search(r'^'+name+r':\s*(.*)$',frontmatter,re.M)
 if not match:return ''
 value=match[1].strip()
 if value.startswith('"'):
  try:return json.loads(value)
  except ValueError:raise ValueError('Invalid history presentation field')
 if value.startswith("'") and value.endswith("'"):return value[1:-1].replace("''", "'")
 if value in ('|','>','|-','>-'):
  tail=frontmatter[match.end():];lines=[]
  for line in tail.splitlines():
   if not line:continue
   if not line.startswith(' '):break
   lines.append(line.strip())
  return ' '.join(lines)
 return value

def collect_history(clean,now=None):
 now=now or datetime.datetime.now(UTC)
 cutoff=now-datetime.timedelta(days=30)
 resource=json.loads(CONFIG.read_text()).get('history_root')
 if not resource:raise FileNotFoundError('Computer History not configured')
 RESOURCES=pathlib.Path(resource).expanduser()
 if not RESOURCES.is_dir():raise FileNotFoundError('Computer History summaries unavailable')
 entries={}; latest=None
 for path in sorted(RESOURCES.glob('*-10min-*.md')):
  match=re.match(r'^(\d{4}-\d{2}-\d{2})T(\d{2})-(\d{2})-(\d{2})-',path.name)
  if not match:continue
  start=datetime.datetime.fromisoformat(match[1]+'T'+':'.join(match.group(2,3,4))+'+00:00')
  if start<cutoff or start>now:continue
  text=path.read_text();front=re.match(r'^---\s*\n([\s\S]*?)\n---(?:\n|$)',text)
  if not front:raise ValueError('Computer History presentation metadata missing')
  title=field(front[1],'title');description=field(front[1],'description')
  if not title or not description:raise ValueError('Computer History title or summary missing')
  apps=field(front[1],'applications')
  if not apps.startswith('[') or not apps.endswith(']'):raise ValueError('Computer History app list invalid')
  app_ids=[]
  for value in apps[1:-1].split(','):
   bid=value.strip().strip('"\'')
   if not bid or bid in SYSTEM_APPS or 'Service' in bid or 'Extension' in bid or '.helper' in bid:continue
   if re.fullmatch(r'[A-Za-z0-9_.-]{1,150}',bid) and bid not in app_ids:app_ids.append(bid)
  iso=start.isoformat().replace('+00:00','Z')
  # Segment identity is stable across regenerated summaries; 6h summaries overlap and are excluded.
  entries[iso]=dict(id='computer-history:'+iso,title=clean(title,200),summary=clean(description,2000),startedAt=iso,endedAt=(start+datetime.timedelta(minutes=10)).isoformat().replace('+00:00','Z'),applications=app_ids[:20])
  latest=max(latest or start,start)
 result=sorted(entries.values(),key=lambda x:x['startedAt'],reverse=True)
 if len(result)>4000:raise ValueError('Computer History limit exceeded')
 if not result:raise ValueError('No recent Computer History summaries')
 return result,dict(name='电脑历史记录',status='success',count=len(result),message='Codex真实10分钟摘要，近30天；最近记录 '+latest.astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime('%m-%d %H:%M'))
