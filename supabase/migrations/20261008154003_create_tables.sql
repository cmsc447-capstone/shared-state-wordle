create table word (
    word    text    primary key check (word ~ '^[a-z]{5}$')
);

create table user (
    user_id     uuid        primary key default gen_random_uuid(),  -- can be given by sign up email
    username    text        not null unique,                        -- does not have to be unique
    created_at  TIMESTAMPTZ not null default now()
);

create table game (
    game_id     uuid        primary key default gen_random_uuid(),
    status      text        not null default 'started' check (status in ('started', 'waiting', 'finished')),
    created_at  TIMESTAMPTZ not null default now(),
    ended_at    TIMESTAMPTZ,
    check ((status = 'finished') = (ended_at is not null))
);

create table plays (
    user_id     uuid    not null references user(user_id) on delete cascade,
    game_id     uuid    not null references game(game_id) on delete cascade,
    turn_order  integer not null check (turn_order in (1, 2)),
    results     text    check (results in ('win', 'draw', 'loss')),
    primary key (user_id, game_id)
);

create table answer (
    game_id     uuid        primary key references game(game_id),
    word        text        not null references word(word),
);

-- This table tells us:
--  Who made the guess
--  What game the guess was for
--  What the guess was
create table guess (
    game_id     uuid        not null references game(game_id) on delete cascade,
    attempt_num integer     not null,
    user_id     uuid        not null references user(user_id),
    word        text        not null references word(word),
    feedback    text        not null.
    made_at     TIMESTAMPTZ not null default now(),
    primary key(game_id, attempt_num)
);