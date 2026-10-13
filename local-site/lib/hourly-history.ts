export type HistoryEntry={id:string;title:string;summary:string;startedAt:string;endedAt:string;applications:string[]};
export type HourEntry=HistoryEntry&{originals:HistoryEntry[]};
export function hourlyHistory(entries:HistoryEntry[]):HourEntry[]{
 const originals=new Map(entries.map(e=>[e.id,e]));const hours=new Map<number,HistoryEntry[]>();
 for(const e of originals.values()){
  const start=Date.parse(e.startedAt),end=Date.parse(e.endedAt);if(!Number.isFinite(start)||!Number.isFinite(end)||end<start)continue;
  for(let cursor=Math.floor(start/3600000)*3600000;cursor<Math.max(end,start+1);cursor+=3600000){hours.set(cursor,[...(hours.get(cursor)||[]),e]);}
 }
 return [...hours.entries()].sort((a,b)=>b[0]-a[0]).map(([hour,rows])=>{
  rows.sort((a,b)=>a.startedAt.localeCompare(b.startedAt));const sentences=new Map<string,string>();
  for(const row of rows)for(const sentence of row.summary.split(/(?<=[。！？])\s*|\n+/)){const key=sentence.replace(/[\s\p{P}\p{S}]/gu,'');if(key&&!sentences.has(key))sentences.set(key,sentence);}
  return {id:'hour:'+new Date(hour+8*3600000).toISOString().slice(0,13),title:[...new Set(rows.map(e=>e.title))].join(' · '),summary:[...sentences.values()].join('\n'),startedAt:new Date(hour).toISOString(),endedAt:new Date(hour+3600000).toISOString(),applications:[...new Set(rows.flatMap(e=>e.applications))],originals:rows};
 });
}
