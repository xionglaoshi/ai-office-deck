import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createRequire} from 'node:module';
import {resolve} from 'node:path';
import {mkdirSync} from 'node:fs';
import {hourlyHistory} from '../lib/hourly-history.ts';
const require=createRequire(import.meta.url),esbuild=require('esbuild');
const root=resolve(import.meta.dirname,'..');
const database=new DatabaseSync(':memory:');
database.exec("CREATE TABLE tasks(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,title TEXT NOT NULL,kind TEXT NOT NULL,category TEXT NOT NULL DEFAULT '',priority TEXT NOT NULL,due TEXT NOT NULL DEFAULT '',project TEXT NOT NULL DEFAULT '',note TEXT NOT NULL DEFAULT '',source TEXT NOT NULL DEFAULT '手动录入',url TEXT NOT NULL DEFAULT '',deleted INTEGER NOT NULL DEFAULT 0,manual_override INTEGER NOT NULL DEFAULT 0,done INTEGER NOT NULL DEFAULT 0,updated TEXT NOT NULL); CREATE TABLE sync_state(id TEXT PRIMARY KEY,payload TEXT NOT NULL,updated TEXT NOT NULL)");
class Statement{constructor(sql,args=[]){this.sql=sql;this.args=args;}bind(...args){return new Statement(this.sql,args);}async first(){return database.prepare(this.sql).get(...this.args)||null;}async all(){return {results:database.prepare(this.sql).all(...this.args)};}async run(){const r=database.prepare(this.sql).run(...this.args);return {meta:{changes:Number(r.changes)}};}}
const token='isolated-test-token-000000000000000000000000';
globalThis.testEnv={SELF_HOSTED:'1',OFFICE_SERVICE_TOKEN:token,OFFICE_PUBLIC_URL:'http://127.0.0.1:5199',DB:{prepare(sql){return new Statement(sql);},async batch(statements){database.exec('BEGIN');try{const results=[];for(const statement of statements)results.push(await statement.run());database.exec('COMMIT');return results;}catch(e){database.exec('ROLLBACK');throw e;}}}};
mkdirSync(resolve(root,'tests/bundles'),{recursive:true});
const modules={};
for(const name of ['sync','curate','tasks']){const out=resolve(root,'tests/bundles/'+name+'.mjs');await esbuild.build({entryPoints:[resolve(root,'app/api/'+name+'/route.ts')],outfile:out,bundle:true,platform:'node',format:'esm',plugins:[{name:'isolated-environment',setup(build){build.onResolve({filter:/^cloudflare:workers$/},()=>({path:'env',namespace:'test'}));build.onResolve({filter:/^@\/app\/chatgpt-auth$/},()=>({path:'user',namespace:'test'}));build.onLoad({filter:/.*/,namespace:'test'},args=>({contents:args.path==='env'?'export const env=globalThis.testEnv;':'export async function getChatGPTUser(){return {userId:"test-owner"}}'}));build.onResolve({filter:/^@\//},args=>({path:resolve(root,args.path.slice(2)+'.ts')}));}}]});modules[name]=await import(out);}
let timestamp=Date.parse('2026-10-13T03:00:00Z');const clock=()=>new Date(timestamp+=1000).toISOString();
const source=crypto.randomUUID(),keep=crypto.randomUUID(),identity='report:stable-original-id:axle-condition';
const item=(id,key,title='测试同名事项')=>({id,subjectKey:key,title,kind:'risk',priority:'normal',due:'',project:'隔离测试',note:'仅测试内存；不会进入真实办公台',source:'WIKI日报',url:'',summary:'已读正文证据',nextStep:'核实状态',remind:false,evidence:[{sourceId:source,location:'isolated fixture',date:'2026-10-12',reporter:'test'}]});
let latest='';
async function call(name,payload){const response=await modules[name].POST(new Request('http://127.0.0.1:5199/api/'+name,{method:'POST',headers:{Authorization:'Bearer '+token,Origin:'http://127.0.0.1:5199','Content-Type':'application/json'},body:JSON.stringify(payload)}));return {status:response.status,...await response.json()};}
async function sync(empty=false){latest=clock();return call('sync',{collectedAt:latest,items:empty?[]:[{id:source,title:'来源',kind:'attention',priority:'normal',due:'',project:'来源',note:'fixture',source:'WIKI日报',url:''}],sources:[{name:'WIKI日报',status:'success',count:empty?0:1,message:'test',complete:true}],activity:[]});}
async function curate(items){return call('curate',{items,summary:'隔离综合测试',reviewedAt:clock(),snapshotAt:latest});}
assert.equal((await sync()).success,true);
const risk=item(crypto.randomUUID(),identity),other=item(keep,'other:independent');
assert.equal((await curate([risk,other])).selected,2);
assert.equal((await curate([risk,other])).selected,2);
assert.equal(database.prepare('SELECT count(*) n FROM tasks').get().n,2);
assert.equal(database.prepare("SELECT count(*) n FROM sync_state WHERE id LIKE 'brief:%'").get().n,1,'identical review must not duplicate stored brief');
let closed=await call('tasks',{action:'delete',id:risk.id});assert.equal(closed.success,true);
const renamed={...risk,id:crypto.randomUUID(),title:'更名后不同来源再提',source:'WIKI部署与关注'};
assert.equal((await curate([renamed,other])).blocked,1,'deleted canonical subject must not revive under another title/source');
const emptyResult=await sync(true);assert.equal(emptyResult.coverageComplete,false);
let payload=JSON.parse(database.prepare("SELECT payload FROM sync_state WHERE id='latest'").get().payload);assert.equal(payload.candidates.length,1);assert.equal(payload.sources[0].status,'error');
assert.equal((await curate([])).preservedUnselected,true);assert.equal(database.prepare('SELECT deleted FROM tasks WHERE id=?').get(keep).deleted,0);
timestamp+=3600000;await sync(false);assert.equal((await curate([renamed,other])).blocked,1);assert.equal(database.prepare('SELECT deleted FROM tasks WHERE id=?').get(risk.id).deleted,1);
const sameTitleA=item(crypto.randomUUID(),'different:a'),sameTitleB=item(crypto.randomUUID(),'different:b');assert.equal((await curate([other,sameTitleA,sameTitleB])).selected,3,'same title with independent stable identities must coexist');
const large=Array.from({length:1201},(_,i)=>({...item(crypto.randomUUID(),'many:'+i),title:'隔离条目'+i,kind:i%3===0?'tracking':i%3===1?'risk':'advice'}));assert.equal((await curate(large)).selected,1201,'old 100/1000 limits removed');
const read=await modules.tasks.GET(new Request('http://127.0.0.1:5199/api/tasks'));const data=await read.json();assert.equal(data.tasks.filter(t=>t.done===0).length,1201);
const changed=database.prepare('SELECT * FROM tasks WHERE id=?').get(large[0].id);await call('tasks',{action:'toggle',id:changed.id,done:1,expectedUpdated:changed.updated});assert.equal((await curate(large)).blocked,1,'manual completion remains authoritative');
const history=(id,start,end,summary='重复内容。')=>({id,title:'工作',summary,startedAt:start,endedAt:end,applications:['test.app']});
const raw=[history('a','2026-10-12T15:55:00Z','2026-10-12T16:05:00Z'),history('b','2026-10-12T16:00:00Z','2026-10-12T16:10:00Z'),history('b','2026-10-12T16:00:00Z','2026-10-12T16:10:00Z')];let hours=hourlyHistory(raw);assert.deepEqual(hours.map(h=>h.id),['hour:2026-10-13T00','hour:2026-10-12T23']);assert.equal(hours[0].originals.length,2);assert.equal(hours[0].summary,'重复内容。');assert.equal(hours[1].originals[0].startedAt,raw[0].startedAt);hours=hourlyHistory([...raw,history('late','2026-10-12T16:20:00Z','2026-10-12T16:30:00Z','迟到记录。')]);assert.equal(hours[0].originals.length,3);assert.equal(hours.length,2);assert.deepEqual(hourlyHistory([history('edge','2026-10-12T15:50:00Z','2026-10-12T16:00:00Z')]).map(h=>h.id),['hour:2026-10-12T23']);
const longSource={id:crypto.randomUUID(),title:'隔离长正文',kind:'attention',priority:'normal',due:'',project:'测试',note:'测试全文'.repeat(12000),source:'WIKI日报',url:'',sourceVersion:'test-long'};latest=clock();assert.equal((await call('sync',{collectedAt:latest,items:[longSource],sources:[{name:'WIKI日报',status:'success',count:1,message:'test',complete:true}],activity:[]})).success,true);const full=JSON.parse(database.prepare('SELECT payload FROM sync_state WHERE id=?').get('source:'+longSource.id).payload);assert.equal(full.note.length,longSource.note.length);const idx=JSON.parse(database.prepare("SELECT payload FROM sync_state WHERE id='latest'").get().payload);assert.equal(idx.candidates[0].contentStoredSeparately,true);
const closedSourceId=crypto.randomUUID(),closedSourceKey='wiki-risk:caselaw/isolated-case.md:case';database.prepare('INSERT INTO sync_state(id,payload,updated) VALUES(?,?,?)').run('source:'+closedSourceId,JSON.stringify({id:closedSourceId,subjectKey:closedSourceKey,note:'isolated closed source'}),clock());database.prepare('INSERT INTO sync_state(id,payload,updated) VALUES(?,?,?)').run('resolved:'+closedSourceKey,JSON.stringify({key:closedSourceKey,taskId:crypto.randomUUID(),title:'closed case',reason:'manual deletion',resolvedAt:clock()}),clock());const wrongIdentity={...item(crypto.randomUUID(),'new-key-and-name'),title:'source alias with another identity',evidence:[{sourceId:closedSourceId}]};assert.equal((await curate([wrongIdentity])).blocked,1,'closed evidence scope must block rename/new key derivation');
console.log('PASS: real route handlers with isolated SQLite — idempotency, renamed deletion, empty/recovery source, independent same titles, 1201 items, completion, Beijing hour/day/late/dedup boundaries');
