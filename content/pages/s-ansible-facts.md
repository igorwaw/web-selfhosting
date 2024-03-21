Title: Sidenote 2 - Ansible fact gathering
Date: 2024-03-22 17:40
Status: published
Tags: services

If you look closely at the playbook's output, you will see that it always begins with "Gathering facts". It takes a few seconds, which annoys many users - especially when you're developing and therefore running the same playbook many times.

## How it works?

Ansible runs a special built-in task at the beginning of each playbook.
Facts are then available as variables. You can print them all with a simple playbook:

```yaml
---
- name: Print all available facts
  hosts: localhost
  tasks:
    - name: Print all facts
      ansible.builtin.debug:
        var: ansible_facts

```

Or even simpler: `ansible <hostname> -m ansible.builtin.setup`.

## Why?

Ansible can manage Linux, other Unix-like operating systems, Windows, network devices and a plethora of other things. Even if you stick with Linux, there's a huge difference between RHEL 6.0 and Ubuntu 23.10.

You can use facts like any other variable in your playbook or template. Some facts are more useful than others. For example I often use *ansible_distribution_release* when adding apt sources.

You can even gather and use fact about one system when configuring another system. For example, you can get IP address from your DB server and use it when configuring a DB client.

## Disabling fact gathering

Sometimes you don't need to gather facts. Be careful though, even if you don't use them directly, your Galaxy roles or built in task might rely on them. But there are some cases when you can be 100% sure you won't need the facts. For example, when working with clouds you then specify localhost as your playbook's target, but it's only the host that runs the cloud API client, you don't really care about its configuration. You can then begin your playbook with:

```yaml
- name: Do something on the cloud
  hosts: localhost
  become: false
  gather_facts: false
```

## Caching facts

If you want to make your playbooks run a few seconds faster, there's a better way then disabling fact gathering: fact caching. For more complex setups you can use the DB, but a simple file is usually enough. Add this to your ansible.cfg:

```ini
[defaults]
fact_caching = jsonfile
fact_caching_connection = $HOME/.ansible/fact-cache
fact_caching_timeout = 3600
```

How long should you cache facts? That depends on you and your infrastructure. If it's highly dynamic, the machine can change at any time, but in many places servers stay the same for months. Personally, I use something between a few minutes and one hour. 
