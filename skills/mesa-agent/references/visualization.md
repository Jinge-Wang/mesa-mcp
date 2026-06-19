# Visualization (PGSTAR)

There are three ways to visualize a run, in order of robustness on a headless/VS Code host:

1. **Plot the data directly (best for a specific figure).** `mesa_plot_history(<work dir>, ...)` and
   `mesa_plot_profile(<work dir>, ...)` render a PNG with matplotlib and return it inline — no PGSTAR
   needed. Presets: `hr` (HR diagram), `kippenhahn` (convective regions + core masses), `abundance`
   (profile mass fractions). Pair with `mesa_analyze_history` / `mesa_analyze_profile` for the numbers.
2. **PGSTAR file output (best for MESA's own composite panels).** See below.
3. **A live auto-updating window.** `mesa_open_live_view(<work dir>)` opens a separate desktop window
   that follows the newest plot as the run proceeds — only where a display exists (`mesa_get_info`
   reports `WINDOW_CAPABILITY`); `mesa_close_live_view` stops it.

MESA's own on-screen PGSTAR **window** needs a working X11/Quartz display, and in a VS Code terminal /
remote / headless session it usually won't appear. `mesa_get_info` reports `PGSTAR_DISPLAY` and
`WINDOW_CAPABILITY` so you can see whether a display is even available.

**For MESA's PGSTAR panels, the robust approach is file output** — have MESA write plot PNGs to disk
during the run, then surface them.

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
