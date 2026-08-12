# sounds/

Drop `.wav`, `.ogg`, or `.mp3` clips here (`.wav`/`.ogg` are the safe choices —
`.mp3` support depends on the local SDL_mixer build; an undecodable clip is
skipped with a warning rather than played).

When a new visitor is detected, one clip is chosen at random — at most once per
cooldown period (default 60 seconds, `--cooldown` to change), and avoiding
back-to-back repeats whenever more than one clip is available.

Source your own clips — the app does not fetch or bundle any audio.
