CREATE TABLE `sync_state` (
	`id` text PRIMARY KEY NOT NULL,
	`payload` text NOT NULL,
	`updated` text NOT NULL
);
--> statement-breakpoint
ALTER TABLE `tasks` ADD `deleted` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `tasks` ADD `manual_override` integer DEFAULT 0 NOT NULL;