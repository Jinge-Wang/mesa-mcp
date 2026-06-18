# Visualization (PGSTAR)

MESA plots with PGSTAR. The on-screen PGSTAR **window** needs a working X11 display, and in a
VS Code terminal / remote / headless session it usually won't appear (even when `DISPLAY` is set,
the terminal may not forward X, or the PGPLOT device isn't interactive). `get_mesa_info` reports
`PGSTAR_DISPLAY` so you can see whether a display is even available.

**The robust approach is PGSTAR file output** — have MESA write plot PNGs to disk during the run,
then surface them.

## How to view a simulation's plots

1. **Enable file output before running.** `mesa_enable_pgstar_file_output(<work dir>)` sets
   `pgstar_flag` (&star_job) and `<plot>_file_flag` / `_file_dir` / `_file_interval` (&pgstar). With
   no `plots` argument it auto-detects the plots already defined as windows (`*_win_flag`); or pass
   `plots='Grid1'` etc. (You can also set these controls directly with `mesa_set_inlist_option`.)
2. **Run** (detached, with consent): `mesa_run(<work dir>)`.
3. **View as it runs / after.** `mesa_latest_plot(<work dir>)` returns the newest plot image
   (inline where the host renders images); `mesa_list_plots(<work dir>)` lists images with their
   model numbers.

## Notes
- A composite **`Grid`** plot (e.g. `Grid1`) packs several panels into one image — a good default
  for "show me the run at a glance."
- Plots are written every `_file_interval` models; raise it for fewer/larger steps.
- If the user specifically wants the live on-screen window and `DISPLAY` is set, it's an X-forwarding
  / device issue outside MESA — recommend file output instead.
