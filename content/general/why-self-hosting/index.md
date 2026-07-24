---
title: "Why Self hosting?"
date: 2023-04-14T17:30:00
draft: false
tags: ["intro"]
---

I think we're on the verge of a "back to the past" moment in IT. For the last 15 years or so, we heard that on-premises infrastructure is dead,
desktop software is not needed, everything should run on the cloud. Preferably as a collection of microservices, utilising NoSQL databases
and message queues.

Recently it changed. I keep seeing articles about the advantages of monolithic architecture, relational DBs, applications that don't embed the
browser, etc. Last but not least, more and more companies realised that the cloud is expensive, on-prem servers are back. 
There is also a growing trend among hobbyists to run self-hosted services at home.

Now, don't get me wrong. All of these technologies have good uses, but they are not a solution for everything.

## Good and bad reasons

**Education** is one good reason. Many IT professionals maintain a homelab to experiment with technology. Isn't it convenient when the lab can also do something useful?

**Privacy** is another good reason. I see some people declaring that privacy is lost anyway and they might as well share all their personal information.
I see others that meticulously control all their data to make sure it never leaves a system they control. I'm neither. I don't believe fully reclaiming
your data is even possible and the more you try to control it, the more you hit the law of diminishing returns. But some things can and should be
done.

How about **owning your data**? A cloud service can be discontinued at any moment. Small companies go out of business, corporations
decide to cut the margins. Especially Google is famous for killing many of their projects, even if they achieved a moderate success.
It is also a known problem with IoT devices - many people discovered their smart bulb or socket is no longer smart (or doesn't work at all)
when it can't connect to the manufacturer's servers. 

**Less reliance on the internet**. OK, I'm not making any plans for living offline, that would be way too uncomfortable. But if I have most
of my data and software locally, I can live with slow or unreliable connection. And yes, it is an issue even in the most developed regions
of the world. Perhaps you would like to live in a village or spend some time in an RV or a boat one day? Outside the towns, mobile
internet is often the only option. Just a few kilometres from the cell tower and you don't even get that. 

**Cutting cost is not a good reason**. You may get some savings, but it's not guaranteed. You might cut down on cloud subscriptions,
but add the cost of hardware and electricity. Not to mention the time spent on configuring all this.

## Self hosting vs homelab

IT people are weird. Accountants don't reconcile a second set of books for fun, neurosurgeons almost never do brain surgery at home. Hand someone a career debugging servers, though, and a suspicious number of them go home and set up more servers. I'm one of them.

I mention self hosting and homelab on this blog. I do both, often on the same server, but they're not the same thing.

- **Self hosting** is about running a service that's actually useful - storage, backups, DNS.
- **Homelab** is about experimenting for its own sake. Running Kubernetes at home makes little practical sense.

The distinction isn't always clear and arguably, all self hosting is educational and not very practical.

## Where am I now?

I plan to write this as a step-by-step guide of my journey to self-hosting, like I'm starting from scratch. That is not strictly true. 
I'm already running some of the services or I did that in the past. I'm going to start with the basic infrastructure first and then 
add new services or better, tidier versions of those I'm already running.
