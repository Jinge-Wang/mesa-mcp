# shmesa (optional bash helpers)

`shmesa` is MESA's own bash convenience script, on `PATH` when `load_mesa` has run. It can speed up
routine tasks, but **it is optional and known to have bugs** — never make a result depend on it, and
verify its effect afterward. Prefer the first-party MCP tools and explicit commands.

Call it through `mesa_env_shell` with a `path` outside `$MESA_DIR`.

## Subcommands

| Command | Use |
|---|---|
| `shmesa work <dir>` | Copy a fresh `star/work` directory to `<dir>`. |
| `shmesa cp <src> <dst>` | Copy a work dir without `LOGS`, `photos`, or caches. |
| `shmesa change <inlist> <param> <value> [...]` | Set inlist parameter(s); backs up to `.bak`. **Caveat:** normalizes indentation to 4 spaces and drops inline comments — for format-sensitive edits, patch the file directly per `inlist-namelist-rules.md`. |
| `shmesa defaults [col ...]` | Copy/augment `history_columns.list` / `profile_columns.list`. |
| `shmesa grep <string>` | Search the MESA **source** for a string (complements `mesa_docs_search`, which searches the docs). |
| `shmesa extras` | Fill in a full `run_star_extras.f90` template. |
| `shmesa zip` | Package a run directory for sharing. |
| `shmesa version` | Print the MESA version. |

Run any subcommand with `-h` for its own help.

## Guidance
- `shmesa grep` is genuinely handy for finding where something is defined in Fortran source.
- For inlist edits, prefer a precise direct patch; if you do use `shmesa change`, re-read the file
  afterward to confirm formatting and that the right line changed.
