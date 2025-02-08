#!/usr/bin/env python3

# WebVirt Utility to expose Proxmox VNC outside of the host.
# This script will add a VNC configuration to all VMs in the Proxmox host
# that do not already have a VNC configuration.
# The VNC port will be the default VNC port (5900) + the VM's ID.
# This script is intended to be run on the Proxmox host itself.
#
# Usage:
#   python3 bulk_expose.py --start-port <port_number> [--dry-run]
#
#   --start-port: The port number to start the VNC port mapping from.
#   --dry-run: Do not make any changes, just print the port mappings.
#
# Example:
#   To start exposing VNC from port 5900:
#   python3 bulk_expose.py --start-port 5900
#
#   To see the port mappings without making any changes:
#   python3 bulk_expose.py --start-port 5900 --dry-run
# 
# The script accepts CONFIG_DIR environment variable to specify the path to the
# directory containing the Proxmox VM configuration files. If not specified, it
# defaults to the current directory.

import os
import sys
from typing import TextIO

# Default values

# Path to the directory containing the Proxmox VM configuration files.
CONFIG_DIR_PATH = os.environ.get("CONFIG_DIR", ".")

# Blacklisted config files that we don't want to touch.
IGNORED_CONFIGS = ["100.conf","800.conf","900.conf"]


def write_config(filehandle: TextIO, port: int) -> bool:
    vnc_config = f"args: -vnc 0.0.0.0:{port}\n"
    filehandle.write(vnc_config)
    return True

def print_help():
    print(
        f"{sys.argv[0]}: Expose Proxmox VNC output in bulk\n"
        f"Usage: {sys.argv[0]} --start-port <port_number> [--dry-run]"
    )

def main() -> int:
    if os.geteuid() != 0:
        print("Not root, Exiting...")
        # return 1

    if "--help" in sys.argv:
        print_help()
        return 0

    # print help message for improper cmdline args
    if len(sys.argv) < 3:
        print_help()
        return 1
    try:
        START_PORT = int(sys.argv[2])
    except ValueError:
        print("Invalid port number")
        return 1

    try:
        configs = os.listdir(CONFIG_DIR_PATH)
    except OSError:
        print(
            "Cannot find proxmox config directory. "
            "Are you sure we're inside a proxmox host?"
        )
        return 1

    # Get rid of any pre-defined config files that we don't want to touch,
    # as well as any non proxmox config files/dirs.
    # This includes our management VM's config.
    configs = [
        config
        for config in configs
        if config not in IGNORED_CONFIGS and config.endswith("conf")
    ]
    configs.sort()
    print("Config File\t\tPort Mapping")
    for port_num, config in enumerate(configs, start=START_PORT):
        with open(os.path.join(CONFIG_DIR_PATH, config), "r+") as cfile:
            if "vnc" in cfile.read():
                print(f"{config}\t\tMapping exists")
                continue  # skip configs with existing vnc configuration setup.
            if sys.argv[-1] == "--dry-run":
                print(f"{config}\t\t5900 + {port_num} [Dry Run]")
                continue
            print(f"{config}\t\t5900 + {port_num}")
            if not write_config(filehandle=cfile, port=port_num):
                print("Partial/broken setup. Please revert manually")
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
