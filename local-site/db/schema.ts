import {sqliteTable,text,integer,index} from 'drizzle-orm/sqlite-core';
export const tasks=sqliteTable('tasks',{
 id:text('id').primaryKey(),userId:text('user_id').notNull(),title:text('title').notNull(),kind:text('kind').notNull(),category:text('category').notNull().default(''),priority:text('priority').notNull(),due:text('due').notNull().default(''),project:text('project').notNull().default(''),note:text('note').notNull().default(''),source:text('source').notNull().default('手动录入'),url:text('url').notNull().default(''),deleted:integer('deleted').notNull().default(0),manualOverride:integer('manual_override').notNull().default(0),done:integer('done').notNull().default(0),updated:text('updated').notNull(),
},t=>[index('idx_tasks_user').on(t.userId)]);

export const syncState=sqliteTable('sync_state',{id:text('id').primaryKey(),payload:text('payload').notNull(),updated:text('updated').notNull()});
