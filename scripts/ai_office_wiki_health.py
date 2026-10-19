#!/usr/bin/python3
# coding: utf-8
"""Read existing authorized ops reports and publish a private dashboard snapshot; no WIKI writes."""
import datetime,hashlib,json,pathlib,re,urllib.request,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def versions(wiki):
 paths=sorted((wiki/'system/memory/ops').glob('????-??-??-知识库每日优化.md'))
 if not paths:raise RuntimeError('No readable ops reports')
 report=paths[-1];raw=report.read_text();mp=pathlib.Path(json.loads((ROOT/'config.json').read_text()).get('wiki_metrics_file',str(pathlib.Path.home()/'.codex/workspace/wiki-daily-reports/quality-metrics-latest.json')));mraw=mp.read_text()
 return report,raw,json.loads(mraw),{str(report.relative_to(wiki)):hashlib.sha256(raw.encode()).hexdigest(),str(mp):hashlib.sha256(mraw.encode()).hexdigest()}
def publish():
 c=json.loads((ROOT/'config.json').read_text());wiki=pathlib.Path(c['wiki_root']);report,text,metrics,hashes=versions(wiki);sys.path.insert(0,str(ROOT/'scripts'));from wiki_quality_audit import parse_ledger
 ledger=wiki/'质量审计日志.md'
 if not ledger.is_file():raise RuntimeError('根质量审计台账缺失，拒绝使用旧缓存代替正本')
 active,_=parse_ledger(ledger);review=dict(issues=active['issues'],reviewedAt=datetime.datetime.fromtimestamp(ledger.stat().st_mtime,datetime.timezone.utc).isoformat(),coverageGap='问题来自WIKI根质量审计日志；日报仅作为证据。尚未执行全库事实时效核验，未核附件、流水或受限原文；问题数不等于受影响页面去重数。');gaps=[]
 hashes['质量审计日志.md']=hashlib.sha256(ledger.read_bytes()).hexdigest()
 for issue in review['issues']:
  for rel in issue['pages']:
   if rel.startswith(('credentials/','restricted/')):continue
   p=wiki/rel
   try:hashes[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
   except OSError:gaps.append('相关页面未读到：'+rel)
 stale=any(expected!=hashes.get(rel) for issue in review['issues'] for rel,expected in issue.get('sourceVersions',{}).items())
 count=re.search(r'\*\*知识库规模\*\*：([\d,]+)',text);total=int(count.group(1).replace(',','')) if count else None;ms=metrics.get('metrics',{});orphan=ms.get('orphan_pages');dead=ms.get('dead_links')
 stamp=datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00','Z')
 data=dict(updated=stamp,reportDate=metrics.get('date','未提供'),reviewedAt=review['reviewedAt'],reviewStale=stale,summary='WIKI共'+(str(total)+'页' if total is not None else'页数未核实')+'；核心口径孤儿页'+str(orphan if orphan is not None else'未核实')+'、断链'+str(dead if dead is not None else'未核实')+'处；下列'+str(len(review['issues']))+'项未解决问题（待用户澄清'+str(sum(i['category']=='clarification' for i in review['issues']))+'项、库质量'+str(sum(i['category']=='quality' for i in review['issues']))+'项）。',metrics=dict(totalPages=total,**ms),issues=[{k:v for k,v in i.items() if k in {'id','category','title','problem','decisionNeeded','type','pages','evidence'}}|{'type':i.get('type','待澄清' if i['category']=='clarification' else '库质量')} for i in review['issues']],coverageGap=review['coverageGap']+'；'+('；'.join(gaps) if gaps else '本次仅刷新既有报告统计及页面指纹，未重新执行全库体检。'),sourceVersions=hashes)
 (ROOT/'work/wiki-health-snapshot.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 token=json.loads(pathlib.Path(c['local_service_file']).read_text())['serviceToken'];op=urllib.request.build_opener(urllib.request.ProxyHandler({'http':c.get('proxy',''),'https':c.get('proxy','')}));url=c['site_url']+'/api/wiki-health';headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
 result=json.load(op.open(urllib.request.Request(url,data=json.dumps(data,ensure_ascii=False).encode(),headers=headers),timeout=30));assert result.get('success')
 saved=json.load(op.open(urllib.request.Request(url,headers=headers),timeout=30));assert saved['health']==data
 return dict(success=True,readbackVerified=True,issues=len(review['issues']),reviewStale=stale)
if __name__=='__main__':print(json.dumps(publish(),ensure_ascii=False))
