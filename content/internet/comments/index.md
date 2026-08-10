---
title: "Self hosting comments with Remark42"
date: 2026-08-10T00:00:00
draft: true
tags: ["vps", "website"]
---

Every post on this site has a comment box at the bottom, but I never wanted to hand that off to Disqus or one of the other ad-funded comment networks - the whole point of this website is to avoid exactly that kind of third-party tracking. `hugo-theme-stack`, the theme all my Hugo sites use, ships with support for a good handful of comment providers out of the box, most of them self-hostable. I picked **Remark42**, and ran it in a Docker container on my [mikr.us](/internet/mikrus/) VPS, next to everything else.

## Why Remark42

Remark42 is a single Go binary (with an official Docker image) that gives you a comment widget you embed on any page, plus an admin interface for moderation. A few things made it a good fit:

- No ads, no tracking, no dependency on an account with yet another company.
- One running instance can serve **multiple sites**, each identified by its own `site` id. Handy, since I run several Hugo sites under too-many-machines.com and didn't want a container per site.
- It supports several login methods - anonymous, email, GitHub, Google and others - configurable per instance.
- Storage is a local embedded database (Bolt), so there's no separate database container to run and back up.

## Running the container

I keep it in a `docker-compose.yml` on the VPS, alongside the other containers:

```yaml
services:
  remark42:
    image: umputun/remark42:latest
    container_name: remark42
    restart: unless-stopped
    environment:
      - SITE=selfhosting,advent,easy-dyi,random
      - REMARK_URL=https://comments.too-many-machines.com
      - SECRET=changeme-generate-a-real-secret
      - ADMIN_SHARED_ID=your-remark42-user-id
      - AUTH_EMAIL_ENABLE=true
      - AUTH_EMAIL_FROM=comments@too-many-machines.com
      - SMTP_HOST=smtp.example.com
      - SMTP_PORT=587
      - SMTP_USERNAME=your-smtp-user
      - SMTP_PASSWORD=your-smtp-password
      - SMTP_TLS=true
    volumes:
      - ./var:/srv/var
    ports:
      - "8080:8080"
```

The things worth customising:

- `SITE` is a comma-separated list of site ids, one per Hugo site that will use this instance. I currently have four: this blog (`selfhosting`), the [Advent of Code site](https://advent.too-many-machines.com/) (`advent`), the DIY site (`easy-dyi`) and a random-posts site (`random`). Two other sites under too-many-machines.com don't use it yet: the photo gallery runs a different Hugo theme without the comments partial, and the oldest site still runs on Pelican rather than Hugo.
- `REMARK_URL` is the public URL the container will be reached at - it has to match what ends up in DNS/Cloudflare.
- `SECRET` signs JWT tokens, generate a real random value and don't reuse it anywhere else.
- `ADMIN_SHARED_ID` is the user id (shown once you log in) that gets admin rights across all sites on the instance.
- `./var` is the only thing that needs backing up - it holds the Bolt database with every comment, across every site.

## Choosing email as the login method

Remark42 supports anonymous comments, but I turned that off - it's the path of least resistance for spam. Full OAuth apps (GitHub, Google) would mean registering and maintaining a separate app registration per provider for very little gain on a low-traffic blog. Email auth (a magic link sent to the commenter, no password) turned out to be the middle ground: enough friction to keep drive-by spam down, no account needed anywhere else, and only one thing to configure - an SMTP relay.

## Exposing it: comments.too-many-machines.com

The VPS only has an IPv6 address, so `comments.too-many-machines.com` goes through [Cloudflare](/internet/cloudflare/) exactly like the photo gallery does: an AAAA record pointed at the VPS with the proxy turned on. Cloudflare terminates TLS at the edge and forwards the request over IPv6 to the container, so I don't need to run Certbot for it, and I get the same DDoS/WAF protection as the rest of the domain for free.

## Wiring it into Hugo

The theme's comment partial reads its config from `hugo.toml`. Each site sets the same `host` (the Remark42 instance) but its own `site` id:

```toml
[params.comments]
  enabled = true
  provider = "remark42"

[params.comments.remark42]
  host = "https://comments.too-many-machines.com"
  site = "selfhosting"
  max_shown_comments = 100
  locale = "en"
  show_email_subscription = false
```

That's the whole change on the Hugo side - the theme takes care of loading the widget script and switching its theme (light/dark) to match the site. One thing to be aware of if your site has a cookie consent banner (`params.cookies.enabled` in the theme): the comments partial will detect it and hold off loading Remark42 until the visitor accepts functional cookies, showing a placeholder with a "manage preferences" button instead. None of my sites have that banner enabled yet, so comments just load directly.

## Result

Comments show up at the bottom of every post, moderation happens through the admin panel at `comments.too-many-machines.com/admin` (login with the email you set as `ADMIN_SHARED_ID`), and adding a fifth site to the same instance is just one more id in the `SITE` list plus the matching block in that site's `hugo.toml`.
