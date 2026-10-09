create table public.word (
    word    text    primary key check (word ~ '^[a-z]{5}$')
);

create table public.user (
    user_id     uuid            primary key default gen_random_uuid(),
    username    text            not null unique,
    created_at  TIMESTAMPTZ     not null default now()
);

create table public.table (
    game_id     uuid            primary key default gen_random_uuid(),
    status      text            not null default 'started' check (status in ('started', 'waiting', 'finished')),
    created_at  TIMESTAMPTZ     not null default now(),
    ended_at    TIMESTAMPTZ,
    
    check ((status = 'finished') = (ended_at is not null))
);

create table public.plays (
    user_id     uuid    not null references user(user_id)
        on update cascade
        on delete cascade,
    game_id     uuid    not null references game(game_id)
        on update cascade
        on delete cascade,
    --turn_order
    results
)