---
title: "Wazuh, part 1: what it is and why bother at home"
date: 2026-07-13T17:40:00
draft: true
tags: ["security"]
---

Wazuh is an open-source SIEM/XDR: agents on your hosts (and, via syslog, your network devices) ship logs and events to a central manager. The manager correlates them against a rule set, raises alerts and can trigger an automatic response. Think Splunk or Elastic Security's free relative - free as in beer, not as in "simple to run".

I use Wazuh at work, so part of the reason I'm running it at home is to keep those skills sharp on my own time, on a system I'm allowed to break. Let's not pretend it's a sensible choice for a typical home network though. Unless you're a genuinely high-risk target - a journalist, an activist, someone handling data that could get them hurt - nobody is mounting a targeted attack against your home LAN. The realistic home threats (a phished laptop, an unpatched IoT gadget, a reused password) are dealt with by patching, network segmentation and backups, not by log correlation. So: a fun project, not a recommendation.

## What it can do

At the core, it's log collection and correlation - the manager watches for patterns across all your agents and raises an alert when something matches a rule. That alone is useful after the fact: something went wrong, and you want to reconstruct what happened across several machines instead of grepping logs on each one by hand.

It can also react in real time, not just record. Rules can trigger an active response - block an IP, kill a process, disable an account - the moment they fire. Tempting, but dangerous: get a rule wrong and you'll lock yourself out of your own server, or block a legitimate client because it looked a bit like an attacker. I'd rather get an alert and act myself, at least until I trust a rule enough to automate it.

### File integrity monitoring

The syscheck module hashes a list of files and directories on a schedule (or in near-real time on Linux, via inotify) and alerts on anything added, changed or removed - `/etc`, SSH keys, cron files, whatever you point it at. Useful for catching tampering, but also just as an audit trail: if a config file changed at 3am and you didn't do it, you want to know.

### Vulnerability detection

The agent inventories what's installed (via syscollector) and the manager cross-references that against CVE feeds. This works well for anything your distro's package manager knows about - apt/dpkg packages get matched against exact versions with known CVEs. It also reaches a bit further than the OS: recent Wazuh versions can inventory and check some language-level package managers too, Python's pip among them, so an outdated Flask or Requests install doesn't go unnoticed.

It stops there, though. Anything that didn't come from a package manager Wazuh knows about - a binary built from source, something dropped in by hand, or (the big one on my setup) whatever's inside a Docker image - is invisible to this module. For a homelab that runs half its services in containers, that's a real gap: you'd want a separate image scanner (Trivy, Grype) to cover what Wazuh can't see.

### Configuration assessment

The SCA (Security Configuration Assessment) module runs periodic checks against bundled rule sets modelled on the CIS benchmarks, for the OS itself and for common services like SSH or the Docker daemon. Each check is also mapped to compliance frameworks - PCI DSS, HIPAA, GDPR, NIST 800-53 and so on. None of those frameworks mean anything for a home network, but the underlying CIS checks are a genuinely useful hardening checklist regardless of who you have to answer to.

## Downsides

Mainly: it's complex to configure well. Out of the box it's noisy, and tuning it to a signal-to-noise ratio you can actually live with takes real effort - more on that in part 2.

## Alternatives

For completeness, since none of these are any more sensible for home use than Wazuh is: on the free/open-source side there's OSSEC (which Wazuh itself is a fork of), Security Onion and the Elastic stack (Elasticsearch/Logstash/Kibana plus Elastic Security). On the commercial side, pretty much every enterprise vendor sells a SIEM - Splunk, Microsoft Sentinel, IBM QRadar and so on. All of them assume a security team watching dashboards, which rules them out for a home lab even more firmly than Wazuh does.
