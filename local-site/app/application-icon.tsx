'use client';
import {useState} from 'react';
import {AppWindow} from 'lucide-react';
import icons from '@/public/app-icons/manifest.json';
const apps:Record<string,{name:string;icon:string}>=icons;
const aliases:Record<string,string>={'cn.org.hermesagent.desktop':'Hermes','com.kangfenmao.CherryStudio':'Cherry Studio','com.workbuddy.workbuddy-ai':'WorkBuddy','com.wps.lingxi':'WPS灵犀','cn.wps.yunboxtool':'WPS云文档','com.xiaomi.mimo.desktop':'MiMo'};
export default function ApplicationIcon({bundleId}:{bundleId:string}){
 const app=apps[bundleId],name=app?.name.replace('（通用图标）','')||aliases[bundleId]||'应用';
 const [failed,setFailed]=useState(false);
 return app?.icon&&!failed?<img src={app.icon} alt={name} title={name} width={26} height={26} loading="lazy" onError={()=>setFailed(true)}/>:<span className="history-app-generic" role="img" aria-label={name} title={name+' · '+bundleId}><AppWindow size={22} aria-hidden="true"/></span>;
}
