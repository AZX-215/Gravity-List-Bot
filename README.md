# Gravity List Bot

**Gravity List Bot** is a Discord bot designed to help your community:

- **Track categorized lists** (headers, bullet notes, alliances, enemies, owners)
- **Run real‑time countdown timers** as standalone or embedded in lists
- **Manage Ark Ascended generator timers** (Tek & Electrical) with auto‑updating dashboards
- **Deploy unified dashboards** via a single `/lists` command
- **Persist all data** via JSON files in a mounted volume (`lists/` directory)

## Key Commands

### Unified Dashboard
- `/lists name:<list>`: deploys or updates a regular or generator list embed

### Regular Lists
- `/create_list name:<list>`
- `/add_name list_name:<list> name:<entry> category:<cat> comment:<optional>`
- `/edit_name list_name:<list> old_name:<old> new_name:<new> new_category:<cat> new_comment:<optional>`
- `/remove_name list_name:<list> name:<entry>`
- `/delete_list name:<list>`
- `/add_text list_name:<list> text:<note>`
- `/add_header list_name:<list> header:<text>`

### Inline Timers in Lists
- `/add_timer_to_list list_name:<list> name:<timer> hours:<int> minutes:<int>`

### Standalone Timers
- `/create_timer name:<timer> hours:<int> minutes:<int> [role:<@role>]`
- `/pause_timer name:<timer>`
- `/resume_timer name:<timer>`
- `/delete_timer name:<timer>`
- `/resync_timers` (admin)

### Generator Timers
*Implemented in `gen_timers.py`*
- `/create_gen_list name:<list>`
- `/add_gen tek list_name:<list> entry_name:<name> element:<int> shards:<int>`
- `/add_gen electrical list_name:<list> entry_name:<name> gas:<int> imbued:<int>`
- `/edit_gen list_name:<list> old_name:<old> [--new_name:<new>] [--gen_type:<Tek|Electrical>] [--element:<int>] [--shards:<int>] [--gas:<int>] [--imbued:<int>]`
- `/remove_gen list_name:<list> name:<entry>`
- `/delete_gen_list name:<list>`
- `/set_gen_role list_name:<list> role:<@role>`
- `/list_gen_lists`
- `/resync_gens` (admin)

### Utilities
- `/list_all` (admin): lists all regular & generator lists
- `/help`: shows this message

## Setup

1. Clone, install requirements, configure `.env`.
2. Run `python bot.py`.
