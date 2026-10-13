"""Local evidence collectors. No network, credentials, source writes or OCR."""
import datetime, hashlib, html, json, os, pathlib, re

EXCLUDE = re.compile(r'凭证|密码|protected|credential|secret|token|备份|归档|_archive', re.I)
CLOSED = re.compile(r'archived|deprecated|superseded|historical|closed', re.I)

def files_under(root, suffix='.md'):
    root = pathlib.Path(root)
    if not root.is_dir():
        raise FileNotFoundError('Expected source directory unavailable')
    result = []
    def visit(folder):
        with os.scandir(folder) as entries:
            for entry in entries:
                if entry.name.startswith('.') or EXCLUDE.search(entry.name):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    visit(entry.path)
                elif entry.is_file() and entry.name.endswith(suffix):
                    result.append(pathlib.Path(entry.path))
    visit(root)
    if not result:
        raise ValueError('Source directory is readable but contains no eligible files; coverage unconfirmed')
    return sorted(result)

def date_of(text):
    m = re.search(r'^updated:\s*["\']?(\d{4}-\d{2}-\d{2})', text, re.M)
    return m[1] if m else ''

def active(text):
    m = re.search(r'^status:\s*["\']?([^\n"\']+)', text, re.M)
    return not m or not CLOSED.search(m[1])

def chunks(text, size=12000):
    """All chunks are retained; a long source never silently disappears."""
    lines=text.splitlines(keepends=True); buffer=''
    for line in lines:
        while len(line)>size:
            if buffer: yield buffer; buffer=''
            yield line[:size]; line=line[size:]
        if len(buffer)+len(line)>size:
            yield buffer; buffer=''
        buffer+=line
    if buffer: yield buffer

def source_item(make_item, key, title, body, group, path, date='', reporter='', **metadata):
    item=make_item(key,title,group,title,body)
    item.update(sourceGroup=group,sourcePath=str(path),sourceDate=date,reporter=reporter,
                sourceVersion=hashlib.sha256(body.encode()).hexdigest(),**metadata)
    return item

def collect_reports(wiki, make_item, clean, now):
    group='WIKI日报'; root=pathlib.Path(wiki)/'wecom/report'; paths=files_under(root)
    items=[]; seen=set(); people=set(); comments=0; images=0; pages=0; total=0
    cutoff=(now-datetime.timedelta(days=21)).timestamp()
    for path in paths:
        # Parse every readable partition, then filter using the report's original time.
        text=path.read_text(); pages+=1
        for block in re.finditer(r'```json\s*\n([\s\S]*?)\n```',text):
            payload=json.loads(block[1]); rows=payload if isinstance(payload,list) else payload.get('reports',payload.get('items',[]))
            if not isinstance(rows,list): raise ValueError('Unsupported report envelope')
            for row in rows:
                if not isinstance(row,dict) or not row.get('journal_uuid'):continue
                total+=1
                if float(row.get('report_time',0))<cutoff:continue
                rid=row['journal_uuid']
                if rid in seen:continue
                seen.add(rid); reporter=row.get('submitter',{}).get('userid','未标注');people.add(reporter)
                date=datetime.datetime.fromtimestamp(row['report_time'],now.tzinfo).isoformat()
                sections=[]
                for field in row.get('apply_data',{}).get('contents',[]):
                    label=' / '.join(x.get('text','') for x in field.get('title',[]))
                    value=field.get('value',{}); body=html.unescape(re.sub(r'<[^>]*>','\n',value.get('text','')))
                    sections.append(label+'：\n'+body.strip())
                    images+=len(value.get('files',[]))+len(re.findall(r'<img\b',value.get('text','')))
                comm=row.get('comments',[]);comments+=len(comm)
                for comment in comm:
                    stamp=comment.get('comment_time'); who=comment.get('userid') or comment.get('comment_userinfo',{}).get('userid') or comment.get('commenter',{})
                    body=comment.get('content') or comment.get('comment') or comment.get('text') or ''
                    if isinstance(body,(dict,list)):body=json.dumps(body,ensure_ascii=False)
                    sections.append('评论（'+str(who)+'；原始时间 '+str(stamp)+'）：'+html.unescape(re.sub(r'<[^>]*>',' ',str(body))))
                body='员工来源自述，未核实为实际完成；不得把员工日常计划全部转为用户待办。\n报告人：'+reporter+'\n原始报告时间：'+date+'\n日报原始ID：'+rid+'\n来源：'+str(path)+'\n'+'\n\n'.join(sections)
                for i,part in enumerate(chunks(body)):
                    items.append(source_item(make_item,'report:'+rid+':'+str(i),row.get('template_name','员工日报')+' · '+reporter+' · '+date[:10],clean(part,20000),group,path,date,reporter,recordId=rid,part=i,evidenceType='reported'))
    if not seen:raise ValueError('No reports in the authorized recent time window')
    return items,dict(name=group,status='success',count=len(seen),complete=True,filesRead=pages,recordsRead=total,people=len(people),comments=comments,imagesNotRead=images,message='已读全部可见分片；近21天 '+str(len(seen))+' 条、'+str(len(people))+' 人、'+str(comments)+' 评论；附件 '+str(images)+' 个未OCR，仅文本覆盖')

def collect_documents(wiki, folders, group, make_item, clean, now, days=None, signal=None):
    items=[]; pages=0; eligible=0; missing=[]
    for folder in folders:
        root=pathlib.Path(wiki)/folder
        try:paths=files_under(root)
        except FileNotFoundError:missing.append(folder);continue
        for path in paths:
            text=path.read_text();pages+=1
            if not active(text):continue
            date=date_of(text)
            event=re.match(r'(\d{4}-\d{2}-\d{2})',path.name)
            applicable=event[1] if event else date
            if days and applicable and applicable<(now-datetime.timedelta(days=days)).strftime('%Y-%m-%d'):continue
            if signal and not re.search(signal,text):continue
            eligible+=1; rel=str(path.relative_to(wiki)); title=re.search(r'^#\s+(.+)',text,re.M)
            title=title[1] if title else path.stem
            body='来源口径日期：'+(applicable or '未标注')+'；mtime不是业务日期。\n原始位置：'+str(path)+'\n'+text
            for i,part in enumerate(chunks(body)):
                items.append(source_item(make_item,'document:'+rel+':'+str(i),title,clean(part,20000),group,path,applicable,part=i,evidenceType='reported' if group=='WIKI邮件' else 'document'))
    if not pages:raise ValueError('No readable source documents')
    return items,dict(name=group,status='error' if missing or group=='WIKI邮件' and not eligible else 'success',count=eligible,complete=not missing and not (group=='WIKI邮件' and not eligible),filesRead=pages,message='已读 '+str(pages)+' 页；适用正文 '+str(eligible)+' 页'+('；缺目录 '+','.join(missing) if missing else '')+('；仅WIKI已落地邮件，不代表实时邮箱覆盖' if group=='WIKI邮件' else ''))
