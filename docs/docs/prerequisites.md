# Prerequisites

To ensure smooth system operation, it is important to meet specific hardware and software requirements. Adhering to these guidelines will help avoid potential issues.

## Hardware Requirements

The Guacamole server and LDAP server can be hosted on virtual machines within a Proxmox environment for better management. However, the LTSP server must be a physical machine due to its need for running VirtualBox to create LTSP client images. Although nested virtualization allows for LTSP on a virtual machine, we will use a dedicated physical server for this purpose.

### Virtual Machine Server

The more powerful your server, the more virtual machines (VMs) it can host. When serving a specific operating system like Ubuntu, you should follow its official system requirements. According to the [Ubuntu 24.04 download page](https://ubuntu.com/download/desktop#system-requirements), the recommended specifications are 4GB of RAM and a 2GHz CPU. For this project, Ubuntu 24.04 VMs have been tested with 1 CPU core from an 80-core server-grade CPU (Intel Xeon Silver 4316 @ 2.30GHz) and 2GB of RAM per VM. This configuration works well for basic tasks like web browsing and light programming.

### LTSP Server

The LTSP server is another key hardware requirement. All VMs will boot from this server and mount user home directories using SSHFS/NFS. Both the CPU and network should be powerful enough to handle these tasks. The [Debian Wiki](https://wiki.debian.org/LTSP/Ltsp%20Hardware%20Requirements) provides a detailed overview.

!!! TLDR
    - Gigabit networking is required between the LTSP server and the switch. 100 Mbps is acceptable for clients connecting to the switch, though Gigabit is recommended.
    - 2GB of RAM plus an additional 30MB per client is needed.
    - CPU requirements are calculated in terms of benchmark scores. In testing, a 4-core desktop CPU (Intel Core i5-7500 @ 3.40GHz) handled 50 clients with SSHFS for home directory mounting.

### Guacamole Server

Apache Guacamole streams virtual machine display outputs to web browsers and supports various remote desktop protocols like VNC and RDP. We will use the VNC protocol, as Proxmox can be configured to share a VM’s display output beyond its web UI.

Since Guacamole handles video encoding for multiple clients, a solid configuration would involve 4 cores and 8GB of RAM for every 100 VMs. All necessary programs for Guacamole will be deployed using Docker.

!!! Tip
    The Guacamole server can run as a VM inside the Proxmox environment.

### LDAP Server

The LDAP server has minimal hardware requirements, as it mainly handles authentication and directory services. A single-core processor and 1GB of RAM should be sufficient for this VM. Although LDAP can be deployed as a Docker container alongside Guacamole, it's preferable to use separate VMs to avoid a single point of failure. If resources permit, use separate virtual machines for Guacamole and LDAP.

## Software Requirements

### LTSP

LTSP officially supports Debian-based distributions and recommends Debian. Installation instructions are available on the [official LTSP documentation site](https://ltsp.org/docs/installation/).

### LDAP

For Debian and Debian-based distributions, the OpenLDAP package is called [slapd](https://packages.debian.org/search?keywords=slapd). Alternatively, any LDAP3-compatible software can be used.

### Guacamole

Guacamole will be installed as Docker containers, which include three images:

- Guacamole Daemon
- Guacamole Webserver
- A database (PostgreSQL recommended)

### Other Tools

- [Docker](https://docs.docker.com/engine/install/debian/): For managing Guacamole Docker containers.
- [VirtualBox](https://www.virtualbox.org/wiki/Linux_Downloads): To create custom Linux installations to be exported as LTSP images.
- [Apache Directory Studio](https://directory.apache.org/studio/download/download-linux.html): LDAP Management and Overview.
<!-- - [LAM](https://github.com/LDAPAccountManager/docker): LDAP User Management WebApp. -->

