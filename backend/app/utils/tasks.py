import asyncio
import datetime
from sqlmodel import select
from ldap import INVALID_CREDENTIALS
from app.database.main import get_session
from app.database.models import DBVirtualMachine
from app.models.vms import VirtualMachine
from app.utils.vms import stop_vm
from app.utils.vms import (
    create_vm,
    new_free_port,
    expose_vnc_port,
    get_vm_mac_addr,
    delete_vm,
    new_free_id,
)
from app.ldap.main import (
    delete_vm_entry,
    create_vm_entry,
    create_user,
    generate_unique_uid,
)
from app.utils.exceptions import VMCreationException, VMPortExposeException


async def check_expiry():
    while True:
        session = next(get_session())
        current_time = datetime.datetime.now(datetime.UTC)
        statement = select(DBVirtualMachine).where(
            DBVirtualMachine.expiry
            <= current_time  # Check if current time is after or at expiry
        )
        expiring_entries = (session.exec(statement)).all()

        for entry in expiring_entries:
            print(
                f"Virtual machine {entry.id} with name {entry.name} expired. proceeding to delete"
            )
            try:
                stop_vm(entry.vmid)
                delete_vm(entry.vmid)
                delete_vm_entry(entry.name)
                session.delete(entry)
            except Exception as e:
                print(e)
            finally:
                session.commit()
        await asyncio.sleep(60)


async def bulk_create(
    users: list[list[str]], core_count: int, memory: int, duration: int, prefix: str
):
    session = next(get_session())
    for user in users:
        vm = VirtualMachine(
            name=f"{user[2]}-vm",
            core_count=core_count,
            memory=memory,
            duration=duration,
        )
        try:
            create_user(
                user[0], user[1], user[2], generate_unique_uid(), user[3], prefix
            )
            id = new_free_id()
            create_vm(id=id, name=vm.name, core_count=vm.core_count, memory=vm.memory)
            port = new_free_port()
            expose_vnc_port(vmid=id, port=port)
            mac_addr = get_vm_mac_addr(id)

            create_vm_entry(vm, user[2], port=port + 5900, mac_addr=mac_addr)
        except (VMCreationException, VMPortExposeException, INVALID_CREDENTIALS) as e:
            print(f"VM creation failed: {e}")
            break
        vm_db_entry = DBVirtualMachine(
            vmid=id,
            name=vm.name,
            core_count=vm.core_count,
            memory=vm.memory,
            port=port,
            owner=user[2],
            expiry=(
                datetime.datetime.now(datetime.UTC)
                + datetime.timedelta(hours=vm.duration)
                if vm.duration > 0
                else datetime.datetime.max
            ),
        )
        session.add(vm_db_entry)
    session.commit()
