from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ldap_url: str
    ldap_dn: str
    ldap_vm_dn: str
    ldap_user_dn: str
    ldap_admin_user: str
    ldap_admin_pass: str
    ldap_base_group_id: int
    vnc_hostname: str
    algorithm: str
    secret_key: str
    api_admin_user: str
    proxmox_host: str
    proxmox_base_url: str
    proxmox_base_port: int
    proxmox_node_name: str
    proxmox_access_token: str
    proxmox_vm_netbridge: str
    proxmox_vm_config_dir: str
    allowed_csv_fields: list[str]
    default_user_passwd_length: int = 8


settings = Settings()
