import {getChatGPTUser} from '@/app/chatgpt-auth';
import {WEATHER_URL,parseWeather,currentWeatherValid,type CityWeather} from '@/lib/weather';
export const dynamic='force-dynamic';
let cache:CityWeather|null=null;
let pending:Promise<CityWeather>|null=null;
const headers={'Cache-Control':'private, no-store'};
export async function GET(){
 if(!await getChatGPTUser())return Response.json({message:'请登录后查看天气'}, {status:401,headers});
 if(cache&&currentWeatherValid(cache)&&Date.now()-Date.parse(cache.fetchedAt)<15*60000)return Response.json({weather:cache,stale:false},{headers});
 try{
  if(!pending)pending=(async()=>{const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),10000);try{const r=await fetch(WEATHER_URL,{signal:controller.signal,headers:{Accept:'application/json'}});if(!r.ok)throw Error('Weather provider unavailable');return parseWeather(await r.json());}finally{clearTimeout(timer);}})().finally(()=>{pending=null;});
  cache=await pending;
  return Response.json({weather:cache,stale:false},{headers});
 }catch{
  if(cache&&currentWeatherValid(cache))return Response.json({weather:cache,stale:true,message:'暂未取得新天气，显示最近数据'},{headers});
  return Response.json({weather:null,message:'北京天气暂时无法读取'}, {status:503,headers});
 }
}
