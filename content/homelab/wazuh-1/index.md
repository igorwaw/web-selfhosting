---
title: "Wazuh, part 1: what it is"
date: 2026-07-13T17:40:00
draft: false
tags: ["security"]
---

Wazuh is an open-source SIEM[^1]/XDR[^2]: agents on your hosts (and, via syslog, your network devices) send logs and events to a central manager. I used Wazuh at work, so part of the reason I'm running it at home is to keep those skills sharp. Let's not pretend it's a sensible choice for a typical home network. Unless you're a genuinely high-risk target, nobody is mounting a targeted attack against your home LAN. The realistic home threats are dealt much better by patching, network segmentation, backups and password hygiene. So, that goes into homelab category.

Wazuh is free - which made it a popular choice for small companies and government organisations which are forced to run SIEM, e.g. by EU regulations like [NIS2](https://digital-strategy.ec.europa.eu/en/policies/nis2-directive) for critical/important sectors, or [DORA](https://www.eiopa.europa.eu/digital-operational-resilience-act-dora_en) for financial entities. Certifications push the same way: [ISO/IEC 27001](https://www.iso.org/standard/27001) - specifically Annex A controls 8.15 (Logging) and 8.16 (Monitoring activities) in the 2022 revision. None of these specifically mention a SIEM by name, but auditors expect to see logs centralised and correlated.

[^1]: SIEM - Security Information and Event Management. The older concept: collect logs and events from lots of systems, correlate them against rules, send alerts.
[^2]: XDR - Extended Detection and Response. The newer concept: it adds automated response (blocking, isolating, killing a process) on top of detection. Wazuh, and most SIEMs marketed today, blur the line between the two.

## What it can do

You can think of it as an all-purpose dashboard for IT security. A single place to check a list of installed software, vulnerabilities found, suspicious events, hardening advice.

### Security events

At the core of it, it's log collection and correlation. The manager watches for patterns across all your agents and raises an alert when something matches a rule. That alone is useful after the fact: something went wrong, and you want to reconstruct what happened across several machines instead of grepping logs on each one by hand.

For Wazuh, "event" means "anything that's related to IT security". This ranges from completely normal things that might be useful for investigation (e.g. successful login), through slightly suspicious (failed login attempt, NIC entering promiscuous mode) to downright critical alert (malware detected). Which is why event rules have (configurable) severity: you want to be alerted over some level, and just store the ones below.

### Real-time response

It can also react to the events. Rules can trigger an active response - block an IP, kill a process, disable an account. Tempting, but dangerous: get a rule wrong and you'll lock yourself out of your own server, or block a legitimate client. Which also means a home server is a better place to gain experience writing the rules than the one serving real customers.

### File integrity monitoring

The syscheck module hashes a list of files and directories on a schedule (or in near-real time on Linux, via inotify) and alerts on anything added, changed or removed. Useful for catching tampering, but also just as an audit trail: if a config file changed at 3am and you didn't do it, you want to know.

### Vulnerability detection

The agent inventories what's installed (via syscollector) and the manager cross-references that against CVE feeds. This works well for anything your distro's package manager knows about - apt/dpkg packages get matched against exact versions with known CVEs. It also reaches a bit further than the OS: recent Wazuh versions can inventory and check some language-level package managers too, Python's pip among them, so an outdated Flask or Requests install doesn't go unnoticed.

It stops there, though. Anything that didn't come from a package manager Wazuh knows about - a binary built from source or installed with everyone's favourite `curl | sudo bash` won't be found.

### Rootkit detection

This is tricky. The whole point of a rootkit is to evade detection. Wazuh bundles some signatures for known rootkits, but mostly tries to look for anomalies:

- **Hidden processes.** Every Linux process has a directory under `/proc`. Rootcheck walks a range of PIDs and calls `kill(pid, 0)` on each - if the call succeeds (meaning the process exists and can receive a signal) but there's no matching `/proc/<pid>` entry, something is hiding it from the normal listing.
- **Hidden ports.** Same idea, applied to sockets: rootcheck tries to `bind()` to each port in turn. If binding fails, because something's already listening, but `netstat` shows nothing on that port, that's a listener hidden from the normal tool.
- **Network interfaces in promiscuous mode.** A normal server has no reason to listen for traffic that isn't addressed to it. Except if it does, which is increasingly common these days, with virtualisation and containers. You might need to reduce severity on this rule.
- **Hidden files.** Files that exist at the raw filesystem level but don't show up in a normal directory listing.

These rules are prone to false positives. A race condition is a classic reason: a process or file is created, picked up by a Wazuh check, then it's removed before the next part of the Wazuh check. In my experience, distributed frameworks triggered alerts every few days. But a real rootkit would be an extremely important signal, so these rules might be worth keeping even if it means investigating a false lead every week.

### Configuration assessment

The SCA (Security Configuration Assessment) module runs periodic checks against compliance frameworks - PCI DSS, HIPAA, GDPR, NIST 800-53 and so on. It checks stuff like password requirements, SSH configuration, filesystem permissions. None of those frameworks mean anything for a home network, they weren't ever directly relevant to my work. But you can treat them as a hardening guide, not a checklist you need to follow.

## Downsides of Wazuh

Mainly: it's complex to configure well. Out of the box it's noisy, and tuning it to a signal-to-noise ratio you can actually live with takes real effort - more on that in part 2.

## Alternatives

For completeness: on the free/open-source side there's OSSEC (which Wazuh itself is a fork of), Security Onion and the Elastic stack (Elasticsearch/Logstash/Kibana plus Elastic Security). On the commercial side, pretty much every enterprise vendor sells a SIEM - Splunk, Microsoft Sentinel, IBM QRadar and so on. All of them are expensive and assume a security team watching dashboards, which makes them even less suitable for home use.
