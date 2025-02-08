import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from sqlmodel import select, Session
from sqlalchemy.exc import NoResultFound
from ldap import INVALID_CREDENTIALS
from app.models.vms import VirtualMachine
from app.models.token import TokenData
from app.routers.auth import get_current_user
from app.ldap.main import delete_vm_entry, create_vm_entry, get_user
from app.database.models import DBVirtualMachine
from app.database.main import get_session
from app.utils.vms import (
    create_vm,
    new_free_port,
    new_free_id,
    expose_vnc_port,
    get_vm_mac_addr,
    validate_specs,
    update_vm_specs,
    delete_vm,
)
from app.utils.exceptions import (
    VMCreationException,
    VMDeletionException,
    VMPortExposeException,
    VMRunningException,
    VMUpdationException,
)

router = APIRouter(prefix="/vms", tags=["Virtual Machines"])


@router.get("", response_model=list[DBVirtualMachine])
async def get_vms_of_current_user(
    *,
    session: Session = Depends(get_session),
    current_user: Annotated[TokenData, Depends(get_current_user)],
):
    """
    Returns all available Virtual machines belonging to the user who is currently logged in.
    """
    res = []
    statement = select(DBVirtualMachine).where(
        DBVirtualMachine.owner == current_user.username
    )
    results = session.exec(statement)
    for result in results:
        res.append(result)
    return res


@router.post("")
async def add_new_vm_for_user(
    *,
    session: Session = Depends(get_session),
    vm: VirtualMachine,
    current_user: Annotated[TokenData, Depends(get_current_user)],
):
    """
    For a logged in user, creates a Virtual machine of specified specs and binds them to the user.
    User may need to log out and log back in on the guacamole web frontend for the changes to be visible.
    """
    if not validate_specs(vm):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"message": "Invalid Virtual Machine details."},
        )
    try:
        id = new_free_id()
        create_vm(id=id, name=vm.name, core_count=vm.core_count, memory=vm.memory)
        port = new_free_port()
        expose_vnc_port(vmid=id, port=port)
        mac_addr = get_vm_mac_addr(id)

        # port = port + 5900: The real port where proxmox listens for VNC clients is at 5900+<selected_num>
        # This needs to be the entry in LDAP so that guacamole connects to the correct port
        create_vm_entry(vm, current_user.username, port=port + 5900, mac_addr=mac_addr)
    except (VMCreationException, VMPortExposeException, INVALID_CREDENTIALS) as e:
        print(f"VM creation failed: {e}")
        # TODO: Handle rollback here.
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "VM creation failed."
        )
    # Add an entry to the db for future queries. LDAP query and data parsing is unnecessarily complicated
    vm_db_entry = DBVirtualMachine(
        vmid=id,
        name=vm.name,
        core_count=vm.core_count,
        memory=vm.memory,
        port=port,
        owner=current_user.username,
        expiry=datetime.datetime.now(datetime.UTC)
        + datetime.timedelta(minutes=vm.duration),
    )
    session.add(vm_db_entry)
    session.commit()

    return JSONResponse("VM Created Successfully", status.HTTP_201_CREATED)


@router.patch("")
async def update_vm(
    *,
    session: Session = Depends(get_session),
    vm: DBVirtualMachine,
    current_user: Annotated[TokenData, Depends(get_current_user)],
):
    """
    Allows the user to change the following attributes of their virtual machine
    - CPU Core count
    - Total memory
    - Duration
    """
    statement = (
        select(DBVirtualMachine)
        .where(DBVirtualMachine == vm)
        .where(DBVirtualMachine.owner == current_user.username)
    )
    result = session.exec(statement)
    try:
        vm_db = result.one()
        vm_pydantic = VirtualMachine(
            name=vm.name, core_count=vm.core_count, memory=vm.memory, duration=vm.expiry
        )
        update_vm_specs(
            vmid=vm.vmid,
            vm=vm_pydantic,
        )
        vm_db.core_count, vm_db.memory = vm.core_count, vm.memory
        session.add(vm_db)
        session.commit()
    except NoResultFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "VM not found")
    except (VMUpdationException, INVALID_CREDENTIALS, Exception) as e:
        print(f"Failed to update VM specs: {e}")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to update VM specs"
        )
    return JSONResponse({"detail": "VM updated successfully"}, status.HTTP_200_OK)


@router.delete("")
async def delete_virtual_machine(
    *,
    session: Session = Depends(get_session),
    id: int,
    current_user: Annotated[TokenData, Depends(get_current_user)],
):
    """
    Allows the user to delete a Virtual Machines owned by them.
    This deletes the VM but will not delete user data since its on the LTSP server.
    """
    try:
        statement = (
            select(DBVirtualMachine)
            .where(DBVirtualMachine.id == id)
            .where(DBVirtualMachine.owner == current_user.username)
        )
        results = session.exec(statement)
        vm = results.one()
    except NoResultFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "VM not found")
    try:
        delete_vm(vm.vmid) # Proxmox
        delete_vm_entry(vm.name) # LDAP
        session.delete(vm) # DB
        session.commit()
    except VMRunningException:
        print("Refusing to delete running VM.")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete running VM")
    except (VMDeletionException, INVALID_CREDENTIALS, Exception) as e:
        print(f"Failed to delete VM: {e}")
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to delete VM"
        )
    return JSONResponse("VM Deleted Successfully", status.HTTP_200_OK)

@router.get("/user")
async def get_user_details(username: str):
    """
    Get user details.
    """
    return get_user(username)
