'use client';
import {useRef,useState} from 'react';
import {ChevronDown,ChevronLeft,ChevronRight,Clock} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {historyPage} from '@/lib/history-pages';
import {Collapsible,CollapsibleTrigger,CollapsibleContent} from '@/components/ui/collapsible';
import ApplicationIcon from './application-icon';
import {hourlyHistory,type HistoryEntry,type HourEntry} from '@/lib/hourly-history';
export type {HistoryEntry} from '@/lib/hourly-history';

function dateKey(value:string){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(value));}
function time(value:string){return new Date(value).toLocaleTimeString('zh-CN',{timeZone:'Asia/Shanghai',hour:'2-digit',minute:'2-digit'});}
export default function ComputerHistory({entries,status,activity=[]}:{entries:HistoryEntry[];status?:{status:string;message:string};activity?:{title:string;source:string;path:string;updated:string;summary:string}[]}){
 const [page,setPage]=useState(0),sectionRef=useRef<HTMLElement>(null);
 const sourceEntries=activity.filter(a=>['Codex','WPS'].includes(a.source)&&Number.isFinite(Date.parse(a.updated))).map(a=>({id:'activity:'+a.source+':'+a.path+':'+a.updated,title:a.source+' · '+a.title,summary:a.source+'会话/材料更新：'+a.summary+'（更新时间不代表业务完成时间）',startedAt:new Date(a.updated).toISOString(),endedAt:new Date(Date.parse(a.updated)+1).toISOString(),applications:[]}));
 const grouped=hourlyHistory([...entries,...sourceEntries]);
 const current=historyPage(grouped,page);
 const pageOriginals=new Set(current.entries.flatMap(entry=>entry.originals.map(original=>original.id)));
 const days=new Map<string,HourEntry[]>();
 for(const entry of [...current.entries].sort((a,b)=>b.startedAt.localeCompare(a.startedAt))){const key=dateKey(entry.startedAt);days.set(key,[...(days.get(key)||[]),entry]);}
 const today=dateKey(new Date().toISOString()),yesterday=dateKey(new Date(Date.now()-86400000).toISOString());
 const latest=entries.length?entries.reduce((a,b)=>a.startedAt>b.startedAt?a:b):null;
 const delayed=latest&&Date.now()-Date.parse(latest.endedAt)>90*60000;
 function changePage(next:number){setPage(next);requestAnimationFrame(()=>sectionRef.current?.scrollIntoView({block:'start'}));}
 return <section ref={sectionRef} className="panel computer-history" aria-label="近期工作"><div className="panel-heading"><h2><Clock size={20}/>近期工作</h2><span className="muted">本页 {current.entries.length} 个小时 · {pageOriginals.size} 条原始记录</span></div><p className="history-caption">{current.start.replaceAll('-','/')}～{current.end.replaceAll('-','/')} · 北京时间 · 每页10天；原始时间与摘要仍可追溯</p>
 {status?.status==='error'&&<p className="history-warning" role="status">本次读取失败，保留上次记录。{status.message}</p>}
 {delayed&&<p className="history-warning">最新记录：{new Date(latest.startedAt).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'})}。最近尚无新摘要，休眠、离线或记录暂停时会延迟。</p>}
 {!current.entries.length&&<div className="empty"><Clock size={28}/><strong>{grouped.length?'这10天暂无记录':'等待近期工作同步'}</strong><p>{current.pageCount>1?'可在底部翻页查看其他日期的记录。':'采集到真实活动摘要后，会在这里按时间显示。'}</p></div>}
 {[...days.entries()].map(([day,items],index)=><Collapsible key={day} defaultOpen={day===today||index===0} className="history-day"><CollapsibleTrigger className="history-day-trigger"><span>{day===today?'今天':day===yesterday?'昨天':day.replaceAll('-',' / ')}</span><ChevronDown size={18}/><small>{items.length} 条</small></CollapsibleTrigger><CollapsibleContent><ol className="history-timeline">{items.map(entry=><li className="history-entry" key={entry.id}><time dateTime={entry.startedAt} title={time(entry.startedAt)+'–'+time(entry.endedAt)}>{time(entry.startedAt)}</time><div className="history-event"><h3>{time(entry.startedAt)}–{time(entry.endedAt)} 工作汇总</h3><p>{entry.summary}</p><details className="history-originals"><summary>查看 {entry.originals.length} 条原始摘要与时间</summary>{entry.originals.map(original=><div key={original.id}><strong>{time(original.startedAt)}–{time(original.endedAt)} · {original.title}</strong><p>{original.summary}</p></div>)}</details><div className="history-apps" aria-label="相关应用">{entry.applications.map(bid=><ApplicationIcon key={bid} bundleId={bid}/>)}</div></div></li>)}</ol></CollapsibleContent></Collapsible>)}
 <nav className="history-pagination" aria-label="近期工作分页"><Button type="button" variant="outline" disabled={current.page===0} onClick={()=>changePage(current.page-1)}><ChevronLeft size={16}/>上一页</Button><span role="status" aria-live="polite">第 {current.page+1} / {current.pageCount} 页 · 每页10天</span><Button type="button" variant="outline" disabled={current.page===current.pageCount-1} onClick={()=>changePage(current.page+1)}>下一页<ChevronRight size={16}/></Button></nav>
 </section>;
}
