import contacts from './wecom-users.json';
import {createWecomNames} from './wecom-name-utils';
export const wecomContacts=contacts;
export const {display:displayWecomNames,lookup:wecomName}=createWecomNames(contacts.users);
