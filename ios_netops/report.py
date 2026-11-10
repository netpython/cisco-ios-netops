"""Small report writers shared by the entry points."""

import csv
from html import escape
from pathlib import Path


def csv_report(path, columns, rows):
    def safe(value):
        if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
            return "'" + value
        return value

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows([safe(row.get(key)) for key in columns] for row in rows)


def html_report(path, title, columns, rows):
    def cell(value):
        return escape("" if value is None else str(value))

    headings = "".join(f"<th scope='col'>{cell(key)}</th>" for key in columns)
    body = "\n".join("<tr>" + "".join(f"<td>{cell(row.get(key))}</td>" for key in columns) + "</tr>"
                     for row in rows)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{cell(title)}</title>
<style>
body {{font: 16px system-ui; margin: 3rem auto; max-width: 1100px; padding: 0 1rem; color: #182638}}
table {{border-collapse: collapse; width: 100%; overflow-wrap: anywhere}}
td, th {{border-bottom: 1px solid #dce4ed; padding: .65rem; text-align: left; vertical-align: top}}
th {{background: #173454; color: white}}
</style>
<h1>{cell(title)}</h1><p>{len(rows)} result(s)</p>
<table><thead><tr>{headings}</tr></thead><tbody>{body}</tbody></table></html>
""", encoding="utf-8")
