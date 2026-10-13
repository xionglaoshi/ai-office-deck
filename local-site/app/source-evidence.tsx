'use client';
import {useState} from 'react';
import {displayWecomNames} from '@/lib/wecom-names';
export default function SourceEvidence({id,version}:{id:string;version?:string}){
 const [text,setText]=useState(''),[error,setError]=useState('');
 async function load(){if(text)return;try{const r=await fetch('/api/tasks?source='+encodeURIComponent(id)+(version?'&version='+encodeURIComponent(version):''),{cache:'no-store'});const data=await r.json() as {source?:{note:string;sourceDate?:string;reporter?:string};message?:string};if(!r.ok||!data.source)throw Error(data.message||'来源档案读取失败');setText('原始日期：'+(data.source.sourceDate||'未标注')+'；报告人：'+displayWecomNames(data.source.reporter||'未标注')+'（原始标注：'+(data.source.reporter||'未标注')+'）\n'+data.source.note);}catch(e){setError((e as Error).message);}}
 return <details onToggle={e=>{if(e.currentTarget.open)void load();}}><summary>查看已保存来源正文</summary>{error?<p role="alert">{error}</p>:<p className="full-note">{text||'正在读取来源正文…'}</p>}</details>;
}
