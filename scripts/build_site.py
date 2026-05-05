#!/usr/bin/env python3
"""Build a static GitHub Pages site from common_params.toml."""

import html
import os
import re
from pathlib import Path

TOML_PATH = Path("src/config_project_template/configs/common_params.toml")
OUTPUT_DIR = Path("site")
OUTPUT_FILE = OUTPUT_DIR / "index.html"

GITHUB_REPO = "uasal/scoob_state"
DEFAULT_BRANCH = "develop"
TOML_BLOB_URL = (
    f"https://github.com/{GITHUB_REPO}/blob/{DEFAULT_BRANCH}/{TOML_PATH}"
)
TOML_EDIT_URL = (
    f"https://github.com/{GITHUB_REPO}/edit/{DEFAULT_BRANCH}/{TOML_PATH}"
)


def parse_toml_ordered(path: Path):
    """Parse a TOML file preserving order and duplicate table names.

    Yields (table_name, [(key, value_raw), ...]) tuples in file order.
    Leading content before the first table header is skipped.
    """
    table_name = None
    entries = []

    with open(path, encoding="utf-8") as fh:
        for line in fh:
            # Strip inline comments and trailing whitespace
            line_stripped = line.rstrip()

            # Match a top-level table header: [Name] or [Name.Sub]
            header_match = re.match(r"^\[([^\[\]]+)\]", line_stripped)
            if header_match:
                if table_name is not None:
                    yield table_name, entries
                table_name = header_match.group(1).strip()
                entries = []
                continue

            if table_name is None:
                # Still in the leading comment block
                continue

            # Skip blank lines and comment lines
            if not line_stripped or line_stripped.startswith("#"):
                continue

            # Parse key = value (value may contain = signs)
            kv_match = re.match(r'^([^=]+?)\s*=\s*(.*)$', line_stripped)
            if kv_match:
                key = kv_match.group(1).strip()
                value_raw = kv_match.group(2).strip()
                # Strip surrounding quotes for display
                if (
                    len(value_raw) >= 2
                    and value_raw.startswith('"')
                    and value_raw.endswith('"')
                ):
                    value_raw = value_raw[1:-1]
                elif (
                    len(value_raw) >= 2
                    and value_raw.startswith("'")
                    and value_raw.endswith("'")
                ):
                    value_raw = value_raw[1:-1]
                entries.append((key, value_raw))

    if table_name is not None:
        yield table_name, entries


def get_state(entries):
    """Return the state value from a list of (key, value) pairs."""
    for key, value in entries:
        if key.lower() == "state":
            return value
    return None


def render_entries(entries):
    """Render key/value pairs as an HTML definition list, skipping 'state'."""
    rows = [
        (k, v) for k, v in entries if k.lower() != "state"
    ]
    if not rows:
        return ""
    items = []
    for key, value in rows:
        items.append(
            f"    <dt>{html.escape(key)}</dt>"
            f"<dd>{html.escape(value) if value != '' else '<em>—</em>'}</dd>"
        )
    return "<dl>\n" + "\n".join(items) + "\n</dl>"


def render_tables(tables):
    """Render all tables as HTML according to their state."""
    parts = []
    for table_name, entries in tables:
        state = get_state(entries)
        entry_html = render_entries(entries)
        esc_name = html.escape(table_name)

        if state == "installed":
            parts.append(
                f'<section class="installed">'
                f"<h2>{esc_name}</h2>"
                f"{entry_html}"
                f"</section>"
            )
        elif state == "absent":
            parts.append(
                f'<section class="absent">'
                f"<details>"
                f"<summary>{esc_name} <span class=\"badge\">(absent)</span></summary>"
                f"{entry_html}"
                f"</details>"
                f"</section>"
            )
        else:
            label = html.escape(state) if state else "unspecified"
            parts.append(
                f'<section class="other">'
                f"<details>"
                f"<summary>{esc_name} <span class=\"badge\">({label})</span></summary>"
                f"{entry_html}"
                f"</details>"
                f"</section>"
            )

    return "\n".join(parts)


def build_html(tables, commit_sha, commit_short_sha, commit_date):
    """Build the full HTML page."""
    esc_sha = html.escape(commit_sha)
    esc_short = html.escape(commit_short_sha)
    esc_date = html.escape(commit_date)

    commit_url = f"https://github.com/{GITHUB_REPO}/commit/{commit_sha}"
    sha_link = (
        f'<a href="{html.escape(commit_url)}">{esc_short}</a>'
        if commit_sha != "unknown"
        else "unknown"
    )

    tables_html = render_tables(tables)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SCoOB State</title>
<style>
  body {{
    font-family: system-ui, -apple-system, sans-serif;
    max-width: 860px;
    margin: 0 auto;
    padding: 1.5rem;
    color: #222;
    background: #fafafa;
  }}
  header {{
    border-bottom: 2px solid #ddd;
    margin-bottom: 1.5rem;
    padding-bottom: 0.75rem;
  }}
  header h1 {{ margin: 0 0 0.25rem; }}
  header p {{ margin: 0.25rem 0; color: #555; font-size: 0.95rem; }}
  header a {{ color: #0969da; }}
  section {{ margin-bottom: 1rem; }}
  section.installed h2 {{
    font-weight: 700;
    color: #111;
    margin: 0.5rem 0 0.25rem;
    font-size: 1.1rem;
  }}
  section.absent details summary,
  section.other details summary {{
    cursor: pointer;
    font-size: 1.05rem;
    padding: 0.2rem 0;
  }}
  section.absent details summary {{ color: #999; }}
  section.other details summary {{ color: #666; }}
  .badge {{
    font-size: 0.8em;
    font-weight: normal;
    color: inherit;
  }}
  dl {{
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 0.1rem 1rem;
    margin: 0.3rem 0 0.3rem 1rem;
    font-size: 0.9rem;
  }}
  dt {{ font-weight: 600; color: #444; }}
  dd {{ margin: 0; color: #333; word-break: break-word; }}
  details > dl {{ margin-top: 0.5rem; }}
</style>
</head>
<body>
<header>
  <h1>SCoOB State</h1>
  <p>Current hardware configuration of the SCoOB testbed.</p>
  <p>
    Last updated: {esc_date} &mdash; commit {sha_link}
    &nbsp;|&nbsp;
    <a href="{html.escape(TOML_EDIT_URL)}">Edit on GitHub</a>
    &nbsp;|&nbsp;
    <a href="{html.escape(TOML_BLOB_URL)}">View source TOML</a>
  </p>
</header>
<main>
{tables_html}
</main>
</body>
</html>
"""


def main():
    commit_sha = os.environ.get("COMMIT_SHA", "unknown")
    commit_short_sha = os.environ.get("COMMIT_SHORT_SHA", "unknown")
    commit_date = os.environ.get("COMMIT_DATE", "unknown")

    tables = list(parse_toml_ordered(TOML_PATH))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    html_content = build_html(tables, commit_sha, commit_short_sha, commit_date)
    OUTPUT_FILE.write_text(html_content, encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE} ({len(tables)} tables)")


if __name__ == "__main__":
    main()
