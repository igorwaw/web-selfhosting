---
title: "Remark42: self-hosting blog comments"
date: 2026-08-10T00:00:00
draft: false
tags: ["vps", "website"]
---

I've long time ago moved to statically generated websites. There's no server-side code running per request, no database - which is great for performance and security, and my sites don't change too often. But that means that comments can't work natively. If you want them on static websites, you need to host them elsewhere and load on the client side, with a bit of JavaScript.

That "somewhere else" is usually a third-party comment network like Disqus, but I didn't want to rely on external provider. Luckily, there are many self-hosted options available and integrating them with a Hugo site is quite simple.

I checked what's supported out of the box but my Hugo theme. **Remark42** seemed easy to use and had all the features I needed. In just a few minutes, I got it running in a Docker container on my [mikr.us](/internet/mikrus/) VPS.

## Why Remark42

A few things made it a good fit:

- A single Go binary, official Docker image, configuration by a handful of environment variables - hard to get simpler than that 
- No ads, no tracking, no dependency on another company.
- One running instance can serve **multiple sites**Handy, since I run several Hugo sites under too-many-machines.com.
- It supports several login methods - anonymous, email, GitHub, Google and others.
- Storage is a local embedded database (Bolt), so there's no separate database container.

## Running the container

Here's my almost-true Docker compose. Obviously, I didn't use *example.com* for my email.

```yaml
services:
  remark42:
    image: umputun/remark42:latest
    container_name: remark42
    restart: always
    ports:
      - "8080:8080"
    env_file:
      - .env
    environment:
      REMARK_URL: "https://comments.too-many-machines.com"
      SITE: "easy-dyi,selfhosting,photo,random,advent"
      ALLOWED_ORIGINS: "https://*.too-many-machines.com"

      # Anonymous comments — no login required
      AUTH_ANON: "true"

      # Email auth — magic link login
      AUTH_EMAIL_ENABLE: "true"
      AUTH_EMAIL_FROM: "mail@example.com"

      # SMTP — used for magic links and reply notifications
      SMTP_HOST: "example.com"
      SMTP_PORT: "465"
      SMTP_TLS: "true"

      # Reply notifications for commenters and admin
      NOTIFY_USERS: "email"
      NOTIFY_ADMINS: "email"

    volumes:
      - ./var:/srv/var

```

The `.env` file keeps more variables. One simply called `SECRET` containing a JWT token and two to configure SMTP authentication. I keep those separately, so I can put the compose file in Ansible, on GitHub, etc.

I think the options are self-explanatory, but just in case:

- `SITE` is a comma-separated list of site ids that will use this instance. I configured 5 here, although my photo gallery (which uses a different theme) doesn't have comments enabled yet.
- `REMARK_URL` is the public URL the container will be reached at.
- `SECRET` signs JWT tokens, generate a real random value and don't reuse it anywhere else.
- `AUTH_EMAIL_ENABLE`, `AUTH_EMAIL_FROM` - to enable authentication by email and set the From field of outgoing mails.
- SMTP options - required since I've chosen email authentication.
- `AUTH_ANON` - anonymous comments, enabled for now, I might change it if I start getting too much spam.

### Choosing email as the login method

Using OAuth apps (GitHub, Google) would mean registering and maintaining a separate app registration per provider and of course relying on external services. Email auth (a magic link sent to the commenter, no password) only needed one thing to configure - an SMTP relay.

## Exposing it: comments.too-many-machines.com

My VPS only has an IPv6 address, so `comments.too-many-machines.com` goes through [Cloudflare](/internet/cloudflare/) exactly like the photo gallery does: an AAAA record pointed at the VPS with the proxy turned on. Cloudflare terminates TLS at the edge and forwards the request over IPv6 to the container, so I also get TLS without running Certbot and DDoS/WAF protection. That's one compromise I had to make.

## Wiring it into Hugo

Enabling Remark42 comments only takes a few lines `hugo.toml`:

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

One important thing: Remark42 support is not part of Hugo itself, but of a specific theme. It is quite common, but not guaranteed, so check your themes if you want to use it.
