#!/usr/bin/env python
import sys
import re
import os
import time
import subprocess
import getpass

mountpath = "/mnt/samba"
credentialpath = os.environ["XDG_DATA_HOME"]+"/smbpipe"
tmppath = "/tmp"
tmpfile = "openbox_smbpipe_tmp"
maxage = 30 #in minutes

def getshares(server, serverip, user, filemanager):
    if user == "guest":
        listoption = "-U guest -N"
        mountoption = "guest"
        edituser = "" #guest is unchangeable
    else:
        listoption = "--authentication-file="+credentialpath+"/"+server+"/"+user
        mountoption = "credentials="+credentialpath+"/"+server+"/"+user
        edituser =  '<separator label="Edit User" />'+\
        '<item label="Delete '+user+'">'+\
        '<action name="Execute">'+\
        '<command>python '+sys.argv[0]+' --credential-file '+server+' --user '+user+' --remove </command>'+\
        '</action>'+\
        '</item>'+\
        '<item label="Change password">'+\
        '<action name="Execute">'+\
        '<command>urxvt -e sh -c "python '+sys.argv[0]+' --credential-file '+server+' --user '+user+'"</command>'+\
        '</action>'+\
        '</item>'

    shares = subprocess.getoutput("smbclient -L \\"+server+" -g "+listoption).splitlines()
    for a in shares[:]:
        if not re.search("[|]", a):
            shares.remove(a)
    
    disks = []
    for a in shares:
        if re.match("Disk", a):
            disks.append(re.split("[|]", a)[1])
    disks.sort(key=str.lower)
    #hidden shares last
    disks.sort(key=lambda disk: disk[len(disk)-1]!='$', reverse=True)
    print('<separator label="Mount" />')
    for disk in disks:
        localpath = mountpath+'/'+server+'/'+re.escape(disk)
        openpath = ""
        if filemanager != "":
            openpath = filemanager + " " + localpath
        print('<item label="'+disk+'">')
        print('<action name="Execute">')
        print('<command>urxvt -e sh -c "sudo mkdir '+localpath+'; sudo mount -t cifs //'+server+'/'+re.escape(disk)+' '+localpath+' -o ip='+serverip+','+mountoption+',file_mode=0777,dir_mode=0777,noacl,noperm ; '+openpath+'"</command>')
        print('</action>')
        print('</item>')
    
    printers = []
    for a in shares:
        if re.match("Printer", a):
            printers.append(re.split("[|]", a)[1])
    printers.sort(key=str.lower)
    #hidden shares last
    printers.sort(key=lambda printer: printer[len(disk)-1]!='$', reverse=True)
    print('<separator label="Printer" />')
    for printer in printers:
        print('<item label="'+printer+'">')
        print('<action name="Execute">')
        #smb://username.password@servername/printer
        print('<command>sh -c "echo \"smb://'+server+'/'+printer+'\" | xclip"</command>')
        print('</action>')
        print('</item>')

    print(edituser)


filemanager = ""
usefilemanager = ""
parameteroffset = 0
if len(sys.argv) > 2 and sys.argv[1] == "--filemanager":
    filemanager = sys.argv[2]
    parameteroffset += 2
    usefilemanager = "--filemanager " + filemanager

if len(sys.argv) == 1+parameteroffset:
    print('<openbox_pipe_menu>')
    print('<menu id="smbpipepython" label="Servers" execute="python '+sys.argv[0]+' '+usefilemanager+' --serverlist" />')
    print('<item label="Refresh list">')
    print('<action name="Execute">')
    print('<command>python '+sys.argv[0]+' --refresh</command>')
    print('</action>')
    print('</item>')
    print('</openbox_pipe_menu>')

elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
    print("""\
Usage: """+sys.argv[0]+"""  [--help|-h] [--filemanager fm] [--serverlist | --refresh | --server server | --credential-file server [--user user [--remove]]
Args:
    --help or -h             Display this help
    --filemanager fm         Open the share (mounted location) when mounting a share
    --serverlist             Returns the serverlist
    --refresh                Deletes temporary file. Next --serverlist returns a new serverlist
    --server server          Returns the shares for server
    --credential-file server Prompts for a username and a password for server and writes a credential file
        --user user          Prompts for a password for user and writes/updates the credential file
            --remove         Removes the credential file for the user (only with --user)
""")
    exit()

elif sys.argv[1+parameteroffset] == "--refresh":
    subprocess.call(["rm", "-f", tmppath+"/"+tmpfile])

elif sys.argv[1+parameteroffset] == "--serverlist":
    try:
        age=time.time()-os.path.getmtime(tmppath+'/'+tmpfile)
    except OSError:
        age=(maxage+1)*60
    if age/60 > maxage:
        #new serverlist
        with open(tmppath+'/'+tmpfile, 'w') as f:
            f.write('<openbox_pipe_menu>')
            servers = subprocess.getoutput("smbtree -S -N -g | grep '\\\\.' | sed -e 's/\t[\\]*//g' | tr '[:upper:]' '[:lower:]'")
            for a in servers.splitlines():
                server = (str(a)).strip()
                f.write('<menu id="'+server+'" label="'+server+'" execute="python '+sys.argv[0]+' '+usefilemanager+' --server '+server+'" />')
            f.write('</openbox_pipe_menu>')
        f.closed

    with open(tmppath+'/'+tmpfile, 'r') as f:
        print(f.read())
    f.closed

elif sys.argv[1+parameteroffset] == "--credential-file":
    server = sys.argv[2+parameteroffset]
    username = ""
    remove = False
    # is user set -> check if remove (-> remove) else -> change (do not ask for user)
    if len(sys.argv) > 3+parameteroffset:
        if sys.argv[3+parameteroffset] == "--user":
            username = sys.argv[4+parameteroffset]
            if len(sys.argv) > 5+parameteroffset:
                if sys.argv[5+parameteroffset] == "--remove":
                    remove = True
    if remove:
        subprocess.call(["rm", "-f", credentialpath+"/"+server+"/"+username])
    else:
        try:
            os.mkdir(credentialpath+"/"+server)
        except OSError:
            pass
        subprocess.call(["chmod", "700", credentialpath+"/"+server])
        if username == "":
            username = input("Username: ")
        password = getpass.getpass()
        with open(credentialpath+'/'+server+'/'+username, 'w') as f:
            f.write('username='+username+'\n')
            f.write('password='+password+'\n')
        f.closed
        subprocess.call(["chmod", "600", credentialpath+"/"+server+"/"+username])

elif sys.argv[1+parameteroffset] == "--server":
    server = sys.argv[2+parameteroffset]
    print('<openbox_pipe_menu>')
    ip = subprocess.getoutput("nmblookup "+server+" | grep "+server+"'<' | sed -e 's/ [^ ]*$//g'").splitlines()
    serverip="ERROR"
    for line in ip:
        if re.match("\d+\.\d+\.\d+\.\d+", line):
            serverip=line.rstrip()
            break
    #for every file in credentialpath/server/ -> users
    users = []
    users.append("guest")
    try:
        users += os.listdir(credentialpath+"/"+server)
    except OSError:
        pass
    for user in users:
        print('<menu id="'+server+'-'+user+'" label="'+user+'">')
        getshares(server, serverip, user, filemanager)
        print('</menu>')
    print('<item label="Create credential file">')
    print('<action name="Execute">')
    print('<command>urxvt -e sh -c "python '+sys.argv[0]+' --credential-file '+server+'"</command>')
    print('</action>')
    print('</item>')

    print('</openbox_pipe_menu>')
