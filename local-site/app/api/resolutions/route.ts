import {serviceDenied,officeOrigin} from '@/lib/owner-auth';
import {env} from 'cloudflare:workers';
import {z} from 'zod';
import {policy,titleKey,type PolicyTask} from '@/lib/task-policy';
export const dynamic='force-dynamic';
const answer=(d:unknown,s=200)=>Response.json(d,{status:s,headers:{'Cache-Control':'private, no-store'}});
// Same owner-private service boundary as /api/curate. User's explicit statement only.
const schema=z.object({id:z.string().uuid(),expectedUpdated:z.string().datetime(),evidence:z.string().min(1).max(2000)}).strict();
export async function POST(req:Request){const denied=serviceDenied(req);if(denied)return denied;if(req.headers.get('origin')&&req.headers.get('origin')!==officeOrigin(req))return answer({message:'请求来源无效'},403);try{
 if(!env.DB)return answer({message:'存储不可用'},503);const d=schema.parse(await req.json());const t=await env.DB.prepare('SELECT id,title,kind,done,deleted,manual_override,updated FROM tasks WHERE id=?').bind(d.id).first<PolicyTask>();if(!t||t.deleted)return answer({message:'事项不存在或已删除'},404);if(t.updated!==d.expectedUpdated)return answer({message:'事项已变化，请重读核对'},409);const p=await policy(env.DB,[t]),time=new Date().toISOString();
 const timeKey=p.subjects[t.id]||titleKey(t.title);
 const guarded=env.DB.prepare('UPDATE tasks SET done=1,manual_override=1,updated=? WHERE id=? AND updated=? AND deleted=0').bind(time,t.id,t.updated);
 // Conditional inserts are executed with the status update in one D1 transaction.
 const keys=[...new Set([timeKey,titleKey(t.title)])];const inserts=keys.map(key=>env.DB!.prepare("INSERT INTO sync_state(id,payload,updated) SELECT ?,?,? WHERE EXISTS(SELECT 1 FROM tasks WHERE id=? AND updated=? AND done=1 AND deleted=0) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,updated=excluded.updated").bind('resolved:'+key,JSON.stringify({key,taskId:t.id,title:t.title,reason:'用户明确告知：'+d.evidence,resolvedAt:time}),time,t.id,time));
 const results=await env.DB.batch([guarded,...inserts]);if(!results[0].meta.changes)return answer({message:'事项已变化，未覆盖'},409);return answer({success:true,id:t.id,done:1,updated:time});
 }catch{return answer({message:'完成或消除记录保存失败'},400);}}
