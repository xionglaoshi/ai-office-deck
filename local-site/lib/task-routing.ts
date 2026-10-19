// Category decisions explicitly made by the owner outlive later source refreshes.
export const officeKinds=['tracking','risk','litigation','advice','payment'] as const;
export type OfficeKind=typeof officeKinds[number];
export type RoutingItem={id:string;kind:string;title:string;responsibility?:string;personalTask?:boolean};
export function routeAutomaticItem<T extends RoutingItem>(item:T,decisions:Record<string,string>={}):T {
 const fixed=decisions[item.id];
 if(fixed&&officeKinds.includes(fixed as OfficeKind))return {...item,kind:fixed};
 // Only an explicit personal assignment qualifies; a company-wide daily task does not.
 if(item.kind==='tracking'&&!item.personalTask)return {...item,kind:'risk'};
 return item;
}
