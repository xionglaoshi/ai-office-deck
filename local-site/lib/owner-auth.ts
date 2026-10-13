import {env} from 'cloudflare:workers';
const vars=()=>env as unknown as Record<string,string|undefined>;
export const selfHosted=()=>vars().SELF_HOSTED==='1';
const enc=new TextEncoder();
function equal(a:string,b:string){let d=a.length^b.length;for(let i=0;i<Math.max(a.length,b.length);i++)d|=(a.charCodeAt(i)||0)^(b.charCodeAt(i)||0);return d===0;}
async function digest(s:string){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',enc.encode(s)))].map(b=>b.toString(16).padStart(2,'0')).join('');}
async function sign(s:string){const secret=vars().OWNER_SESSION_KEY;if(!secret||secret.length<32)throw Error('Session key unavailable');const key=await crypto.subtle.importKey('raw',enc.encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign']);return [...new Uint8Array(await crypto.subtle.sign('HMAC',key,enc.encode(s)))].map(b=>b.toString(16).padStart(2,'0')).join('');}
export async function verifyPassword(password:string){const expected=vars().OWNER_PASSWORD_HASH;return !!expected&&password.length>=12&&equal(await digest(password),expected);}
export async function makeSession(){const payload=String(Date.now()+12*60*60*1000);return payload+'.'+await sign(payload);}
export async function verifySession(value:string){try{const [payload,signature,...extra]=value.split('.');return !extra.length&&Number(payload)>Date.now()&&Number(payload)<Date.now()+13*60*60*1000&&equal(await sign(payload),signature);}catch{return false;}}
export function serviceDenied(req:Request){if(!selfHosted())return null;const token=vars().OFFICE_SERVICE_TOKEN;const auth=req.headers.get('authorization')||'';if(!token||token.length<32||!equal(auth,'Bearer '+token))return Response.json({message:'Service authorization required'},{status:401,headers:{'Cache-Control':'no-store'}});return null;}
export function officeOrigin(req:Request){const configured=vars().OFFICE_PUBLIC_URL;if(selfHosted()&&configured){try{return new URL(configured).origin;}catch{throw Error('Invalid office public URL');}}return new URL(req.url).origin;}

export function localNoPassword(){if(!selfHosted()||vars().LOCAL_NO_PASSWORD!=="1")return false;try{const u=new URL(vars().OFFICE_PUBLIC_URL||"");return u.protocol==="http:"&&["127.0.0.1","localhost","[::1]"].includes(u.hostname);}catch{return false;}}
