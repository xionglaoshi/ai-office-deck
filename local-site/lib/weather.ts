export const WEATHER_URL='https://api.open-meteo.com/v1/forecast?latitude=39.90&longitude=116.40&current=temperature_2m,apparent_temperature,weather_code,is_day&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=Asia%2FShanghai&forecast_days=1';
export type CityWeather={city:string;date:string;temperature:number;feelsLike:number;low:number;high:number;currentCode:number;todayCode:number;observedAt:string;fetchedAt:string;source:string;sourceUrl:string};
export function chinaDate(now:number){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(now);}
export function currentWeatherValid(weather:CityWeather,now=Date.now()){
 const age=now-Date.parse(weather.observedAt);
 return weather.date===chinaDate(now)&&Number.isFinite(age)&&age>=-30*60000&&age<=3*3600000;
}
export function parseWeather(input:unknown,now=Date.now()):CityWeather{
 const d=input as any,c=d?.current,day=d?.daily;
 const numbers=[c?.temperature_2m,c?.apparent_temperature,day?.temperature_2m_min?.[0],day?.temperature_2m_max?.[0],c?.weather_code,day?.weather_code?.[0]];
 if(d?.timezone!=='Asia/Shanghai'||numbers.some(v=>typeof v!=='number'||!Number.isFinite(v))||typeof c?.time!=='string'||!/^[0-9-]{10}T\d{2}:\d{2}$/.test(c.time)||day?.time?.[0]!==chinaDate(now))throw Error('Weather data invalid or out of date');
 const weather:CityWeather={city:'北京',date:day.time[0],temperature:c.temperature_2m,feelsLike:c.apparent_temperature,low:day.temperature_2m_min[0],high:day.temperature_2m_max[0],currentCode:c.weather_code,todayCode:day.weather_code[0],observedAt:c.time+':00+08:00',fetchedAt:new Date(now).toISOString(),source:'Open-Meteo',sourceUrl:'https://open-meteo.com/'};
 if(!currentWeatherValid(weather,now)||weather.low>weather.high)throw Error('Weather data invalid or out of date');
 return weather;
}
export function weatherDescription(code:number){
 const descriptions:Record<number,string>={0:'晴',1:'晴间多云',2:'多云',3:'阴',45:'雾',48:'雾凇',51:'小毛毛雨',53:'毛毛雨',55:'较强毛毛雨',56:'冻毛毛雨',57:'较强冻毛毛雨',61:'小雨',63:'中雨',65:'大雨',66:'冻雨',67:'较强冻雨',71:'小雪',73:'中雪',75:'大雪',77:'雪粒',80:'小阵雨',81:'阵雨',82:'强阵雨',85:'小阵雪',86:'阵雪',95:'雷雨',96:'雷雨伴冰雹',97:'强雷雨',99:'强雷雨伴冰雹'};
 return descriptions[code]||'天气状况待更新';
}
