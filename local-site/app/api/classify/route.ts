import {env} from 'cloudflare:workers';
import {z} from 'zod';
import {serviceDenied,officeOrigin} from '@/lib/owner-auth';
import {kindSchema,archiveStatement} from '@/lib/office-data';
export const dynamic='force-dynamic';
const schema=z.object({items:z.array(z.object({id:z.string().uuid(),kind:kindSchema,expectedUpdated:z.string()}).strict()),reason:z.string().min(1).max(1000)}).strict();
const answer=(d:unknown,s=200)=>Response.json(d,{status:s,headers:{'Cache-Control':'private, no-store'}});
// An owner-authorized category-only migration: states, identity and human text are untouched.
export async function POST(req:Request){
 const denied=serviceDenied(req);if(denied)return denied;
 if(req.headers.get('origin')&&req.headers.get('origin')!==officeOrigin(req))return answer({message:'请求来源无效'},403);
 try{
  if(!env.DB)return answer({message:'存储不可用'},503);const db=env.DB;
  const parsed=schema.safeParse(await req.json());if(!parsed.success)return answer({message:'分类格式无效'},400);
  const {items,reason}=parsed.data;if(new Set(items.map(i=>i.id)).size!==items.length)return answer({message:'重复事项'},400);
  const now=new Date().toISOString(),statements=[];
  for(const item of items){
   const old=await db.prepare('SELECT * FROM tasks WHERE id=?').bind(item.id).first<any>();
   if(!old||old.updated!==item.expectedUpdated)return answer({message:'事项已变化，请重读后核对'},409);
   const record=await db.prepare('SELECT payload FROM sync_state WHERE id=?').bind('detail:'+item.id).first<{payload:string}>();
   const detail=record?JSON.parse(record.payload):{};
   statements.push(await archiveStatement(db,{...old,...detail},now));
   statements.push(db.prepare('UPDATE tasks SET kind=?,updated=? WHERE id=? AND updated=?').bind(item.kind,now,item.id,item.expectedUpdated));
   statements.push(db.prepare('INSERT INTO sync_state(id,payload,updated) SELECT ?,?,? WHERE EXISTS(SELECT 1 FROM tasks WHERE id=? AND updated=?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,updated=excluded.updated').bind('classification:'+item.id,JSON.stringify({kind:item.kind,reason}),now,item.id,now));
   statements.push(db.prepare('INSERT INTO sync_state(id,payload,updated) SELECT ?,?,? WHERE EXISTS(SELECT 1 FROM tasks WHERE id=? AND updated=?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,updated=excluded.updated').bind('detail:'+item.id,JSON.stringify({...detail,personalTask:item.kind==='tracking',remind:item.kind==='tracking'&&!!detail.remind}),now,item.id,now));
  }
  // The write guards also check versions inside the batch, after the preflight reads.
  await db.batch(statements);
  const result=await db.prepare('SELECT id,kind,updated FROM tasks').all<{id:string;kind:string;updated:string}>();
  if(items.some(i=>!result.results.some(r=>r.id===i.id&&r.kind===i.kind&&r.updated===now)))return answer({message:'分类存在并发变化，请重读核对'},409);
  return answer({success:true,selected:items.length,updated:now,readbackVerified:true});
 }catch{return answer({message:'分类保存失败，请读回核对'},503);}
}
