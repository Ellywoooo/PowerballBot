# Powerball Rule Change Checklist

The Powerball number range changes from **1–10** to **1–14** on
**13 September 2026**.

## Automatic changes

The application now switches rules based on the current date:

- `config.get_powerball_max()` returns 10 before 2026-09-13 and 14 on or
  after that date.
- Powerball scoring uses the active number range automatically.
- Once the new range is active, Powerball scoring excludes draws from before
  2026-09-13 so statistics from the 1–10 game are not mixed with the 1–14
  game.

No manual edit is required to activate the new Powerball range.

## Manual work required before 2026-09-13

- [ ] Confirm the official Division 8 criteria from NZ Lotto's published
      rules.
- [ ] Implement the confirmed criteria in `scorer.determine_division()`.
- [ ] Remove the runtime warning in `scorer.py` once Division 8 is
      implemented.
- [ ] Re-run the full test suite and confirm nothing else assumes a
      seven-division system.
