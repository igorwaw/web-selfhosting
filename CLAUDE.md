# web-selfhosting

Personal blog (Hugo static site, theme `hugo-theme-stack`) about self-hosting: at home and on the internet, plus general IT posts. Part of a family of sites under too-many-machines.com (see `menu.main` in `hugo.toml`); this one is `selfhosting.too-many-machines.com`.

## Content structure

- Posts are Hugo page bundles: `content/<section>/<slug>/index.md`, with any images co-located in the same directory (referenced by bare filename, e.g. `![alt](photo.png)`).
- Sections (`mainSections` in `hugo.toml`): `general`, `home`, `internet`.
  - `general` - meta posts about the site/approach itself (why self-host, tooling sidenotes, green IT, etc.)
  - `home` - self-hosting on the home network/NAS, not exposed to the internet.
  - `internet` - self-hosting on a public VPS/shared hosting, plus the infra around it (DNS, Cloudflare, email).
- Front matter fields, in this order:
  ```yaml
  ---
  title: "..."
  date: 2026-07-07T00:00:00
  draft: true
  tags: ["tag-one"]
  ---
  ```
  - **New posts must be created with `draft: true`.** The user flips it to `false` themselves when ready to publish - never set `draft: false` when scaffolding a new post.
  - `tags` uses the inline array style shown above, not YAML block-list style.
  - `date` should be a safely past timestamp on the day it's written - Hugo excludes future-dated content from the build by default, which silently drops the page.
- `content/_index.md` has hand-curated, categorized link lists (`## General information`, `## Self hosting at home`, `## Self hosting on the internet`) that must be manually updated when adding a new post - Hugo does not auto-generate this list. Match the existing ordering convention in each list (usually append at the end unless the user specifies a position).
- A banner/featured image needs an explicit `image: filename.png` front matter field pointing at a file in the same bundle (or a full URL). This theme's stock `_partials/helper/image.html` has **no fallback** to the first image in the bundle - unlike the sibling `web-random`/`web-diy` sites, which have a custom override that adds one. Don't assume that fallback exists here.

## Writing style

- British English spelling throughout (colour, organise, centimetre, etc.).
- Em dashes are not used - replace with a spaced hyphen ( ` - ` ).
- ALL CAPS words are intentional emphasis - never "fix" the casing.
- Preserve the author's voice/sentence structure/fragments when editing; only fix genuine typos, spelling, missing words, and repeated words automatically. Style, restructuring, and questionable factual claims are suggestions, not automatic edits.

## Build

- `hugo` from the repo root builds the site into `public/`; drafts and future-dated posts are excluded by default (no special flags needed for a "no drafts" build).
- For a clean rebuild: `rm -rf public && hugo`.
- This is one of several sibling Hugo/Pelican sites under `/home/big/code/` (`web-advent`, `web-diy`, `web-gallery`, `web-personal` (Pelican), `web-random`) - conventions here don't necessarily apply to those.
