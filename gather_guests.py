import os
import pwd
import grp
import subprocess

def get_all_users():
    users = []
    for entry in pwd.getpwall():
        users.append({
            'name': entry.pw_name,
            'uid': entry.pw_uid,
            'gid': entry.pw_gid,
            'gecos': entry.pw_gecos,
            'dir': entry.pw_dir,
            'shell': entry.pw_shell
        })
    return users

def get_last_logins():
    try:
        output = subprocess.check_output(['lastlog']).decode('utf-8', errors='ignore')
        return output
    except Exception as e:
        return str(e)

def get_logged_in_users():
    try:
        output = subprocess.check_output(['w']).decode('utf-8', errors='ignore')
        return output
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    print("=== USERS ===")
    for u in get_all_users():
        print(u)
    print("\n=== LASTLOG ===")
    print(get_last_logins())
    print("\n=== W ===")
    print(get_logged_in_users())
