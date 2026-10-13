import type {D1Database} from '@cloudflare/workers-types';
export type PolicyTask={id:string;title:string;kind:string;done:number;deleted?:number;manual_override?:number;updated:string};
export function titleKey(title:string){return 'title:'+title.normalize('NFKC').replace(/[（(](?:待核对|待确认|待验收|已完成|已消除)[）)]/g,'').replace(/^(?:待核对|核对|跟进)[：:]?/,'').replace(/[\s\p{P}\p{S}]/gu,'').toLowerCase();}
export async function policy(db:D1Database,tasks:PolicyTask[]){
 const rows=await db.prepare("SELECT id,payload FROM sync_state WHERE id LIKE 'subject:%' OR id LIKE 'resolved:%'").all<{id:string;payload:string}>();
 const subjects:Record<string,string>={},resolved:Record<string,{key:string;taskId:string;title:string;reason:string;resolvedAt:string}>={};
 for(const row of rows.results){const data=JSON.parse(row.payload);if(row.id.startsWith('subject:'))subjects[row.id.slice(8)]=data.key;else resolved[data.key]=data;}
 for(const t of tasks)if(t.manual_override&&(t.done===1||t.done===2||t.deleted))for(const key of [subjects[t.id]||titleKey(t.title),titleKey(t.title)])resolved[key]??={key,taskId:t.id,title:t.title,reason:t.deleted?'人工删除':(t.kind==='task'||t.kind==='tracking')?'人工完成':'人工消除',resolvedAt:t.updated};
 return {subjects,resolved,closed:new Set(Object.keys(resolved))};
}
export function subjectStatement(db:D1Database,id:string,key:string,time:string){return db.prepare('INSERT INTO sync_state(id,payload,updated) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,updated=excluded.updated').bind('subject:'+id,JSON.stringify({key}),time);}
export function resolutionStatements(db:D1Database,t:PolicyTask,key:string,time:string,reason:string,close=true){
 return [...new Set([key,titleKey(t.title)])].map(k=>close?db.prepare('INSERT INTO sync_state(id,payload,updated) SELECT ?,?,? WHERE EXISTS(SELECT 1 FROM tasks WHERE id=? AND updated=?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,updated=excluded.updated').bind('resolved:'+k,JSON.stringify({key:k,taskId:t.id,title:t.title,reason,resolvedAt:time}),time,t.id,time):db.prepare("DELETE FROM sync_state WHERE id=? AND json_extract(payload,'$.taskId')=? AND EXISTS(SELECT 1 FROM tasks WHERE id=? AND updated=?)").bind('resolved:'+k,t.id,t.id,time));
}
