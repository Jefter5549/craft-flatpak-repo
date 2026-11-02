# Storytold Craft Suite — Flatpak OSTree Repository

[![Sync Storytold Craft Suite to Flatpak OSTree](https://github.com/Jefter5549/craft-flatpak-repo/actions/workflows/sync-craft-repo.yml/badge.svg)](https://github.com/Jefter5549/craft-flatpak-repo/actions/workflows/sync-craft-repo.yml)

Automated OSTree repository continuously synchronized with official GitHub Releases of the [Storytold](https://github.com/storytold) ArtCraft application suite across all supported architectures (`x86_64` and `aarch64`).

Hosted directly on **GitHub Pages**, allowing native Flatpak installation and updates (`flatpak update`) without intermediaries or custom background daemons.

---

## 🚀 Quick Setup

### 1. Add the Repository
Run the following command to add this remote repository to your local user Flatpak configuration:

```bash
flatpak remote-add --user --if-not-exists craft-repo https://jefter5549.github.io/craft-flatpak-repo/craft.flatpakrepo
```

### 2. Update Metadata
Fetch the latest application stream metadata:

```bash
flatpak update --appstream
```

### 3. Install Any Application
Install any application by its ID or browse available applications:

```bash
# Browse all available applications
flatpak remote-ls craft-repo

# Install PhotoCraft
flatpak install craft-repo ai.storyteller.photocraft

# Install VectorCraft
flatpak install craft-repo ai.storyteller.vectorcraft

# Install FilmCraft
flatpak install craft-repo ai.storyteller.filmcraft

# Install ArtCraft Launcher
flatpak install craft-repo ai.storyteller.artcraft-launcher
```

### 4. Updating Applications
Whenever storytold releases a new version, GitHub Actions imports it automatically. You update your apps just like any standard Flatpak app:

```bash
flatpak update
```

---

## 📦 Supported Applications

| Application | Description | Architectures |
|---|---|---|
| **PhotoCraft** | Professional raster image and photo editor written in pure Rust | `x86_64`, `aarch64` |
| **VectorCraft** | Vector graphics editor for SVG art and illustrations | `x86_64`, `aarch64` |
| **FilmCraft** | Non-linear video editor for multi-track composition | `x86_64`, `aarch64` |
| **LightCraft** | Photography workflow & RAW image development studio | `x86_64`, `aarch64` |
| **PdfCraft** | Document editor, annotator, and reader for PDF files | `x86_64`, `aarch64` |
| **EffectCraft** | Visual effects, motion graphics, and procedural image compositor | `x86_64`, `aarch64` |
| **DesignCraft** | Layout and desktop publishing for print and digital media | `x86_64`, `aarch64` |
| **FigCraft** | Collaborative UI/UX interface design and prototyping tool | `x86_64`, `aarch64` |
| **TextureCraft** | Procedural 3D texture and PBR material authoring tool | `x86_64`, `aarch64` |
| **WordCraft** | Clean-room distraction-free word processor in pure Rust | `x86_64`, `aarch64` |
| **SoundCraft** | Digital audio workstation (DAW) and audio editing tool | `x86_64`, `aarch64` |
| **DeckCraft** | Modern presentation and slide deck software | `x86_64`, `aarch64` |
| **CADCraft** | Parametric 2D/3D CAD modeling and technical drafting | `x86_64`, `aarch64` |
| **GridCraft** | Fast spreadsheet and tabular data management | `x86_64`, `aarch64` |
| **Craft Anything** | AI-assisted procedural creative generation toolkit | `x86_64`, `aarch64` |
| **ArtCraft Launcher** | Suite launcher and manager for Craft applications | `x86_64`, `aarch64` |

---

## 🛠 How It Works

1. **Automation:** A GitHub Actions workflow runs on a daily schedule (and whenever triggered manually).
2. **Release Discovery:** It inspects all repositories under the `storytold` GitHub organization, dynamically discovering any repo that publishes `.flatpak` bundles.
3. **OSTree Ingestion:** The workflow imports each downloaded bundle using `flatpak build-import-bundle --update-appstream` into an OSTree `archive-z2` static repository structure.
4. **Delta & Summary Generation:** It runs `flatpak build-update-repo --generate-static-deltas` to compute binary deltas for bandwidth-efficient incremental client updates.
5. **Zero-Backend Hosting:** The repository is deployed straight to GitHub Pages (`actions/deploy-pages`), requiring zero VPS infrastructure or ongoing maintenance.
