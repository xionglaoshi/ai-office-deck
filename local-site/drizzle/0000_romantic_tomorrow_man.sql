CREATE TABLE `tasks` (
	`id` text PRIMARY KEY NOT NULL,
	`user_id` text NOT NULL,
	`title` text NOT NULL,
	`kind` text NOT NULL,
	`priority` text NOT NULL,
	`due` text DEFAULT '' NOT NULL,
	`project` text DEFAULT '' NOT NULL,
	`note` text DEFAULT '' NOT NULL,
	`source` text DEFAULT '手动录入' NOT NULL,
	`url` text DEFAULT '' NOT NULL,
	`done` integer DEFAULT 0 NOT NULL,
	`updated` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `idx_tasks_user` ON `tasks` (`user_id`);