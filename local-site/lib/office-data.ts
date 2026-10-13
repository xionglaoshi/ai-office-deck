import {z} from 'zod';
export const normalizeKind=(kind:string)=>kind==='task'?'tracking':kind==='attention'||kind==='decision'?'risk':kind;
export const isTracking=(kind:string)=>normalizeKind(kind)==='tracking';
export const kindSchema=z.enum(['tracking','risk','advice','task','attention','decision']).transform(normalizeKind);
export const evidenceSchema=z.object({sourceId:z.string().uuid(),date:z.string().max(80).default(''),reporter:z.string().max(200).default(''),location:z.string().max(2000).default(''),excerpt:z.string().max(20000).default(''),version:z.string().max(100).default(''),type:z.enum(['reported','document','verified','suggestion']).default('reported')}).strict();
export const itemSchema=z.object({id:z.string().uuid(),subjectKey:z.string().trim().min(1).max(500).optional(),title:z.string().min(1).max(200),kind:kindSchema,priority:z.enum(['normal','urgent']),due:z.string().refine(v=>!v||/^\d{4}-\d{2}-\d{2}$/.test(v)&&!isNaN(Date.parse(v))&&new Date(v).toISOString().slice(0,10)===v),project:z.string().max(100),note:z.string().max(80000),source:z.string().max(100),url:z.string().max(1000).refine(v=>!v||/^https?:\/\//.test(v)&&URL.canParse(v)),summary:z.string().max(12000).default(''),latestProgress:z.string().max(20000).default(''),responsibility:z.string().max(4000).default(''),nextStep:z.string().max(12000).default(''),coverageGap:z.string().max(4000).default(''),remind:z.boolean().default(false),evidence:z.array(evidenceSchema).default([])}).strict();
export function detailsOf(t:z.infer<typeof itemSchema>){return {summary:t.summary,latestProgress:t.latestProgress,responsibility:t.responsibility,nextStep:t.nextStep,coverageGap:t.coverageGap,remind:t.remind&&isTracking(t.kind),evidence:t.evidence};}
export function candidateGroup(t:{source:string;sourceGroup?:string;subjectKey?:string}){return t.sourceGroup||(t.subjectKey?.startsWith('wiki-risk:')?'WIKI问题与风险':t.source);}
export function mergeSourceSnapshot(old:any,data:any){
 const failed=new Set<string>();const sources=data.sources.map((s:any)=>{
  const previous=(old.sources||[]).find((x:any)=>x.name===s.name);
  const emptyUnexpected=s.status==='success'&&s.count===0&&previous?.count>0&&!(s.filesRead>0);
  if(s.status==='error'||s.complete===false||emptyUnexpected){failed.add(s.name);return {...s,status:'error',complete:false,message:s.message+'；覆盖不完整，保留上次有效候选',preservedCount:(old.candidates||[]).filter((t:any)=>candidateGroup(t)===s.name).length};}
  return s;
 });
 const entries=new Map((old.candidates||[]).filter((t:any)=>failed.has(candidateGroup(t))).map((t:any)=>[t.id,{...t,coverageStale:true}]));
 for(const t of data.items)entries.set(t.id,{...t,coverageStale:failed.has(candidateGroup(t))});
 const activities=new Map((old.activity||[]).filter((t:any)=>failed.has(t.source)).map((t:any)=>[t.source+':'+t.path,t]));
 for(const t of data.activity)activities.set(t.source+':'+t.path,t);
 return {computerHistory:data.computerHistory??old.computerHistory??[],sources,activity:[...activities.values()],received:entries.size,candidates:[...entries.values()],collectedAt:data.collectedAt,coverageComplete:failed.size===0};
}
export async function contentHash(value:unknown){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(value))))].map(v=>v.toString(16).padStart(2,'0')).join('');}
export function taskContent(t:any){const {updated,user_id,manual_override,category,...content}=t;return content;}
export async function archiveStatement(db:any,t:any,time:string){const payload=JSON.stringify(t);return db.prepare('INSERT INTO sync_state(id,payload,updated) VALUES(?,?,?) ON CONFLICT(id) DO NOTHING').bind('revision:'+t.id+':'+await contentHash(taskContent(t)),payload,time);}
