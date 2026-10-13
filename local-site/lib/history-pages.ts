const DAY=86400000;
export function beijingDay(value:string|number){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(value));}
// Calendar-day windows, including today; a missing day never expands the window.
export function historyPage<T extends {startedAt:string}>(entries:readonly T[],requestedPage=0,now=Date.now()){
 const today=beijingDay(now),anchor=Date.parse(today+'T00:00:00Z');
 const dated=entries.filter(e=>Number.isFinite(Date.parse(e.startedAt))).map(entry=>({entry,day:beijingDay(entry.startedAt)})).filter(e=>e.day<=today);
 const oldest=dated.reduce((day,e)=>e.day<day?e.day:day,today);
 const pageCount=Math.max(1,Math.ceil((Math.round((anchor-Date.parse(oldest+'T00:00:00Z'))/DAY)+1)/10));
 const page=Math.max(0,Math.min(Number.isFinite(requestedPage)?Math.floor(requestedPage):0,pageCount-1));
 const end=new Date(anchor-page*10*DAY).toISOString().slice(0,10),start=new Date(anchor-(page*10+9)*DAY).toISOString().slice(0,10);
 return {page,pageCount,start,end,entries:dated.filter(e=>e.day>=start&&e.day<=end).map(e=>e.entry)};
}
