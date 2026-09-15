# Powerball Rule Change Checklist

The Powerball number range changed from **1–10** to **1–14** on
**13 September 2026**.

## Automatic changes

- `config.get_powerball_max()` returns 10 before 2026-09-13 and 14 on or
  after that date.
- Powerball scoring uses the active number range automatically.
- Once the new range is active, Powerball scoring excludes draws from before
  2026-09-13 so statistics from the 1–10 game are not mixed with the 1–14
  game.

## Division 8 (implemented)

Official Powerball Division 8 criteria (Lotto NZ):

> Match **2 Lotto numbers + the Bonus Ball + the Powerball** on the same
> line → fixed **$12** prize.

Implemented in `scorer.determine_division()`:

- [x] Confirmed official Division 8 criteria
- [x] Implemented in `determine_division()` (only when Powerball also matches,
      and only under the 1–14 rules)
- [x] Removed the runtime Division 8 warning
- [x] Tests cover Division 8 under new vs old rules
