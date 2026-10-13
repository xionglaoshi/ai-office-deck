import {officeOrigin} from '@/lib/owner-auth';
export async function POST(req:Request){if(req.headers.get('origin')!==officeOrigin(req))return new Response(null,{status:403});return new Response(null,{status:303,headers:{Location:'/owner-login','Set-Cookie':'office_owner=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'}});}
