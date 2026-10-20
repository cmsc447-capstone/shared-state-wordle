-- IDs will come from Supabase Auth, remove default gen_random_id()
alter table player
    alter column player_id drop default;

-- Each row must be tied to an auth account
alter table player
    add constraint player_user_id_fkey
    foreign key (player_id) references auth.users (id)
    on delete cascade; -- When account is deleted delete entry in player table

-- [Trigger] player will be automatically created on sign-up
create function create_player()
returns triggger 