/** Display-only: exact known account tokens; never mutate stored evidence. */
export function createWecomNames(users:Record<string,string>){
 const lookup=(userid:string)=>Object.hasOwn(users,userid)?users[userid]:userid;
 function display(text:string){
  // Preserve URLs, email addresses, absolute file paths and source identifiers.
  const protectedText=/((?:https?:\/\/|file:\/\/|[A-Za-z]:\\|(?<![A-Za-z0-9_.@-])\/)[^\s，；。<>]+|(?:source|report|wecom|userid|uuid):[^\s，；。<>]+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})/g;
  return text.split(protectedText).map((part,index)=>index%2?part:part.replace(/[A-Za-z0-9_.@-]+/g,token=>lookup(token))).join('');
 }
 return {display,lookup};
}
