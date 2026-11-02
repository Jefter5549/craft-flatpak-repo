#!/usr/bin/env python3
"""
Sync storytold / Craft applications from GitHub Releases into an OSTree repository
for hosting on GitHub Pages as a Flatpak remote.
"""

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

KNOWN_APPS = [
    "photocraft",
    "vectorcraft",
    "filmcraft",
    "lightcraft",
    "pdfcraft",
    "effectcraft",
    "designcraft",
    "figcraft",
    "texturecraft",
    "wordcraft",
    "soundcraft",
    "deckcraft",
    "cadcraft",
    "gridcraft",
    "craft-anything",
    "craft-launcher",
]

APP_TITLES = {
    "photocraft": "PhotoCraft",
    "vectorcraft": "VectorCraft",
    "filmcraft": "FilmCraft",
    "lightcraft": "LightCraft",
    "pdfcraft": "PdfCraft",
    "effectcraft": "EffectCraft",
    "designcraft": "DesignCraft",
    "figcraft": "FigCraft",
    "texturecraft": "TextureCraft",
    "wordcraft": "WordCraft",
    "soundcraft": "SoundCraft",
    "deckcraft": "DeckCraft",
    "cadcraft": "CADCraft",
    "gridcraft": "GridCraft",
    "craft-anything": "Craft Anything",
    "craft-launcher": "ArtCraft Launcher",
}

APP_DESCRIPTIONS = {
    "photocraft": "Professional open-source raster photo and image editor written in pure Rust.",
    "vectorcraft": "Vector graphics editor for illustrations, SVG assets, and digital art.",
    "filmcraft": "Non-linear video editor for multi-track composition and production.",
    "lightcraft": "Digital photography workflow software and RAW image development tool.",
    "pdfcraft": "Document reader, editor, annotator, and form processor for PDF files.",
    "effectcraft": "Visual effects, motion graphics, and procedural image compositing engine.",
    "designcraft": "Layout and desktop publishing software for print and digital publications.",
    "figcraft": "UI/UX interface prototyping and collaborative vector design tool.",
    "texturecraft": "3D procedural texture and PBR material authoring studio.",
    "wordcraft": "Distraction-free word processor and typography-first document editor.",
    "soundcraft": "Multi-track digital audio workstation (DAW) and audio processing tool.",
    "deckcraft": "Presentation software for modern slide decks, animations, and speaker notes.",
    "cadcraft": "Parametric 2D/3D CAD modeling and technical drafting suite.",
    "gridcraft": "Spreadsheet calculations, data visualization, and table management.",
    "craft-anything": "Extensible AI and procedural generation toolkit for creative pipelines.",
    "craft-launcher": "Official application manager and launcher for the storytold Craft Suite.",
}


def api_request(url, token=None):
    headers = {"User-Agent": "craft-flatpak-sync", "Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(url, target_path, token=None):
    headers = {"User-Agent": "craft-flatpak-sync"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp, open(target_path, "wb") as out_file:
        shutil.copyfileobj(resp, out_file)


def init_ostree_repo(repo_path):
    os.makedirs(os.path.join(repo_path, "objects"), exist_ok=True)
    os.makedirs(os.path.join(repo_path, "refs", "heads"), exist_ok=True)
    os.makedirs(os.path.join(repo_path, "refs", "tags"), exist_ok=True)
    os.makedirs(os.path.join(repo_path, "refs", "remotes"), exist_ok=True)
    os.makedirs(os.path.join(repo_path, "refs", "mirrors"), exist_ok=True)
    os.makedirs(os.path.join(repo_path, "state"), exist_ok=True)
    os.makedirs(os.path.join(repo_path, "tmp", "cache"), exist_ok=True)
    config_file = os.path.join(repo_path, "config")
    if not os.path.exists(config_file):
        with open(config_file, "w", encoding="utf-8") as f:
            f.write("[core]\nrepo_version=1\nmode=archive-z2\n")
        print(f"[+] Initialized OSTree archive-z2 repository at {repo_path}")


def get_all_target_repos(token=None):
    candidates = set(KNOWN_APPS)
    try:
        url = "https://api.github.com/orgs/storytold/repos?per_page=100"
        repos = api_request(url, token)
        for r in repos:
            name = r.get("name", "").lower()
            if "craft" in name or name in KNOWN_APPS:
                candidates.add(r.get("name"))
    except Exception as e:
        print(f"[!] Warning: failed to enumerate full org repo list: {e}. Falling back to known apps.")
    return sorted(list(candidates))


def discover_available_releases(repos, token=None):
    releases_data = {}
    for repo in repos:
        try:
            url = f"https://api.github.com/repos/storytold/{repo}/releases/latest"
            rel = api_request(url, token)
            assets = rel.get("assets", [])
            flatpak_assets = [a for a in assets if a.get("name", "").endswith(".flatpak")]
            if flatpak_assets:
                releases_data[repo] = {
                    "tag_name": rel.get("tag_name", ""),
                    "published_at": rel.get("published_at", ""),
                    "html_url": rel.get("html_url", ""),
                    "assets": flatpak_assets,
                }
                print(f"[+] Discovered {repo}: tag {rel.get('tag_name')} with {len(flatpak_assets)} flatpak asset(s)")
        except Exception:
            # Repo has no release or not found
            pass
    return releases_data


def get_installed_refs(repo_path):
    refs_root = os.path.join(repo_path, "refs", "heads", "app")
    app_refs = []
    if os.path.exists(refs_root):
        for root, _, files in os.walk(refs_root):
            for f in files:
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, os.path.join(repo_path, "refs", "heads"))
                app_refs.append(rel_path)
    return sorted(app_refs)


def generate_flatpakrepo_file(output_path, base_url):
    repo_url = base_url.rstrip("/") + "/repo/"
    content = f"""[Flatpak Repo]
Title=Storytold Craft Suite
Url={repo_url}
Homepage=https://github.com/storytold
Comment=OSTree Flatpak repository for Storytold ArtCraft applications
Description=Automated OSTree repository continuously synchronized with official GitHub Releases across x86_64 and aarch64.
gpg-verify=false
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] Generated {output_path}")


def generate_index_html(output_path, apps_info, base_url, last_updated):
    repo_url = base_url.rstrip("/") + "/repo/"
    flatpakrepo_url = base_url.rstrip("/") + "/craft.flatpakrepo"

    cards_html = []
    for app_id, data in sorted(apps_info.items(), key=lambda x: x[1].get("title", x[0])):
        title = data.get("title", app_id)
        desc = data.get("description", "Craft suite application.")
        tag = data.get("tag", "latest")
        arches = ", ".join(sorted(data.get("architectures", [])))
        install_cmd = f"flatpak install craft-repo {app_id}"
        repo_link = data.get("github_url", "https://github.com/storytold")

        cards_html.append(f"""
        <div class="card" data-title="{title.lower()}" data-id="{app_id.lower()}">
            <div class="card-header">
                <h3>{title}</h3>
                <span class="badge badge-version">{tag}</span>
            </div>
            <p class="app-desc">{desc}</p>
            <div class="meta-row">
                <span class="meta-label">App ID:</span>
                <code>{app_id}</code>
            </div>
            <div class="meta-row">
                <span class="meta-label">Arch:</span>
                <span class="badge badge-arch">{arches or 'all'}</span>
            </div>
            <div class="cmd-box">
                <code>{install_cmd}</code>
                <button class="copy-btn" onclick="copyText('{install_cmd}', this)" title="Copy command">📋</button>
            </div>
            <div class="card-footer">
                <a href="{repo_link}" target="_blank" rel="noopener">GitHub Releases ↗</a>
            </div>
        </div>
        """)

    cards_str = "\n".join(cards_html)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Storytold Craft Suite — Flatpak OSTree Repository</title>
    <style>
        :root {{
            --bg: #0f141c;
            --surface: #18202c;
            --border: #263445;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --text: #f1f5f9;
            --text-dim: #94a3b8;
            --code-bg: #0a0e14;
            --accent: #10b981;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.5;
            padding: 2rem 1rem;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        header {{
            text-align: center;
            margin-bottom: 2.5rem;
        }}
        h1 {{
            font-size: 2.4rem;
            font-weight: 800;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtitle {{
            color: var(--text-dim);
            font-size: 1.1rem;
            max-width: 700px;
            margin: 0 auto 1.5rem;
        }}
        .instruction-box {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2.5rem;
        }}
        .instruction-box h2 {{
            font-size: 1.25rem;
            margin-bottom: 0.75rem;
            color: #60a5fa;
        }}
        .step {{
            margin-bottom: 1rem;
        }}
        .step:last-child {{ margin-bottom: 0; }}
        .step-label {{
            font-weight: 600;
            color: var(--text-dim);
            font-size: 0.9rem;
            display: block;
            margin-bottom: 0.35rem;
        }}
        .cmd-box {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--code-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.6rem 0.9rem;
            overflow-x: auto;
        }}
        .cmd-box code {{
            font-family: "JetBrains Mono", "Fira Code", monospace;
            font-size: 0.9rem;
            color: #38bdf8;
            white-space: nowrap;
        }}
        .copy-btn {{
            background: transparent;
            border: none;
            color: var(--text-dim);
            cursor: pointer;
            padding: 0.2rem 0.5rem;
            margin-left: 0.5rem;
            font-size: 1rem;
            border-radius: 4px;
            transition: background 0.2s;
        }}
        .copy-btn:hover {{
            background: var(--border);
            color: var(--text);
        }}
        .search-bar {{
            width: 100%;
            background: var(--surface);
            border: 1px solid var(--border);
            color: var(--text);
            padding: 0.8rem 1.2rem;
            border-radius: 10px;
            font-size: 1rem;
            margin-bottom: 2rem;
            outline: none;
        }}
        .search-bar:focus {{
            border-color: var(--primary);
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            transition: transform 0.15s, border-color 0.15s;
        }}
        .card:hover {{
            transform: translateY(-2px);
            border-color: #3b82f688;
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 0.5rem;
        }}
        .card-header h3 {{
            font-size: 1.2rem;
        }}
        .app-desc {{
            color: var(--text-dim);
            font-size: 0.9rem;
            flex-grow: 1;
            margin-bottom: 1rem;
        }}
        .meta-row {{
            font-size: 0.85rem;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .meta-label {{
            color: var(--text-dim);
        }}
        .badge {{
            display: inline-block;
            font-size: 0.75rem;
            padding: 0.15rem 0.5rem;
            border-radius: 6px;
            font-weight: 600;
        }}
        .badge-version {{
            background: #1e3a8a;
            color: #93c5fd;
        }}
        .badge-arch {{
            background: #064e3b;
            color: #6ee7b7;
        }}
        .card .cmd-box {{
            margin-top: 0.5rem;
            margin-bottom: 0.75rem;
        }}
        .card-footer {{
            border-top: 1px solid var(--border);
            padding-top: 0.75rem;
            font-size: 0.85rem;
            text-align: right;
        }}
        .card-footer a {{
            color: #60a5fa;
            text-decoration: none;
        }}
        .card-footer a:hover {{
            text-decoration: underline;
        }}
        footer {{
            text-align: center;
            color: var(--text-dim);
            font-size: 0.85rem;
            margin-top: 3rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Storytold Craft Suite</h1>
            <p class="subtitle">Direct OSTree Flatpak repository powered by GitHub Pages. Continuously synced with official GitHub Releases across x86_64 and aarch64.</p>
        </header>

        <section class="instruction-box">
            <h2>Quick Setup</h2>
            <div class="step">
                <span class="step-label">1. Add this repository to Flatpak:</span>
                <div class="cmd-box">
                    <code>flatpak remote-add --user --if-not-exists craft-repo {flatpakrepo_url}</code>
                    <button class="copy-btn" onclick="copyText('flatpak remote-add --user --if-not-exists craft-repo {flatpakrepo_url}', this)">📋</button>
                </div>
            </div>
            <div class="step">
                <span class="step-label">2. Update remote metadata:</span>
                <div class="cmd-box">
                    <code>flatpak update --appstream</code>
                    <button class="copy-btn" onclick="copyText('flatpak update --appstream', this)">📋</button>
                </div>
            </div>
            <div class="step">
                <span class="step-label">3. Check for app updates any time via native Flatpak:</span>
                <div class="cmd-box">
                    <code>flatpak update</code>
                    <button class="copy-btn" onclick="copyText('flatpak update', this)">📋</button>
                </div>
            </div>
        </section>

        <input type="text" id="searchInput" class="search-bar" placeholder="🔍 Search apps by name or ID (e.g. PhotoCraft, vectorcraft)..." oninput="filterApps()">

        <div class="grid" id="appsGrid">
            {cards_str}
        </div>

        <footer>
            <p>Last synchronized: {last_updated} UTC</p>
            <p>Repository endpoint: <code>{repo_url}</code></p>
        </footer>
    </div>

    <script>
        function copyText(text, btn) {{
            navigator.clipboard.writeText(text).then(() => {{
                const orig = btn.innerText;
                btn.innerText = "✓";
                setTimeout(() => {{ btn.innerText = orig; }}, 1500);
            }});
        }}

        function filterApps() {{
            const query = document.getElementById("searchInput").value.toLowerCase();
            const cards = document.querySelectorAll(".card");
            cards.forEach(card => {{
                const title = card.getAttribute("data-title");
                const id = card.getAttribute("data-id");
                if (title.includes(query) || id.includes(query)) {{
                    card.style.display = "flex";
                }} else {{
                    card.style.display = "none";
                }}
            }});
        }}
    </script>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[+] Generated {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Synchronize storytold Craft suite releases to Flatpak OSTree repo")
    parser.add_argument("--repo-dir", default="public/repo", help="Path to OSTree repo directory")
    parser.add_argument("--public-dir", default="public", help="Path to public directory for GitHub Pages")
    parser.add_argument("--state-file", default="state.json", help="Path to state file tracking releases")
    parser.add_argument("--base-url", default="https://jefter5549.github.io/craft-flatpak-repo/", help="Base URL of GitHub Pages")
    parser.add_argument("--only-apps", default="", help="Comma-separated app names to sync (for testing/partial runs)")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN") or None

    os.makedirs(args.public_dir, exist_ok=True)
    init_ostree_repo(args.repo_dir)

    state = {}
    if os.path.exists(args.state_file):
        try:
            with open(args.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}

    target_repos = get_all_target_repos(token)
    if args.only_apps:
        only = [a.strip() for a in args.only_apps.split(",") if a.strip()]
        target_repos = [r for r in target_repos if r in only]

    print(f"[*] Scanning {len(target_repos)} target repositories for releases...")
    releases = discover_available_releases(target_repos, token)

    imported_any = False
    temp_dir = tempfile.mkdtemp(prefix="flatpak_sync_")

    try:
        for repo_name, rel in releases.items():
            tag = rel["tag_name"]
            assets = rel["assets"]

            repo_state = state.get(repo_name, {})
            imported_assets = repo_state.get("imported_assets", [])

            for asset in assets:
                asset_name = asset["name"]
                asset_id = f"{tag}_{asset_name}_{asset.get('size', 0)}"

                if asset_id in imported_assets:
                    continue

                download_url = asset["browser_download_url"]
                tmp_bundle = os.path.join(temp_dir, asset_name)
                print(f"[>] Downloading {asset_name} ({asset.get('size', 0) / (1024*1024):.2f} MB)...")

                try:
                    download_file(download_url, tmp_bundle, token)
                    print(f"[>] Importing {asset_name} into OSTree repo...")
                    cmd = ["flatpak", "build-import-bundle", "--update-appstream", args.repo_dir, tmp_bundle]
                    res = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    print(f"    {res.stdout.strip()}")
                    imported_any = True
                    imported_assets.append(asset_id)
                except Exception as e:
                    print(f"[!] Error importing {asset_name}: {e}")
                finally:
                    if os.path.exists(tmp_bundle):
                        os.remove(tmp_bundle)

            state[repo_name] = {
                "tag_name": tag,
                "published_at": rel["published_at"],
                "html_url": rel["html_url"],
                "imported_assets": imported_assets,
            }

        # Update summary and indexes
        print("[*] Running flatpak build-update-repo...")
        update_cmd = ["flatpak", "build-update-repo", "--generate-static-deltas", args.repo_dir]
        subprocess.run(update_cmd, check=True)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # Inspect refs to build app catalog
    installed_refs = get_installed_refs(args.repo_dir)
    print(f"[+] Total installed app refs: {len(installed_refs)}")

    # Map app IDs to metadata
    apps_info = {}
    for ref in installed_refs:
        parts = ref.split("/")
        # format: app/org.id/arch/branch
        if len(parts) >= 4 and parts[0] == "app":
            app_id = parts[1]
            arch = parts[2]

            # Try to match app name from app_id or repo
            matched_repo = None
            for r in target_repos:
                clean_r = r.replace("-", "").lower()
                clean_id = app_id.replace(".", "").replace("-", "").lower()
                if clean_r in clean_id:
                    matched_repo = r
                    break

            if app_id not in apps_info:
                apps_info[app_id] = {
                    "title": APP_TITLES.get(matched_repo, app_id.split(".")[-1].title()),
                    "description": APP_DESCRIPTIONS.get(matched_repo, f"Application {app_id}"),
                    "architectures": set(),
                    "tag": releases.get(matched_repo, {}).get("tag_name", "latest"),
                    "github_url": releases.get(matched_repo, {}).get("html_url", "https://github.com/storytold"),
                }
            apps_info[app_id]["architectures"].add(arch)

    for app_id in apps_info:
        apps_info[app_id]["architectures"] = list(apps_info[app_id]["architectures"])

    # Generate flatpakrepo and web page
    flatpakrepo_path = os.path.join(args.public_dir, "craft.flatpakrepo")
    generate_flatpakrepo_file(flatpakrepo_path, args.base_url)

    index_html_path = os.path.join(args.public_dir, "index.html")
    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    generate_index_html(index_html_path, apps_info, args.base_url, now_str)

    apps_json_path = os.path.join(args.public_dir, "apps.json")
    with open(apps_json_path, "w", encoding="utf-8") as f:
        json.dump(apps_info, f, indent=2)

    with open(args.state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    print("[✓] Synchronization complete!")


if __name__ == "__main__":
    main()
