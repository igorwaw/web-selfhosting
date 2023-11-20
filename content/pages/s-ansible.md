Title: Sidenote 1 - Using Ansible
Date: 2023-11-19 17:40
Status: published
Tags: services

I use Ansible to configure my home computers. I started doing it to learn the tool, but is it really worth to use it at home other than for education? Maybe.

On the downside, it's generaly faster to configure a server manually. The syntax is quite awkward for
beginners. If you need to change a few lines in a config file, you can do it in 30 seconds with a text editor or spend an hour retrying the playbook. But it can save you time as well if you're going to repeat the task.

There are several ways to use Ansible. One is to automate ad-hoc tasks, such as patching, gathering some information, repairing common problems. It's quite usual if you're introducing Ansible into a pre-existing infrastructure.

But Ansible really shines if you use the Infrastructure as a Code approach. That is, every server (or group of identical servers) has one playbook containing the whole configuration: software, user accounts etc. Parts of the playbook that are the same on different servers can be shared (see below about roles). And if you ever need to rebuild your server, you can do it with one command. It happened 3 times with my NAS (I experimented with different hardware). For more experimental devices or VMs, you can intentionally rebuilt them often.

Proper Ansible playbooks are idempotent, meaning they can be run multiple times. Ansible will check the state of the server and skip tasks that wouldn't change anything. 

## Think what should be automated

Since it's a home network, I didn't do several things I would do in an enterprise setting. The most important ommision is provisioning. I just started from the base system already installed. Provisioning can be automated, but I decided not to do it. I've got different types of machines: Raspberry Pis, PCs, VMs, VPS. Each needs to be provisioned in a different way: PXE, writing image to the card, cloning base image or using Terraform. That would mean lots of work for not much use (usually once per machine) and not much educational value (I know how to do it). My setup does 80% of the job with 20% of the effort.

Sometimes one action you do with Ansible changes the way you interact with the server later. Example: I change SSH port on all my servers. That means I have to login with a default port on the first run, but on each subsequent run I need to use my custom port. Solution? I just manually change the port in the Ansible inventory. If I had a higly dynamic infrastructure with new machines coming every day, that wouldn't to, but in my case it only happens once per machine. 

## Using linter

Playbook syntax can be hard in the beginning. A wrong indentation can turn it into an incorrect YAML. Even worse, there are some real gotchas, for example if you don't put quotes around numeric file permissions, they might end up other than expected. A tool called ansible-lint checks all these and enforces some best practices.

In fact, the linter is really picky and you might have to ignore some rules. I've got this in my .ansible-lint:

```yaml
skip_list:
  - yaml[line-length]
  - package-latest
```

Which means I allow long lines (linter thinks you should split them, I disagree) and installing latest version of software instead of a specific version.

I started using Ansible several years ago. In the meantime, the idea how an Ansible playbook should look like changed a lot. Running ansible-lint revealed many problems with my code. For example, it is recommended to use fully-qualified collection names even for builtin commands (eg. ansible.builtin.file instead of file).

## Using roles

Roles are reusable pieces of configuration, which make my playbooks really short. There are some things I want to do with all Linux machines on my network:

- create a user account and install SSH key,
- configure SSH server the way I like it,
- upgrade packages
- install some packages that I use everywhere.

Which is why I prepared a role "linux_common". Then there's role "linux_dev" that install code editors, C++ compiler and some tools (Python is included in the base system). I want it on my laptop and on my desktop, but on the server. Similar with the office and multimedia software included in the role "linux_desktop".

My home server Firefly gets many roles. There's one called firefly which contains settings specific to this machine, but there are also roles for Jellyfin and Prometheus. In future I might decide to move them elsewhere, so I'll just include those roles in another machine's playbook.

![Ansible role directory tree]({static}/images/ansible-role.png)

Ansible uses some conventions about directory structure and file naming. You can ignore them, but adhering to them will make life easier for everyone. This is an example for a moderately complex role.

The most important directory is "tasks", it stores YAML files with all task definitions. Handlers are special kind of tasks - they are run after all the standard tasks if a specific condition was met. For example, you can restart your service if its binary has changed or if the configuration file was modified. If both events happened, Ansible is smart enough to only run the handler once. In both of these directories, only file "main.yml" is read. But if it gets too long, you can import other files from it.

Directory "defaults" stores default values for variables, which are overwritten by custom values from "vars". Last but not least, "files" contains all files that will be copied to the server without any change, those from "templates" are filled with some generated content first.

## Using Galaxy

You can install roles prepared by others using Ansible Galaxy. They often save you hours of writing and testing playbooks. Some of them are so well-prepared that you can use them without changing the code, only modyfing the configuration. Others though are of lesser quality, or your infrastructure is so specific that a generic role can't solve all of your problems. In that case, you can just edit them just like you would edit your own role.
