import {officeOrigin} from '@/lib/owner-auth';
import {env} from 'cloudflare:workers';
import {getChatGPTUser} from '@/app/chatgpt-auth';
import {z} from 'zod';
import {policy,resolutionStatements,titleKey,type PolicyTask} from '@/lib/task-policy';
import {normalizeKind,kindSchema,archiveStatement} from '@/lib/office-data';
export const dynamic='force-dynamic';
const headers={'Cache-Control':'private, no-store'};
const answer=(data:unknown,status=200)=>Response.json(data,{status,headers});
const form=z.object({action:z.literal('save'),id:z.string().uuid().optional(),createId:z.string().uuid().optional(),expectedUpdated:z.string().optional(),title:z.string().trim().min(1).max(200),kind:kindSchema,category:z.enum(['office','technical']).optional(),priority:z.enum(['normal','urgent']),due:z.string().refine(v=>!v||(/^\d{4}-\d{2}-\d{2}$/.test(v)&&!isNaN(Date.parse(v))&&new Date(v).toISOString().slice(0,10)===v)),project:z.string().max(100),note:z.string().max(80000),source:z.string().trim().min(1).max(100),url:z.string().max(1000).refine(v=>!v||/^https?:\/\//.test(v)&&URL.canParse(v))}).strict();
const toggle=z.object({action:z.literal('toggle'),id:z.string().uuid(),expectedUpdated:z.string().optional(),done:z.union([z.literal(0),z.literal(1),z.literal(2)])}).strict();
const remove=z.object({action:z.literal('delete'),id:z.string().uuid(),expectedUpdated:z.string().optional()}).strict();
export async function GET(req:Request){
 try{
  const user=await getChatGPTUser();if(!user)return answer({message:'请登录后查看工作清单'},401);
  if(!env.DB)return answer({message:'工作清单暂时无法读取，请稍后重试'},503);
  const r=await env.DB.prepare("SELECT id,title,kind,category,priority,due,project,note,source,url,done,updated,manual_override FROM tasks WHERE (user_id=? OR user_id='__automatic__') AND deleted=0 ORDER BY updated DESC").bind(user.userId).all();
  const records=await env.DB.prepare("SELECT id,payload,updated FROM sync_state WHERE id LIKE 'detail:%' OR id LIKE 'brief:%'").all<{id:string;payload:string;updated:string}>();
  const detail=Object.fromEntries(records.results.filter(x=>x.id.startsWith('detail:')).map(x=>[x.id.slice(7),JSON.parse(x.payload)]));
  const sourceId=new URL(req.url).searchParams.get('source'),sourceVersion=new URL(req.url).searchParams.get('version');
  if(sourceId){const current=await env.DB.prepare('SELECT payload,updated FROM sync_state WHERE id=?').bind('source:'+sourceId).first<{payload:string;updated:string}>();const currentSource=current?JSON.parse(current.payload):null;const entry=!sourceVersion||currentSource?.sourceVersion===sourceVersion?current:await env.DB.prepare('SELECT payload,updated FROM sync_state WHERE id=?').bind('source-version:'+sourceId+':'+sourceVersion).first<{payload:string;updated:string}>();if(!entry)return answer({message:'来源档案不存在'},404);const source=JSON.parse(entry.payload);if(currentSource&&source.sourceVersion===currentSource.sourceVersion&&source.sourcePath&&typeof source.part==='number'){const stored=await env.DB.prepare("SELECT payload FROM sync_state WHERE id LIKE 'source:%'").all<{payload:string}>();const parts=stored.results.map(x=>JSON.parse(x.payload)).filter(x=>x.sourcePath===source.sourcePath&&x.sourceGroup===source.sourceGroup&&x.recordId===source.recordId&&typeof x.part==='number').sort((a,b)=>a.part-b.part);source.note=parts.map(x=>x.note).join('\n');source.savedParts=parts.length;}else if(sourceVersion&&currentSource?.sourceVersion!==sourceVersion){source.note='历史证据分片；其他原版本分片关联未确认，不能当作全文。\n'+source.note;}return answer({source,savedAt:entry.updated});}
  const historyId=new URL(req.url).searchParams.get('history');
  if(historyId){if(!r.results.some((t:any)=>t.id===historyId))return answer({message:'事项不存在'},404);const revisions=await env.DB.prepare("SELECT payload,updated FROM sync_state WHERE id LIKE ? ORDER BY updated DESC").bind('revision:'+historyId+':%').all<{payload:string;updated:string}>();return answer({revisions:revisions.results.map(x=>({...JSON.parse(x.payload),recordedAt:x.updated}))});}
  const state=await env.DB.prepare('SELECT payload,updated FROM sync_state WHERE id=?').bind('latest').first<{payload:string;updated:string}>();
  const curated=await env.DB.prepare('SELECT payload,updated FROM sync_state WHERE id=?').bind('curated').first<{payload:string;updated:string}>();
  const reminders=await env.DB.prepare('SELECT payload FROM sync_state WHERE id=?').bind('reminders').first<{payload:string}>();
  return answer({tasks:r.results.map((t:any)=>({...t,kind:normalizeKind(t.kind),...detail[t.id]})),sync:state?{...JSON.parse(state.payload),updated:state.updated,reminders:reminders?JSON.parse(reminders.payload):null,candidates:undefined,briefs:records.results.filter(x=>x.id.startsWith('brief:')).sort((a,b)=>b.updated.localeCompare(a.updated)).map(x=>({id:x.id,updated:x.updated,...JSON.parse(x.payload)})),curated:curated?{...JSON.parse(curated.payload),updated:curated.updated}:null}:null});
 }catch(e){console.error('Tasks read failed',e);return answer({message:'读取失败，请重试；尚未确认清单是否为空'},503);}
}
export async function POST(req:Request){
 if(req.headers.get('origin')!==officeOrigin(req))return answer({message:'请在工作台中操作'},403);
 try{
  const user=await getChatGPTUser();if(!user)return answer({message:'请登录后保存事项'},401);
  if(!env.DB)return answer({message:'暂时无法保存，请保留输入并稍后重试'},503);
  const parsed=z.union([form,toggle,remove]).safeParse(await req.json());if(!parsed.success)return answer({message:'请检查事项名称、日期和链接格式'},400);
  const t=parsed.data,now=new Date().toISOString();
  const previous='id' in t&&t.id?await env.DB.prepare("SELECT * FROM tasks WHERE id=? AND (user_id=? OR user_id='__automatic__') AND deleted=0").bind(t.id,user.userId).first<PolicyTask>():null;
  if(previous&&t.expectedUpdated&&previous.updated!==t.expectedUpdated)return answer({message:'事项已在另一处修改，请刷新后重试'},409);
  const rules=previous?await policy(env.DB,[previous]):null;
  if(t.action==='delete'||t.action==='toggle'){
   if(!previous||!rules)return answer({message:'事项已不存在，请刷新'},404);
   const update=t.action==='delete'?env.DB.prepare("UPDATE tasks SET deleted=1,manual_override=1,updated=? WHERE id=? AND (user_id=? OR user_id='__automatic__') AND deleted=0 AND updated=?").bind(now,t.id,user.userId,previous.updated):env.DB.prepare("UPDATE tasks SET done=?,manual_override=1,updated=? WHERE id=? AND (user_id=? OR user_id='__automatic__') AND deleted=0 AND updated=?").bind(t.done,now,t.id,user.userId,previous.updated);
   const close=t.action==='delete'||t.done===1||t.done===2;
   const reason=t.action==='delete'?'人工删除':t.done===2?'人工放弃':normalizeKind(previous.kind)==='tracking'?'人工完成':'人工消除';
   const result=await env.DB.batch([update,await archiveStatement(env.DB,previous,now),...resolutionStatements(env.DB,previous,rules.subjects[t.id]||titleKey(previous.title),now,reason,close)]);
   if(!result[0].meta.changes)return answer({message:'事项已不存在，请刷新'},404);return answer({success:true});
  }
  const id=t.id||t.createId||crypto.randomUUID();
  if(t.id){
   if(!previous)return answer({message:'事项已不存在，请刷新'},404);
   await env.DB.batch([await archiveStatement(env.DB,previous,now)]);
   const r=await env.DB.prepare("UPDATE tasks SET title=?,kind=?,category=?,priority=?,due=?,project=?,note=?,source=?,url=?,manual_override=1,updated=? WHERE id=? AND (user_id=? OR user_id='__automatic__') AND deleted=0 AND updated=?").bind(t.title,t.kind,t.category||'office',t.priority,t.due,t.project,t.note,t.source,t.url,now,id,user.userId,previous.updated).run();
   if(!r.meta.changes)return answer({message:'事项已不存在，请刷新'},404);
  }else{
   await env.DB.prepare('INSERT INTO tasks (id,user_id,title,kind,category,priority,due,project,note,source,url,done,updated) VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?) ON CONFLICT(id) DO NOTHING').bind(id,user.userId,t.title,t.kind,t.category||'office',t.priority,t.due,t.project,t.note,t.source,t.url,now).run();
  }
  return answer({success:true,id});
 }catch(e){console.error('Tasks write failed',e);return answer({message:'保存失败，请保留输入并刷新核对后重试'},503);}
}
