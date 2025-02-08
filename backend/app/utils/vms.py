import os
import time
import requests
from app.config import settings
from app.models.vms import VirtualMachine
from app.utils.exceptions import (
    VMCreationException,
    VMPortExposeException,
    VMDeletionException,
    VMRunningException,
    VMUpdationException,
    VMStopException,
)

# Suppress no cert warnings since everything is run locally
requests.packages.urllib3.disable_warnings()


def validate_specs(vm: VirtualMachine) -> bool:
    """
    The Virtual machine must satisfy the following conditions.
    - Atleast 512 MB of RAM (Enforced by proxmox)
    - Atleast 1 CPU Core
    - Atleast 60 minutes in duration
    - Atmost 50 character name
    """
    if not vm.memory >= 512:
        return False
    if not vm.core_count > 0:
        return False
    if not vm.duration >= 0 and vm.duration <= 9999999999: # safe upper limit for mathematical operations on datetime objects
        return False
    if not len(vm.name) <= 50:
        return False
    return True


def create_vm(id: int, name: str, core_count: int, memory: int):
    """
    Uses the API token generated from proxmox to create virtual machine using the pve API.
    The VM should have less than or equal to the max resources available to the host server.
    If not, the VM creation will succeed but it will not start.
    ie: you cannot start a VM with 96 cores on a 64 core server.
    """
    VM_CREATE_URL = (
        settings.proxmox_base_url
        + f":{settings.proxmox_base_port}/api2/json/nodes/{settings.proxmox_node_name}/qemu"
    )
    payload = {
        "vmid": id,
        "name": name,  # Should not contain underscores.
        "cores": core_count,
        "memory": memory,
        "cpu": "x86-64-v2-AES",
        "ostype": "l26",  # Enables optimizations based on OS type. l26 = linux 2.x to 6.x
        "scsihw": "virtio-scsi-single",
        "net0": f"virtio,bridge={settings.proxmox_vm_netbridge},firewall=1",
    }
    headers = {
        "content-type": "application/json",
        "Authorization": settings.proxmox_access_token,
    }
    try:
        response = requests.post(
            url=VM_CREATE_URL, json=payload, headers=headers, verify=False
        )
    except requests.exceptions.RequestException as e:
        # The request failed. App cannot reach proxmox API
        raise VMCreationException(
            f"Failed creating virtual machine. possible network error: {e}"
        )
    if response.status_code != 200:
        # App could reach proxmox API but it did not complete the operation.
        # Maybe wrong token?
        print(
            f"""
            VM creation failed with the following error: {response.reason}
            Does the following data look ok?
            {payload}
            If ok, check PVE API auth token.
            """
        )
        raise VMCreationException(
            "Failed creating virtual machine. pve API did not respond with OK"
        )


def update_vm_specs(vmid: int, vm: VirtualMachine):
    VM_UPDATE_URL = (
        settings.proxmox_base_url
        + f":{settings.proxmox_base_port}/api2/json/nodes/{settings.proxmox_node_name}/qemu/{vmid}"
    )
    payload = {
        "cores": f"{vm.core_count}",
        "memory": f"{vm.memory}",
    }
    headers = {
        "content-type": "application/json",
        "Authorization": settings.proxmox_access_token,
    }
    try:
        response = requests.put(
            VM_UPDATE_URL, json=payload, headers=headers, verify=False
        )
    except requests.exceptions.RequestException as e:
        raise VMUpdationException(
            f"Failed updating virtual machine specs. possible network error: {e}"
        )
    if response.status_code != 200:
        raise VMUpdationException(
            "Failed updating vm specs. pve API did not respond with OK"
        )


def delete_vm(vmid: int):
    VM_DELETE_URL = (
        settings.proxmox_base_url
        + f":{settings.proxmox_base_port}/api2/json/nodes/{settings.proxmox_node_name}/qemu/{vmid}"
    )
    headers = {
        "content-type": "application/json",
        "Authorization": settings.proxmox_access_token,
    }
    try:
        response = requests.delete(url=VM_DELETE_URL, headers=headers, verify=False)
    except requests.exceptions.RequestException as e:
        raise VMDeletionException(
            f"Failed deleting virtual machine. possible network error: {e}"
        )
    if response.status_code != 200:
        print(response.reason)
        if "running" in response.reason:
            raise VMRunningException("Cannot delete running VM")
        else:
            raise VMDeletionException(
                "Failed deleting virtual machine. pve API did not respond with OK"
            )


def stop_vm(vmid: int):
    VM_STOP_URL = (
        settings.proxmox_base_url
        + f":{settings.proxmox_base_port}/api2/json/nodes/{settings.proxmox_node_name}/qemu/{vmid}/status/shutdown"
    )
    headers = {
        # "content-type": "application/json",
        "Authorization": settings.proxmox_access_token,
        "forceStop": "1",
    }
    try:
        respose = requests.post(url=VM_STOP_URL, headers=headers, verify=False)
    except requests.exceptions.RequestException as e:
        raise VMStopException(
            f"Failed to stop virtual machine. possible network error: {e}"
        )
    if respose.status_code != 200:
        print(respose.reason)
        raise VMStopException(
            "Failed to stop virtual machine. pve API did not respond with OK."
        )


def get_vm_mac_addr(vmid: str) -> str:
    time.sleep(1)  # Wait for VM to finish creating
    QUERY_VM_URL = (
        settings.proxmox_base_url
        + f":{settings.proxmox_base_port}/api2/json/nodes/{settings.proxmox_node_name}/qemu/{vmid}/config"
    )
    headers = {
        "content-type": "application/json",
        "Authorization": settings.proxmox_access_token,
    }
    try:
        response = requests.get(url=QUERY_VM_URL, headers=headers, verify=False)
    except requests.exceptions.RequestException:
        raise VMCreationException(
            "Failed to query Vm's MAC address. possible network error. "
        )
    if response.status_code != 200:
        print(response.reason)
        raise VMCreationException(
            "Failed to query VM port, pve API did not respond with OK"
        )
    data = response.json()
    return data.get("data").get("net0").split(",")[0].split("=")[1]


def new_free_id() -> int:
    """
    Returns lowest unique ID for VM (100 - 999999999)
    """
    existing_vms = os.listdir(settings.proxmox_vm_config_dir)
    existing_vms = sorted(list(map(lambda vm: int(vm.split(".")[0]), existing_vms)))
    if len(existing_vms) == 0:
        return 100  # No VMs created yet, highly unlikely but hey.
    if (
        len(existing_vms) == 1
    ):  # Search will fail with out of index error, hence return the next best
        return existing_vms[0] + 1
    for i in range(len(existing_vms) - 1):
        if existing_vms[i] + 1 != existing_vms[i + 1]:
            return existing_vms[i] + 1
    return existing_vms[-1] + 1


def new_free_port() -> int:
    """
    Returns the lowest available port for exposing VNC
    """
    existing_vms = os.listdir(settings.proxmox_vm_config_dir)
    used_ports = []
    for vm in existing_vms:
        with open(os.path.join(settings.proxmox_vm_config_dir, vm), "r") as conf:
            for line in conf:
                if "vnc" in line:
                    used_ports.append(int(line.split(":")[-1]))
    return sorted(used_ports)[-1] + 1


def expose_vnc_port(vmid: int, port: int):
    vms = os.listdir(settings.proxmox_vm_config_dir)
    if str(vmid) + ".conf" not in vms:
        raise VMPortExposeException("No such Virtual machine")
    time.sleep(5)  # Wait for VM config file to be ready
    with open(
        os.path.join(settings.proxmox_vm_config_dir, str(vmid) + ".conf"), "a"
    ) as conf:
        conf.write(f"\nargs: -vnc 0.0.0.0:{port}")
