-- Author: Miguel Leon

-- This migration allows for games to be specified by their type
-- invite, match, or bot games (coming soon). This will allow for
-- player stats to be filtered by game types.

-- This added a new column to the game table "game_type"
-- the values for this table may be:
--  invite: For games created via an invite
--  match:  For games created by matchmaking
--  bot:    For games played against a bot
alter table game
    add column game_type text
    check (game_type in ('invite', 'match', 'bot'));

-- This should only affect the seed.sql since for games
-- created before this migration cannot be seperated by
-- type
update game
    set game_type = 'invite' where game_type is null;

-- All future games will require a game type to be specified
alter table game
    alter column game_type set not null;