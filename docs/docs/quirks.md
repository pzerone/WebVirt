This page contains some quirks that you may encounter while setting up the platform and how to work around them.
!!! Note
    Any changes done to the LTSP images will require you to rebuild the image. This can be done by running the following commands:
    ```bash
    sudo ltsp image <image_name>
    ```
### Disable Auto suspend
By default in gnome the client image is set to suspend after 5 minutes of inactivity depending on the client distro defaults. This can be troublesome since it usually results in a frozen system and no way for user to restart it. To disable this system wide, you'll have to edit the following files
 `/etc/dconf/db/local.d/00-power`
```ini
# Specify the dconf path
[org/gnome/settings-daemon/plugins/power]

# Enable screen dimming
idle-dim=false

# Set brightness after dimming
idle-brightness=30
```
`/etc/dconf/db/local.d/00-screensaver`
```ini
# Specify the dconf path
[org/gnome/desktop/session]

# Number of seconds of inactivity before the screen goes blank
# Set to 0 seconds if you want to deactivate the screensaver.
idle-delay=uint32 0

# Specify the dconf path
[org/gnome/desktop/screensaver]

# Number of seconds after the screen is blank before locking the screen
lock-delay=uint32 0
```

### Kali Linux does not authenticate LDAP users
You may encounter an issue where Kali Linux clients are unable to authenticate LDAP users even after configuring LDAP on Kali VM in virtualbox. This is due to the fact that in Kali, the `nslcd.service` not enabled by default. To fix this, you'll have to manually enable the service after installing LDAP packages. Run the following command:
```bash
sudo systemctl enable --now nslcd.service
```
### Username prompt on login
Since all users exists on the LDAP server, GDM will not show the list of users on the login screen and the user should click on the "Not listed?" button to enter the username manually. This can be annoying for users who are not aware of this. To disable user list and show username prompt on login, you'll have to edit `/etc/gdm3/greeter.dconf-defaults` to uncomment the `disable-user-list=true` line.
