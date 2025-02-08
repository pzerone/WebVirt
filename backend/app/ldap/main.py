# LDAP use bytes for data in and out, instead of regular strings.
# Almost all of the data that goes into and out of LDAP needs to encoded using str.encode()
# or use byte strings like: b"steve" and decoded using bytes.decode('utf-8')
import ldap
import ldap.modlist
from app.models.vms import VirtualMachine
from app.config import settings


conn = ldap.initialize(uri=settings.ldap_url)


def user_dn_builder(username: str) -> str:
    return f"uid={username},ou=People,{settings.ldap_dn}"


def admin_dn_builder(username: str) -> str:
    return f"cn={username},{settings.ldap_dn}"


def vm_dn_builder(vmid: str) -> str:
    return f"cn={vmid},ou=Groups,{settings.ldap_dn}"


def verify_password(username: str, password: str) -> bool:
    try:
        conn.bind_s(admin_dn_builder(username), password)
    except ldap.INVALID_CREDENTIALS:
        return False
    return True


def get_user(username: str):
    result = conn.search_s(
        settings.ldap_dn, ldap.SCOPE_SUBTREE, filterstr=f"uid={username}"
    )
    # LDAP returns enties in bytes, decode to get usable data
    return (
        {key: value[0].decode("utf-8") for key, value in result[0][1].items()}
        if result
        else None
    )


def get_all_users():
    """
    Sample search result:
     [
       [
         "ou=People,dc=trcldap,dc=icfoss,dc=org",
         {
           "objectClass": [
             "organizationalUnit"
           ],
           "ou": [
             "People"
           ]
         }
       ],
       [
         "uid=g1,ou=People,dc=trcldap,dc=icfoss,dc=org",
         {
           "objectClass": [
             "posixAccount",
             "inetOrgPerson",
             "organizationalPerson",
             "person"
           ],
           "loginShell": [
             "/bin/bash"
           ],
           "homeDirectory": [
             "/mnt/guests/g1"
           ],
           "uid": [
             "g1"
           ],
           "cn": [
             "Guest 1"
           ],
           "uidNumber": [
             "10059"
           ],
           "gidNumber": [
             "5000"
           ],
           "sn": [
             "1"
           ],
           "givenName": [
             "Guest"
           ]
         }
       ]
     ]
     """
    # the first entry in the list is metadata of the scope subtree, hence skipping
    return conn.search_s(settings.ldap_user_dn, ldap.SCOPE_SUBTREE)[1:]


def generate_unique_username(first_name: str, last_name: str):
    uids = [user[1].get("uid")[0].decode("utf-8") for user in get_all_users()]
    lim = 1
    while lim < len(first_name):
        if first_name[:lim] + last_name not in uids:
            return first_name[:lim] + last_name
        lim += 1
    i = 1
    while first_name + last_name + str(i) in uids:
        i += 1
    return first_name + last_name + str(i)


def generate_unique_uid() -> int:
    # This approach will not reuse UIDs unless all of the succeeding UIDs are also deleted
    # But that is safe anyway since we do not want a new user getting access to a previous user's UID and hence their home dir
    uids = sorted([int(user[1].get("uidNumber")[0]) for user in get_all_users()])
    return uids[-1] + 1


def create_user(
    first_name: str,
    last_name: str,
    username: str,
    uid_number: int,
    password: str,
    homedir_prefix: str,
):
    conn.bind_s(admin_dn_builder(settings.ldap_admin_user), settings.ldap_admin_pass)

    dn = f"uid={username},{settings.ldap_user_dn}"
    modlist = ldap.modlist.addModlist(
        {
            "objectClass": [
                b"inetOrgPerson",
                b"organizationalPerson",
                b"person",
                b"posixAccount",
            ],
            "loginShell": [b"/bin/bash"],
            "homeDirectory": [f"{homedir_prefix}/{username}".encode()],
            "uid": [username.encode()],
            "cn": [f"{first_name} {last_name}".encode()],
            "uidNumber": [f"{uid_number}".encode()],
            "gidNumber": [f"{settings.ldap_base_group_id}".encode()],
            "sn": [f"{last_name}".encode()],
            "givenName": [f"{first_name}".encode()],
        }
    )
    conn.add_s(dn=dn, modlist=modlist)
    conn.passwd_s(user=dn, oldpw=None, newpw=password)  # Set user password


def get_vms(username: str):
    result = conn.search_s(
        settings.ldap_vm_dn,
        ldap.SCOPE_SUBTREE,
        f"member=uid={username},{settings.ldap_user_dn}",
        attrlist=["cn", "guacConfigParameter"],
    )
    return result if result else None


def create_vm_entry(vm: VirtualMachine, uid: str, port: int, mac_addr: str):
    conn.bind_s(admin_dn_builder(settings.ldap_admin_user), settings.ldap_admin_pass)

    dn = f"cn={vm.name},{settings.ldap_vm_dn}"
    modlist = ldap.modlist.addModlist(
        {
            "objectClass": [b"guacConfigGroup", b"groupOfNames"],
            "guacConfigProtocol": [b"vnc"],
            "guacConfigParameter": [
                f"hostname={settings.vnc_hostname}".encode(),
                f"port={port}".encode(),
                b"wol-send-packet=true",
                f"wol-mac-addr={mac_addr}".encode(),
                f"wol-broadcast-addr={settings.proxmox_host}".encode(),
                b"wol-udp-port=9",
                b"wol-wait-time=5",
                f"core-count={vm.core_count}".encode(),
                f"memory={vm.memory}".encode(),
            ],
            "member": [
                f"uid=trcadmin,{settings.ldap_user_dn}".encode(),
                f"uid={uid},{settings.ldap_user_dn}".encode(),
            ],
        }
    )
    conn.add_s(dn=dn, modlist=modlist)


def delete_vm_entry(vmname: str):
    # This may throw ldap.INVALID_CREDENTIALS. Instead of catching it here, let it propagate to router, we don't have any reason to catch it here
    # other than to log, which is already being done at router along with other possible exceptions.
    conn.bind_s(admin_dn_builder(settings.ldap_admin_user), settings.ldap_admin_pass)
    dn = f"cn={vmname},{settings.ldap_vm_dn}"
    conn.delete_s(dn)
