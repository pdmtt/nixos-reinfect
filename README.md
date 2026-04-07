# nixos-reinfect

## What is this?

A script to install NixOS on non-NixOS Linux-based hosts.

This is a fork of [nixos-infect](github.com/elitak/nixos-infect).

nixos-infect was originally so named because of the high likelihood of rendering a system inoperable.
Use with extreme caution and preferably only on newly provisioned systems.

This repository's name was changed to nixos-REinfect to highlight the effort of implementing reproducible testing,
assuring the script will successfully run as many times as needed.

## Tested on

<!-- STATUS:BEGIN -->

| Provider | Status | Last tested |
|----------|:------:|:---------:|
| Digitalocean | ✅ [run](https://github.com/pdmtt/nixos-reinfect/actions/runs/23884785906) | ?
| Hetzner      | ✅ [run](https://github.com/pdmtt/nixos-reinfect/actions/runs/23884785906) | ?

<!-- STATUS:END -->

### Why tested only against Debian 12?

The main goal of this project is to make sure people can install NixOS in any VPS provider. As of 2026-04-03, all 
providers above offer Debian 12 as an image. Considering this script wipes out the targeted host, it is assumed there's
no scenario where someone couldn't just spin up a new machine with Debian 12, in order to convert it to NixOS.

On the other hand, supporting more OSs than the minimum necessary would hinder advancing coverage over new providers.

## How do I use it?

> [!WARNING]
> Use with extreme caution and preferably only on newly provisioned systems.
>
> This script wipes out the targeted host's root filesystem when it runs to completion.
> A failure will leave the system in an inconsistent state.

0. **Read and understand the [the script](./nixos-infect.sh)**
1. Deploy any custom configuration you want on your host
2. Deploy your host as non-Nix Operating System.
3. Deploy an SSH key for the root user.

> _NB:_ This step is important.
> The root user will not have a password when nixos-infect runs to completion.
> To enable root login, you _must_ have an SSH key configured.
> If a custom SSH port is used, it will be reverted back to 22.

4. run the script with:

```sh
# bash -x is advised, because it'll help you to troubleshoot if anything fails.
curl https://raw.githubusercontent.com/pdmtt/nixos-reinfect/master/nixos-infect.sh \
  | NIX_CHANNEL=nixos-24.05 bash -x
```

If you're running this script and networking does not come up after reboot, try setting `doNetConf=y` environment variable when executing the script. 
This generates the network configuration automatically.

If the provider allows passing cloud-config files to newly provisioned instances, you may use the following command to run
this script on creation:
```yaml
#cloud-config

runcmd:
  - curl https://raw.githubusercontent.com/pdmtt/nixos-reinfect/master/nixos-infect.sh | PROVIDER=hetznercloud NIX_CHANNEL=nixos-24.05 bash 2>&1 | tee /tmp/infect.log
```

## Provider specifics

### Digital Ocean

You may pass the abovementioned cloud-config file using Digital Ocean's "user data" mechanism found in the Web UI or HTTP API.

Potential tweaks:

- `/etc/nixos/{,hardware-}configuration.nix`: rudimentary mostly static config
- `/etc/nixos/networking.nix`: networking settings determined at runtime tweak if no ipv6, different number of adapters, etc.

```yaml
#cloud-config
write_files:
  - path: /etc/nixos/host.nix
    permissions: "0644"
    content: |
      {pkgs, ...}:
      {
        environment.systemPackages = with pkgs; [ vim ];
      }
runcmd:
  - curl https://raw.githubusercontent.com/pdmtt/nixos-reinfect/master/nixos-infect.sh | PROVIDER=digitalocean NIXOS_IMPORT=./host.nix NIX_CHANNEL=nixos-24.05 bash 2>&1 | tee /tmp/infect.log
```

### Hetzner

Hetzner cloud works out of the box.
When creating a server, provide the abovementioned command as "Cloud config".

