import json
import csv
from typing import Annotated
from datetime import datetime
from codecs import iterdecode
from fastapi import (
    APIRouter,
    HTTPException,
    UploadFile,
    status,
    BackgroundTasks,
    Depends,
)
from app.config import settings
from app.models.vms import VirtualMachine
from app.models.token import TokenData
from app.utils.vms import validate_specs
from app.utils.tasks import bulk_create
from app.utils.auth import generate_password
from app.routers.auth import get_current_user
from app.ldap.main import generate_unique_username

router = APIRouter(prefix="/admin", tags=["Admin Routes"])


@router.post("/csv")
async def process_csv(
    file: UploadFile,
    core_count: int,
    memory: int,
    duration: int,
    prefix: str,
    bg_tasks: BackgroundTasks,
    current_user: Annotated[TokenData, Depends(get_current_user)],
):
    """
    This is an admin only route to bulk create users and their virtual machines.
    Scenario:
        A group of people register for a Kali linux course.
        The admin first sets up the Kali image in LTSP with all required tools.
        Admin receives the list of students/candidates attending the course
        the list must be a CSV file with the following columns:
            - first_name
            - last_name
        Admin uploads this CSV to this route along with the following information
            - CPU Core count for all users
            - Total memory for all users
            - Duration of the course (in minutes). this info is used to lock the user account once the course is over,
                so that they cannot login afterwards
    The VM and user creation is done asynchronously, hence the user list with the following info will be returned upfront.
        - first_name
        - last_name
        - unique username
        - password
    """
    if current_user.username != settings.api_admin_user:  # Only allowd for admin
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")

    if not validate_specs(
        VirtualMachine(core_count=core_count, memory=memory, duration=duration)
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Invalid virtual machine specs"
        )
    if file.content_type != "text/csv":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {
                "reason": "Invalid filetype",
                "expected": "text/csv",
                "received": file.content_type,
            },
        )
    reader = csv.reader(iterdecode(file.file, "utf-8"))
    header = (
        reader.__next__()
    )  # Get the first row of the file, which will be the header.
    if header != settings.allowed_csv_fields:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {
                "reason": "Invalid header names",
                "expected": settings.allowed_csv_fields,
                "received": header,
            },
        )
    entries = [
        ["first_name", "last_name", "username", "password"]
    ]  # Update the header with username and password columns
    entries.extend([entry for entry in reader if any(field.strip() for field in entry)])
    if len(entries) < 2:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Empty or corrupted csv file. Check contents."
        )

    for user in entries[1:]:  # Generate username and password for each user
        user.append(
            generate_unique_username(user[0].replace(" ", "").lower(), user[1].replace(" ", "").lower())
        )
        user.append(generate_password(settings.default_user_passwd_length))
    with open("creation_log.json", "a") as logfile:  # log the creation to a file
        logfile.write(str(datetime.now()))
        logfile.write(
            f"\nUser count: {len(entries)-1}\nCore Count: {core_count}\nMemory: {memory}\nDuration: {duration}\nHome Directory prefix: {prefix}\n"
        )
        json.dump(entries, logfile)
        logfile.write("\n\n")

    bg_tasks.add_task(
        bulk_create, entries[1:], core_count, memory, duration, prefix
    )  # Call background task
    return entries
