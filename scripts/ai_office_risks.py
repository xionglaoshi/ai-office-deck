"""Read WIKI case, media and meeting bodies as risk candidates, not confirmed tasks."""
import datetime,pathlib,re
from ai_office_sources import files_under
SIGNAL=re.compile(r'风险|问题|争议|纠纷|仲裁|强制执行|未结案|未判决|待跟踪|待核|尚未|未解决|受阻|负面|舆情|停采|资金缺口|回款|举证')
CLOSED=re.compile(r'已撤诉|协商和解办结|已办结|结案归档')
def collect_risks(wiki,make_item,clean,now):
 root=pathlib.Path(wiki);result=[];errors=0;scanned=0
 paths=files_under(root/'business/cases')+files_under(root/'business/meetings')
 for path in paths:
  if CLOSED.search(path.stem):continue
  try:text=path.read_text()
  except (OSError,UnicodeError):errors+=1;continue
  status=re.search(r'^status:\s*["\']?([^\n"\']+)',text,re.M)
  if status and re.search(r'archived|deprecated|superseded|historical|closed',status[1],re.I):continue
  date=re.search(r'^updated:\s*["\']?(\d{4}-\d{2}-\d{2})',text,re.M);source_date=date[1] if date else '未标注'
  event=re.match(r'(\d{4}-\d{2}-\d{2})',path.name)
  if path.parent.name=='meetings':
   applicable=event[1] if event else source_date
   if applicable=='未标注' or applicable<(now-datetime.timedelta(days=90)).strftime('%Y-%m-%d'):continue
  scanned+=1;section='';groups={}
  for line_no,line in enumerate(text.splitlines(),1):
   if line.startswith('#'):section=line.strip('# ').strip()
   if not SIGNAL.search(line) or line.startswith(('title:','tags:','> 来源')) or CLOSED.search(line):continue
   # Full meaningful lines are retained; long evidence is not silently omitted.
   group='案件与舆情' if path.parent.name=='cases' else section
   groups.setdefault(group,[]).append((line_no,clean(line,12000)))
  for section,lines in list(groups.items()):
   if not lines:continue
   rel=str(path.relative_to(root));key='wiki-risk:'+rel+':'+section
   title=('案件/舆情线索：' if path.parent.name=='cases' else '会议问题线索：')+path.stem+((' · '+section) if path.parent.name=='meetings' else '')
   note='风险候选，不能直接认定现实仍有效；须核对当前进展、已判决/结案/解决证据与关联来源。\n来源口径日期：'+source_date+'\n原始位置：'+str(path)+':'+str(lines[0][0])+'\n正文线索：\n'+'\n'.join(str(n)+': '+line for n,line in lines)
   entry=make_item(key,title,'WIKI',path.stem,note);entry['subjectKey']=key;entry['sourcePath']=str(path);entry['sourceDate']=source_date;entry['excerptOnly']=len(note)>20000;result.append(entry)
 if scanned==0:raise ValueError('No readable applicable risk pages')
 return result,dict(name='WIKI问题与风险',status='error' if errors else 'success',count=len(result),message='案件、舆情及近90天会议正文；已读 '+str(scanned)+' 页，全部仅为待核对候选'+('；部分读取失败' if errors else ''))
