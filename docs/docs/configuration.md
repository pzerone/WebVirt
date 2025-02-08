## Recap
We have set up Proxmox on a server, configured LDAP on a virtual machine, installed LTSP on a separate machine, and deployed Apache Guacamole as Docker containers on a virtual machine.

## Setting Up Wake On LAN for VMs
!!! Info
    The following scripts and commands are to be run on the Proxmox server.

Once our platform is deployed and users begin utilizing the virtual machines, a challenge arises when a user shuts down a VM. They won't have the ability to start it back up on their own. Fortunately, Apache Guacamole allows us to send Wake-On-LAN (WOL) packets to power on the VM before attempting a connection. However, since we're working with virtual machines instead of physical ones, the network interface card (NIC) isn't actively listening for WOL packets once the VM is shut down. To resolve this, we'll configure the Proxmox server to listen for WOL packets and start the appropriate VM based on the packet's target MAC address.

The following Script was sourced from proxmox forums with slight modifications. (credit goes to [EpicLPer](https://forum.proxmox.com/members/epiclper.161512/))
Original forum post [link](https://forum.proxmox.com/threads/wake-on-lan-wol-for-vms-and-containers.143879/)
```bash
#!/bin/bash

IFACENAME="vmbr1"

while true; do
  sleep 2
  wake_mac=$(tcpdump -c 1 -UlnXi "$IFACENAME" ether proto 0x0842 or udp port 9 2>/dev/null |\
  sed -nE 's/^.*20:  (ffff|.... ....) (..)(..) (..)(..) (..)(..).*$/\2:\3:\4:\5:\6:\7/p')
  echo "Captured magic packet for address: \"${wake_mac}\""
  echo -n "Looking for existing VM: "
  matches=($(grep -il ${wake_mac} /etc/pve/qemu-server/*))
  if [[ ${#matches[*]} -eq 0 ]]; then
    echo "${#matches[*]} found"
  echo -n "Looking for existing LXC: "
  matches=($(grep -il ${wake_mac} /etc/pve/lxc/*))
  if [[ ${#matches[*]} -eq 0 ]]; then
    echo "${#matches[*]} found"
    continue
  elif [[ ${#matches[*]} -gt 1 ]]; then
    echo "${#matches[*]} found, using first found"
  else
    echo "${#matches[*]} found"
  fi
  vm_file=$(basename ${matches[0]})
  vm_id=${vm_file%.*}
  details=$(pct status ${vm_id} -verbose | egrep "^name|^status")
  name=$(echo ${details} | awk '{print $2}')
  status=$(echo ${details} | awk '{print $4}')
  if [[ "${status}" != "stopped" ]]; then
    echo "SKIPPED CONTAINER ${vm_id} : ${name} is ${status}"
  else
    echo "STARTING CONTAINER ${vm_id} : ${name} is ${status}"
    pct start ${vm_id}
  fi
    continue
  elif [[ ${#matches[*]} -gt 1 ]]; then
    echo "${#matches[*]} found, using first found"
  else
    echo "${#matches[*]} found"
  fi
  vm_file=$(basename ${matches[0]})
  vm_id=${vm_file%.*}
  details=$(qm status ${vm_id} -verbose | egrep "^name|^status")
  name=$(echo ${details} | awk '{print $2}')
  status=$(echo ${details} | awk '{print $4}')
  if [[ "${status}" != "stopped" ]]; then
    echo "SKIPPED VM ${vm_id} : ${name} is ${status}"
  else
    echo "STARTING VM ${vm_id} : ${name} is ${status}"
    qm start ${vm_id}
  fi
done
```

Replace `IFACENAME` with the name of the network interface that Proxmox will be listening on. To test this setup, save the file on the proxmox server and execute it manually (it will eventually be set up as a systemd service, but for now, we'll leave it as is). 

Next, create a new virtual machine or use an existing one, power it off, and retrieve its MAC address from the Proxmox web UI. Then, from **another machine** with `wol` installed, run the following command to send a Wake-On-LAN (WOL) packet:

```bash
# Replace with the target MAC address
wol --port 9 AA:BB:CC:DD:EE:FF
```
If the VM powers on, your setup is successful. If not, ensure that the machine sending the WOL packet can reach the Proxmox server and verify that no firewalls are blocking port 9 between them.

#### Systemd service
Now that the script is working like indented, we can set it up as a systemd service to ensure it runs on boot and restarts if it crashes. Create a new service file with the following content:

```ini
[Unit]
Description=Wake-on-LAN for Proxmox Virtual Environments
After=network.target

[Service]
Type=simple
Restart=always
User=root
ExecStart=/usr/local/bin/scripts/wol-vms.sh

[Install]
WantedBy=multi-user.target
```
Make sure to place the script in the correct directory on the proxmox server and update the `ExecStart` path accordingly. Save the file as `wol-vms.service` in `/etc/systemd/system/` and run the following commands to enable and start the service:

```bash
systemctl enable --now wol-vms
```
Now lets move on to creating some VMs for our users to access.

## Creating Virtual Machines
We will create a few virtual machines for our users to access. run the following command on the proxmox server to create 5 virtual machines:

```bash
for i in {1..5}; do qm create 200$i --name VM-200$i --cpu x86-64-v2-AES --cores 2 --sockets 1 --memory 4096 --net0 virtio,bridge=vmbr1,firewall=1 --ostype l26 --scsihw virtio-scsi-single; done
```
This command will create 5 virtual machines with 2 cores, 4GB of RAM, and a single network interface connected to `vmbr1`. The VMs will be named `VM-2001`, `VM-2002`, `VM-2003`, `VM-2004`, and `VM-2005`. Feel free to adjust the resources and names as needed. You can find more info on the qm command [here](https://pve.proxmox.com/pve-docs/qm.1.html).

We now have 2 more steps to complete before our platform is ready for users to access. We need to expose the VNC output from proxmox, so that guacamole can connect to it and we need to add the VMs to LDAP and associate them with users. Let's start with the first step.

## Exposing VNC Output
By default, Proxmox does not expose the VNC output of virtual machines. To enable this, we need to add a few lines to the VM configuration file. Run the following command to add the necessary lines to the configuration files:

```bash
for i in {1..5}; do echo "args: -vnc 192.168.111.123:$((i + 77))" >> /etc/pve/qemu-server/200$i.conf; done
```
This command will add the `-vnc` argument to the VM configuration files, exposing the VNC output on the IP address of the Proxmox server and port `5900+xx`, where `xx` is the VM number added to 77. For example, `VM-2001` will be exposed on `192.168.111.123:5978`. There is a dedicated wiki page on the Proxmox website that explains the VNC options in more detail [here](https://pve.proxmox.com/wiki/VNC_Client_Access).

Make sure to replace the IP address with the one that your Proxmox server is using. Now that the VNC output is exposed, we can move on to the final step.

## Adding VMs to LDAP
!!! Info
    The following scripts and commands are to be run on the LDAP server.

To allow users to access the VMs, we need to add them to LDAP and associate them with the users. We will use the `ldapadd` command to add the VMs to LDAP. Create a new file called `vms.ldif` on the LDAP server with the following content:

```ldif
# VM 1
dn: cn=VM 1,ou=groups,dc=example,dc=com
objectClass: guacConfigGroup
objectClass: groupOfNames
guacConfigProtocol: vnc

guacConfigParameter: hostname=192.168.111.123 # Replace with the IP address of the Proxmox server where VNCs are exposed
guacConfigParameter: port=5978 # Replace with the port number of the VNC output
guacConfigParameter: wol-send-packet=true
guacConfigParameter: wol-mac-addr=AA:BB:CC:DD:EE:FF # Replace with the MAC address of the VM
guacConfigParameter: wol-broadcast-addr=192.168.111.123 # Replace with the proxmox server IP where our wol-vms script is listening
guacConfigParameter: wol-udp-port=9
guacConfigParameter: wol-wait-time=5 # Time to wait for the VM to start before connecting
member: uid=ldapadmin,ou=people,dc=example,dc=com # Replace with the user that should have access to the VM. You can add multiple users by repeating this line
```
Replace the values in the `vms.ldif` file with the appropriate values for your setup. Duplicate the entry for each VM you created, changing the `cn=`, `port=`, `wol-mac-addr=` and `member=` values accordingly. Once the file is ready, run the following command to add the VMs to LDAP:

```bash
ldapadd -x -D cn=admin,dc=example,dc=com -W -f vms.ldif
```
You will be prompted to enter the LDAP admin password. You can verify that the VMs were added successfully by running the following command:

```bash
ldapsearch -x -LLL -b ou=groups,dc=example,dc=com
```
This command will list all the groups in the `ou=groups,dc=example,dc=com` branch. You should see the VMs listed with the appropriate configuration. If everything looks good, you can now access the VMs using Apache Guacamole.

## Wrapping Up
We have successfully set up Wake-On-LAN for VMs on the Proxmox server, created virtual machines for users to access, exposed the VNC output, and added the VMs to LDAP. Users can now access the VMs using Apache Guacamole. Spin up a browser and navigate to the Guacamole web interface to test the connection. If everything is working as expected, you have successfully set up a remote desktop platform using Proxmox, LDAP, LTSP, and Apache Guacamole. Congratulations!.

## Next Steps
- [Creating and managing LTSP Images](management.md)