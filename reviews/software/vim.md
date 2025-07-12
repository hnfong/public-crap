# Neovim

- Overall Rating: ☆ ☆ ☆ ☆ ☆
- Verdict: Highly recommended for programmers with good taste.

- The modern variant of vim. Apparently the og vim author (may he rest in peace) needed some healthy competition to get the project going.
- Heavy reliance on lua, which is nice
- Terminal handling was completely revamped. No "sub-shell" in neovim. Run commands in a vim-terminal window instead
  - As of 2025, vim terminal still lacks quite a few features. Admittedly they're not a terminal project (which is complicated enough in itself) but still this makes for some rather subpar experience.

# Vim

- Used as main editor since ~2001 until switching to neovim in ~2021
- Even as early as 2002 I heard rumors saying I can't program without vim... (which is not that far from the truth)

## Pros

- Consistent text editing experience for 25+ years.
  - This is especially in stark contrast to people using other text editors, who stereotypically went from Emacs → UltraEdit → Notepad++ → Sublime Text → Atom → VS Code; changing editors every few years can be a chore.
- Allows speed and confidence when editing text.
- The value of consistency is much greater than (user) speed. The value of speed of the editor itself (no visible lags in most operations) cannot be understated though.

## Cons

- Impossible to move away from qwerty keyboard
- Adjustment needed to use "normal" text editors due to over-familiarity with vim keybinds
- Recently (2025) tried helix, and while it was very similar to vim, I realized I couldn't even temporarily switch to it without messing up my productivity, because I've become so dependent on the vim keybinds.
- btw, for me personally, I'd rather use default keybinds than so called "vim" keybinds because my muscle memory is activated once I start using vim keys, and any minor deviation will just make me expend conscious brain power asking myself whether I'm in a "real" vim or a "fake" vim-keybind environment.

## Plugins

I'm very light on plugins.

Telescope is one that I use (sparingly). I do have a couple other plugins but I usually configure them to get out of my way.

I do have a "wrapper" around nvim that does some magic (globbing files, opening multiple files, etc.). See [magic_open](https://github.com/hnfong/dotfiles/blob/master/bin/magic_open)
