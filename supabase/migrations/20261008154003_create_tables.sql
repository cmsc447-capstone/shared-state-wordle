create table word (
    word    text    primary key check (word ~ '^[a-z]{5}$')
);

create table user (
    user_id     uuid            primary key default gen_random_uuid(),
    username    text            not null unique,
    created_at  TIMESTAMPTZ     not null default now()
);

create table game (
    game_id     uuid            primary key default gen_random_uuid(),
    status      text            not null default 'started' check (status in ('started', 'waiting', 'finished')),
    created_at  TIMESTAMPTZ     not null default now(),
    ended_at    TIMESTAMPTZ,
    
    check ((status = 'finished') = (ended_at is not null))
);

create table plays (
    user_id     uuid    not null references user(user_id)
        on update cascade
        on delete cascade,
    game_id     uuid    not null references game(game_id)
        on update cascade
        on delete cascade,
    --turn_order
    results     text    check(results in ('win', 'draw', 'loss')),

    primary key (user_id, game_id)
);

create table answer (
    game_id     uuid    primary key references game(game_id)
        on update cascade,
    word      text    not null references word(word)
);

create table guess (
    game_id         uuid        not null references game(game_id)
        on update cascade
        on delete cascade,
    attempt_number  INTEGER     not null,
    feedback        TEXT        not null,
    made_at         TIMESTAMPTZ     not null default now(),

    primary key(game_id, attempt_number)
);

create table made_by (
    game_id         uuid        not null,
    attempt_number  INTEGER     not null,
    user_id         uuid        not null references player(player_id),

    primary key (game_id, attempt_number),
    foreign key (game_id, attempt_number) references guess (game_id, attempt_number)
);

create table game_guess (
    game_id         uuid        not null,
    attempt_number  INTEGER     not null,

    primary key (game_id, attempt_number),
    foreign key (game_id, attempt_number) references guess(game_id, attempt_number)
);

create table guessed (
    game_id         uuid        not null,
    attempt_number  INTEGER     not null,
    word            TEXT        not null references word(word),

    primary key(game_id, attempt_number),
    foreign key(game_id, attempt_number) references guess(game_id, attempt_number)
);