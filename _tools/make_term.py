#!/usr/bin/env python3
"""Scaffold week pages for a new term from the UNC academic calendar.

Reads _tools/term.json and writes one post per teaching week, with the right
dates, weekday names, and no-class days already marked. Fill in the readings
afterwards; the layout, fonts and banner code apply automatically.

    python3 _tools/make_term.py            # dry run: print the plan and one sample page
    python3 _tools/make_term.py --write    # write the files into _posts/

Existing files are never overwritten unless you pass --force.
"""

import argparse
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
POSTS = ROOT / "_posts"
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def load_term(path):
    cfg = json.loads(path.read_text())
    cfg["first_class_day"] = dt.date.fromisoformat(cfg["first_class_day"])
    cfg["last_class_day"] = dt.date.fromisoformat(cfg["last_class_day"])
    cfg["no_class"] = {dt.date.fromisoformat(d): label for d, label in cfg["no_class"].items()}
    cfg["breaks"] = [
        {
            "start": dt.date.fromisoformat(b["start"]),
            "end": dt.date.fromisoformat(b["end"]),
            "label": b["label"],
        }
        for b in cfg["breaks"]
    ]
    if cfg.get("final_exam"):
        cfg["final_exam"]["date"] = dt.date.fromisoformat(cfg["final_exam"]["date"])
    return cfg


def in_break(day, cfg):
    for b in cfg["breaks"]:
        if b["start"] <= day <= b["end"]:
            return b
    return None


def build_weeks(cfg):
    """Group the term's meeting days into weeks, skipping break weeks entirely."""
    meeting = set(cfg["meeting_days"])
    weeks, week_no = [], 0
    monday = cfg["first_class_day"] - dt.timedelta(days=cfg["first_class_day"].weekday())
    while monday <= cfg["last_class_day"]:
        days = []
        for i in range(7):
            day = monday + dt.timedelta(days=i)
            if day < cfg["first_class_day"] or day > cfg["last_class_day"]:
                continue
            if DAY_NAMES[day.weekday()] not in meeting:
                continue
            if in_break(day, cfg):
                continue
            days.append(day)
        if days:
            week_no += 1
            weeks.append({"number": week_no, "monday": monday, "days": days})
        monday += dt.timedelta(days=7)
    return weeks


def page_for(week, cfg):
    """Return (filename, contents) for one week."""
    slug = f"{cfg['slug_prefix']}-week-{week['number']}"
    post_date = week["monday"] + dt.timedelta(days=cfg["post_date_offset_days"])
    lines = [
        "---",
        "layout: post",
        f'title:  "Week {week["number"]} - TITLE"',
        f"date:   {post_date} 01:00:00",
        f"permalink: {cfg['permalink_prefix']}week-{week['number']}",
        f'term:   "{cfg["term"]}"',
        "excerpt: ",
        "categories: ",
        "tags: ",
        "image:",
        "  feature: FIXME.jpg",
        "  # focus: 50% 50%   # optional crop: horizontal% vertical%",
        "bgContrast: dark",
        "bgGradientOpacity: darker",
        "syntaxHighlighter: no",
        "---",
        "",
        f"##### **Week {week['number']} - TITLE**",
        "",
        "---",
        "",
    ]
    for day in week["days"]:
        name = DAY_NAMES[day.weekday()]
        stamp = f"{day.month:02d}/{day.day:02d}"
        off = cfg["no_class"].get(day)
        if off:
            lines += [f"###### {name} {stamp} - **{off}**", ""]
        elif name == cfg.get("recitation_day"):
            lines += [f"###### {name} {stamp} - {cfg['recitation_label']}", "- **Play** ", ""]
        else:
            lines += [f"###### {name} {stamp} - TITLE", "- **Watch** ", "- **Read** ", ""]
        lines += ["---", ""]
    while lines and lines[-1] in ("", "---"):
        lines.pop()
    return f"{post_date}-{slug}.markdown", "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--term", default=str(ROOT / "_tools" / "term.json"))
    ap.add_argument("--write", action="store_true", help="write files into _posts/")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    args = ap.parse_args()

    cfg = load_term(pathlib.Path(args.term))
    weeks = build_weeks(cfg)

    print(f"{cfg['term']}: {cfg['first_class_day']} to {cfg['last_class_day']}")
    print(f"{len(weeks)} teaching weeks, meeting {', '.join(cfg['meeting_days'])}\n")
    for w in weeks:
        parts = []
        for day in w["days"]:
            stamp = f"{DAY_NAMES[day.weekday()][:3]} {day.month:02d}/{day.day:02d}"
            if day in cfg["no_class"]:
                stamp += " (no class)"
            parts.append(stamp)
        print(f"  Week {w['number']:<2} {', '.join(parts)}")
    for b in cfg["breaks"]:
        print(f"\n  {b['label']}: {b['start']} to {b['end']} (no week generated)")
    if cfg.get("final_exam"):
        fe = cfg["final_exam"]
        print(f"  {fe['label']}: {fe['date']} ({DAY_NAMES[fe['date'].weekday()]}) — add by hand")

    if not args.write:
        name, body = page_for(weeks[0], cfg)
        print(f"\n--- dry run. sample file: _posts/{name}\n")
        print(body)
        print("Run again with --write to create all files.")
        return

    written, skipped = [], []
    for w in weeks:
        name, body = page_for(w, cfg)
        path = POSTS / name
        if path.exists() and not args.force:
            skipped.append(name)
            continue
        path.write_text(body)
        written.append(name)
    print(f"\nwrote {len(written)} files into _posts/")
    for n in written:
        print("  +", n)
    if skipped:
        print(f"skipped {len(skipped)} existing files (use --force to overwrite)")
        for n in skipped:
            print("  =", n)


if __name__ == "__main__":
    sys.exit(main())
