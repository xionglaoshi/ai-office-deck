'use client';
import {useEffect,useState} from 'react';
import {Cloud,CloudSun,Sun,CloudRain,CloudSnow,CloudLightning,CloudFog} from 'lucide-react';
import {currentWeatherValid,weatherDescription,type CityWeather} from '@/lib/weather';
function WeatherIcon({code}:{code:number}){const Icon=code>=95?CloudLightning:code===45||code===48?CloudFog:code>=71&&code<=77||code===85||code===86?CloudSnow:code>=51?CloudRain:code===0?Sun:code===1||code===2?CloudSun:Cloud;return <Icon size={17} aria-hidden="true"/>;}
export default function CityWeather(){
 const [weather,setWeather]=useState<CityWeather|null>(null),[state,setState]=useState('loading');
 useEffect(()=>{
  const lifecycle=new AbortController();let loading=false;
  async function load(){if(loading)return;loading=true;try{const r=await fetch('/api/weather',{cache:'no-store',signal:lifecycle.signal});const d=await r.json() as {weather?:CityWeather;stale?:boolean};if(!r.ok||!d.weather||!currentWeatherValid(d.weather))throw Error('Unavailable');if(!lifecycle.signal.aborted){setWeather(d.weather);setState(d.stale?'stale':'ready');}}catch{if(!lifecycle.signal.aborted){setWeather(old=>old&&currentWeatherValid(old)?old:null);setState('unavailable');}}finally{loading=false;}}
  void load();const timer=setInterval(()=>{if(document.visibilityState==='visible')void load();},15*60000);
  const resume=()=>{if(document.visibilityState==='visible')void load();};document.addEventListener('visibilitychange',resume);
  return()=>{lifecycle.abort();clearInterval(timer);document.removeEventListener('visibilitychange',resume);};
 },[]);
 const valid=weather&&currentWeatherValid(weather);
 if(!valid)return <span className="city-weather weather-unavailable" role="status"><Cloud size={16} aria-hidden="true"/>北京 · {state==='loading'?'天气读取中…':'天气暂未更新'}</span>;
 const time=new Date(weather.observedAt).toLocaleTimeString('zh-CN',{timeZone:'Asia/Shanghai',hour:'2-digit',minute:'2-digit'});
 return <div className="city-weather" aria-label="北京天气" title={`当前${weatherDescription(weather.currentCode)}；体感${Math.round(weather.feelsLike)}°C；北京时间${time}天气数据；来源${weather.source}（天气模型）。`}><span className="weather-main"><WeatherIcon code={weather.todayCode}/>北京 · 今天{weatherDescription(weather.todayCode)}<span>当前 {Math.round(weather.temperature)}°C</span><span>{Math.round(weather.low)}～{Math.round(weather.high)}°C</span></span><span className="weather-meta">{time}{state==='ready'?'更新':'数据 · 暂未刷新'} <a href={weather.sourceUrl} target="_blank" rel="noreferrer">{weather.source}</a></span></div>;
}
