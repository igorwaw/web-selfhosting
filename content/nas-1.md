Title: Storage server, part 1: hardware
Date: 2023-04-14 17:35
Status: published
Tags: storage

A house is not a home without a NAS. OK, maybe I'm not really that emotionally attached to my file server,
but it's one of the first things you need if you want to rely less on the cloud. What can you use it for?

- sharing files between the devices,
- storing large data you create, such as photos and videos - laptops and even desktops tend to have
smallish SSD drives these days, not really suitable for media content,
- backups,
- storing music, movies and TV shows.

You can also use the same machine as an all-purpose server. With virtualization and containers, it's easy to
separate different workloads (you can run everything on the same OS, but the system might get messy).

I'm trying to keep my IT green (see separate sidenote for details), which in short means:

- the fewer boxes running 24/7, the better,
- prefer old hardware to new one.


## Commercial vs DIY

The easiest option is to buy an off-the-shelf NAS such as Synology or Qnap. I had one in the past. The good thing
about them is you can get them up and running in less than an hour and without much knowledge.
Just install disks, plug it to the network and answer a few questions in the web UI. Even though I had the
knowledge (it was actually my second NAS, the first one being a DIY), I chose Synology for convenience.

But the cheap models only have 2 disk bays, very little RAM and a pathetic CPU. They work fine as basic
file servers, but doing anything in the GUI is an exercise in frustration. Click, wait for 10 seconds until it
responds, click, wait again. You'll quickly miss the command line. I used RAID1 for storage so when I ran
out of space, the only option would be to replace both disks with the bigger ones, old disks would be
useless. Enough, back to the DIY.


## To USB or not to USB?

I also have a drawer full of USB HDDs. Few were mine, most I literally inherited. Many of them are small
and not really worth bothering, but about a dozen are 1TB. I experimented with a NAS running on
a single-board system (Odroid C1+, similar to Raspberry Pi 3 but much cheaper) and a small-form PC (Dell
Wyse) and decided I REALLY don't want a NAS on USB drives. You can run one or two semi-reliably, but
the more you have, the probability of problems approaches 1. Sometimes the plug moves in the socket and you
end up with a corrupt filesystem. Or the cable cannot handle the power. Or the disks run fine when you
initially connect them one by one, but during the next reboot they will start all at once drawing too
much current (yes, I tried a powered USB hub)  and only half of them will show up. Of course, you can't
have RAID on USB (technically, it is possible, the system wouldn't stop you, but it's a really bad idea if your
drives can disappear at any moment). 

## Choosing hardware

Many people choose an advanced filesystem such as ZFS for the storage server. They have some advantages
(eg. built-in RAID and snapshots), but most of them can be imitated with underlying layers such as MD and LVM. And they
need a lot of RAM and CPU power, in some cases also SSD for cache.

If you can live with plain old filesystems, you don't really need much. Any reasonably modern (say, less than 15 years)
mainline CPU from Intel or AMD is already way more powerful than the puny processor in commercial NAS, even most
Atoms are. Faster CPUs generally draw more power and require more (louder) cooling,  but that's only true if you compare 
models from the same generation. Very old CPUs also couldn't scale down the power when idle (or not so effectively).
Rule of the thumb for Intel CPUs: if it's called "Core i-some number" OR if it's called something else like Pentium or Xeon,
but it's the same microarchitecture as "Core i-something"  (check Wikipedia), it should be OK. Xeons are server CPUs, with high
performance, bigger cache and more cores. In the past they were power hogs, these days some of them can scale
down quite well. Check the specs to be sure.

BTW, I wish Intel used a more consistent naming convention as they did in the previous century. Now Core i5 is supposed
to be faster than i3, but it's not true if i3 is several generations younger. Not to mention Pentium and Celeron brands which
don't really mean anything as the same name is used for 20 or 30 years.

As for RAM, even a small one like 1 GB is OK for the start, Linux would only need few dozen MB anyway and use the rest for
disk cache. You should connect NAS using Ethernet, not Wifi. 1Gbit is a reasonable choice, 100Mbit can sometimes slow
things down (but if you have an old LAN, don't worry too much). Faster than 1Gbit is not needed for a generic file storage.

But I also wanted to run other services on the same box, in containers and VMs. To sum up: I was checking the second-hand
market for a motherboard with:

- a 64-bit CPU with virtualization extensions
- preferably a home or low-power model rather than Xeon or Core i7,
- at least 1GB of RAM with an option to expand to 8GB
- multiple SATA ports,
- USB3 ports,
- PCI Express slots for further expansion if needed.

## The plan

So, I have two 3TB 3.5" disks from my Synology. I have a bunch of external disks, some of which could be removed
from the case. The process is called shucking and it's quite popular among self-hosters. External drives are often
cheaper than internal ones, despite the extra cost of the enclosure. It's for a reason: they are built with lower
quality components (or they failed QA tests), they might live for years if they are only used occasionally, but won't
last long with more intensive use. But I already got them and I'm prepared that any drive can fail at any moment.
I might as well use them for the next year or two, when they all fail I will replace them with larger and more reliable
drives.

Unfortunately, some USB drives can't be shucked. They don't have SATA and power connectors and the USB port is
soldered directly onto the board. So here's the plan:

- I will use 2x3TB 3.5" HDDs as RAID1, for the generic storage, 
- I will connect internally as many 2.5" drives as I can, the rest externally, and use them for videos, since the files wouldn't change often I can skip RAID and instead use Snapraid (see later parts)
- One of the 2.5" will be used for backups of my other machines

These 2.5" will be off most of the time which is probably the right usage pattern for USB drives.

## A case for the proper case

I need a case that can hold many drives. The cheapest option would be a second-hand server in a 19" rack-mountable
case. They look very cool and in the past I wanted to have one at home, but then I worked in a datacenter and discovered
how much noise they make. And their power usage is enormous. I need something more suitable for home:
a case with many drive bays, but using a standard power supply, cooling and motherboard.

Searching the internet I found they are relatively easy to buy in the USA, but not in the UK where I live. It's quite a niche product after
all, very few PCs use more than 1 or 2 drives. Those that can be found are twice as expensive as in the States, buying straight
from the US vendor means paying for shipping and long waiting.

But I found one interesting option: *Kolink Satellite Cube*. According to the specs, it has 4x 2.5" and 3x 3.5" bays.
It holds a mini-ITX motherboard - not perfect, but OK. It's cheap and quite small. I ordered the case and searched for the MB.
Mini-ITX are hard to find, but I found a great second-hand option, with 8GB RAM, a Pentium CPU that's really a 4th generation
Intel Core and best of all, 6 SATA ports!

When I got the case, I discovered the specs were wrong in two ways. One, it can hold a mini-ITX or a micro-ATX
motherboard, the latter is slightly larger and much more popular. Fine, if I knew that maybe I would have found 
the motherboard quicker, but I'm satisfied with the one I got. But the other thing was worse. Turned out I can
have 4x 2.5" OR 3x 3.5", but not both (some combinations possible: side frame can hold 1x3.5" or 2x2.5", top frame
two disks of any size, pity there's no second side frame cause there's enough space for it).
What a disappointment! But anything with more bays would be twice as expensive, much larger and I would have
to wait again. I'll use 2x 3.5" and 2x 2.5" for now and maybe mod the case in the future. Or more likely, I'll just replace
the drives with bigger ones.

Finally, I bought some SATA cables and a PSU. The smallest I could find was 450W and even that was difficult,
probably because the only people who build PCs these days are gamers and crypto miners. I chose one that claims 90% efficiency
when running with 10%-20% of the max load.

## The system drive

Should you place your OS with the data or use a separate disk? Both ways have some pros and cons.

Sometimes you are forced to use a separate drive. If you use an old motherboard, it might not support booting
from large disks - but once the operating system loads, it will access the drives just fine. 

Most, if not all, NAS-specific distros require a separate system disk. Decoupling data from OS will generally
make your life easier in the long run: you can replace data disks if  they are too small, or you can move data
to another server. You can also run the system from an SSD which is much faster - it doesn't make much
difference if you use it only for NAS, but a huge one if you also want to host VMs or containers.

On the other hand, keeping OS with the data means you don't waste precious drive bay in the case. And if your data is on
RAID, the system is also protected from the drive failure.

After some considerations, I decided to use an SSD scavenged from an old laptop. Since my case has fewer bays
than I expected, I just let it hang on the power cables. There are no moving parts anyway and it's very light. Will it get
adequate cooling if it's in the part of the case that wasn't supposed to hold drives? Should be, there's still more airflow
than inside the laptop.

Tip: if you want to use a separate drive, but don't want to waste drive bay/SATA port/money on the extra disk,
you can install Linux on a USB stick. Just remember they are way slower even than HDDs and wear out quickly.
You should try to use them read-only (possible but tricky, requires combining read-only fs with a writable ramdisk on top
of it, eg. aufs) or almost read-only (eg. disable swap, redirect logs to an external system). You can even install the stick
internally - motherboards have USB connectors for use with the case's front ports. 

Is the lack of RAID a real problem? The system disk is easy to backup. If it fails, I can replace the drive and restore
the system from an image in minutes. And it's a home system, so the risk of some downtime is acceptable.

## Some assembly required

The last time I built a PC, it had a 366 MHz CPU and 128MB of RAM and it wasn't because I used second-hand parts.
But it's not a rocket science. I screwed the board in, connected all the cables, turned on the power and... nothing
happened. I checked the cables - still nothing. Took everything out of the case, connected only PSU to the
motherboard, shorted the "power button" pins - same. That's what you get with the used hardware, right?

But I made one more check. You can start a power supply without a motherboard by shorting pin 14 with any
of the ground pins. I did that - the fan didn't start spinning, multimeter showed no voltage. Imagine my surprise:
a second-hand motherboard is fine, but a brand-new PSU isn't. Returned it, got one from a more reputable brand
(Thermaltake) - this time it worked.

It's a pity that the case didn't come with a PSU. It has quite a different shape than a standard PC tower case,
meaning the power cables could be much shorter. I use a Lenovo workstation which has a dedicated PSU with
cables just the right length, it really helps to keep the inside tidy and improve the airflow.
