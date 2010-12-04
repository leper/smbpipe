#! /usr/bin/python
import sys
import re
import os
import time
import subprocess

mountpath = "/mnt/samba"
credentialpath = "$XDG_DATA_HOME/smbpipe"
tmppath = "/tmp"
tmpfile = "openbox_smbpipe_tmp"
maxage = 30 #in minutes

if len(sys.argv) == 1:
    print('<openbox_pipe_menu>')
    print('<menu id="smbpipepython" label="Servers" execute="python '+sys.argv[0]+' --serverlist" />')
    print('<item label="Refresh list">')
    print('<action name="Execute">')
    print('<command>python '+sys.argv[0]+' --refresh</command>')
    print('</action>')
    print('</item>')
    print('</openbox_pipe_menu>')

elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
    print("""\
Usage: """+sys.argv[0]+""" [--serverlist|--refresh|--server server]
Args:
    --serverlist    Returns the serverlist
    --refresh       Deletes temporary file. Next --serverlist returns a new serverlist
    --server server Returns the shares for server
""")
    exit()

elif sys.argv[1] == "--refresh":
    subprocess.call("rm", "-f "+tmppath+"/"+tmpfile)

elif sys.argv[1] == "--serverlist":
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
                f.write('<menu id="'+server+'" label="'+server+'" execute="python '+sys.argv[0]+' --server '+server+'" />')
            f.write('</openbox_pipe_menu>')
        f.closed

    with open(tmppath+'/'+tmpfile, 'r') as f:
        print(f.read())
    f.closed

elif sys.argv[1] == "--server":
    server = sys.argv[2]
    print('<openbox_pipe_menu>')
    ip = subprocess.getoutput("nmblookup "+server+" | grep "+server+"'<' | sed -e 's/ [^ ]*$//g'").splitlines()
    serverip="ERROR"
    for line in ip:
        if re.match("\d+\.\d+\.\d+\.\d+", line):
            serverip=line.rstrip()
            break
    shares = subprocess.getoutput("smbclient -L \\"+server+" -g --authentication-file="+credentialpath+"/"+server).splitlines()
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
    print(disks)
    print('<separator label="Mount" />')
    for disk in disks:
        print('<item label="'+disk+'">')
        print('<action name="Execute">')
        print('<command>urxvt -e sh -c "sudo mkdir \\"'+mountpath+'/'+server+'/'+disk+'\\"; sudo mount -t cifs \\"//'+server+'/'+disk+'\\" \\"'+mountpath+'/'+server+'/'+disk+'\\" -o ip='+serverip+',credentials='+credentialpath+'/'+server+'"</command>')
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
        print('<item label="'+printer+'" />')
    print('</openbox_pipe_menu>')