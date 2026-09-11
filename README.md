# Burger Content Engine

Recording queue, week schedule, scripts and competitor research for **@HanneBurger** (THE FINALS).
Built to plan both channels eventually. HanneBurger is loaded, BurgerCam FPV is a slot waiting to be filled.

**Live site:** enable GitHub Pages under Settings, Pages, Deploy from branch, `main` / root.
It will then serve at `https://hannesolo94.github.io/Burger-content-engine/`.

## What is in here

| File | What it is |
|---|---|
| `index.html` | The whole site. Board, week schedule, playbook, card drawer. No build step, no dependencies. |
| `data.js` | All the content: cards, scripts, competitor rows. Edit this to change what the site shows. |
| `img/` | Competitor thumbnail strips, one per topic, four videos each. |

## How it works

**Board.** Five statuses: Ideas, Capture, My edit, Ready, Published. Drag a card between columns.
Moves are saved in that browser's local storage, so they follow the device, not the account.
"Copy board state" puts the current statuses on the clipboard as JSON, which is how a move made on
the laptop gets back into `data.js`.

**Cards.** Click one for why it sits where it sits, the clip list to hunt before playing, title options,
thumbnail direction, the competitor research behind it, and the full script where one exists.

**The week.** Seven nights, one idea each, with the clip list for that night. Night five is deliberately
a free night.

**Playbook.** The one rule, the two lanes, the title rules from the channel's own A/B results, and the
tweak ladder of one change per video.

## Competitor numbers

The `x` on every research row is views divided by subscribers, the same multiplier vidIQ shows.
It is there because a small channel beating its own size by ten times is a format that transfers
down to 116 subscribers, while a big channel's raw view count is not.

Pulled 11 September 2026 from a YouTube search with the this-year filter, across 13 queries matched
to the idea list. Re-run it from `D:\VideoAgent\research\finals_competitors\pull_competitors.py`.
