"""
Based on micropython-ftplib 0.1.0 by SpotlightKid:
    https://github.com/SpotlightKid/micropython-ftplib

Which was based on on CPython's ftplib by Guido van Rossum, et al.:
    https://github.com/python/cpython/blob/3.7/Lib/ftplib.py

Python Software Foundation License
"""

import usocket as socket

MAXLINE = 2048
CRLF = '\r\n'
B_CRLF = b'\r\n'
_GLOBAL_DEFAULT_TIMEOUT = object()

class Error(Exception): pass
class ReplyError(Error): pass
class TempError(Error): pass
class PermError(Error): pass
class ProtoError(Error): pass
class FTP:

    sock = None
    file = None
    encoding = "utf-8"
    

    def __init__(self, host="sftp.crh.noaa.gov", port=21, user="ccoopuser", passwd="1129#Nawwal",
                 ssl=True,ssl_params={"keyfile": "/flash/cert/key.crt","certfile": "/flash/cert/cert.crt"}, timeout=10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.ssl = ssl
        self.ssl_params = ssl_params
        #print("Established")
        #test
        if host:
            #print("Connecting")            
            if user:
                self.connect(host, port)
                self.login(user, passwd)
                self.sendcmd("SYST")
                self.sendcmd("OPTS UTF8 ON")
                self.sendcmd("PBSZ 0")
                self.sendcmd("PROT P")
                self.sendcmd("TYPE I")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.sock is not None:
            try:
                self.quit()
            except (OSError, EOFError):
                pass
            finally:
                if self.sock is not None:
                    self.close()

    def _create_connection(self, addr, timeout=None):
        if self.ssl == True:
            import ussl
            proto = socket.IPPROTO_SEC            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, proto)
            sock = ussl.wrap_socket(sock, **self.ssl_params)
            sock.connect(addr)
            sock.settimeout(30)
            return sock
        
    def connect(self, host, port, timeout=10):
        #print("Cntl Host: " + str(host))
        #print("Cntl Port: " + str(port))
        self.sock = self._create_connection((host, port), timeout)
        return self.getresp()

    def download(self, host = "sftp.crh.noaa.gov", port = 3000, timeout=10):
        #print("File Host COMMAND: " + str(host))
        #print("File Port COMMAND: " + str(port))
        self.sock = self._create_connection((host, port), timeout)

    def rcv(self, sz = 0):
        sock = self.sock
        data = str(self.sock.recv(sz), self.encoding)
        eof="EOF"
        if not data:
            return eof
        else:
            return data
        return

    def login(self, user='anonymous', passwd='anonymous@'):
        resp = self.sendcmd('USER ' + user)
        if resp[0] == '3':
            resp = self.sendcmd('PASS ' + passwd)
        return resp

    def quit(self):
        resp = self.voidcmd('QUIT')
        self.close()
        return resp

    def close(self):
        sock = self.sock
        self.sock = None
        if sock is not None:
            sock.close()
            
    def chTimeout(self, timeout=10):
        sock = self.sock
        sock.settimeout(timeout)
        return
    
    def getline(self):
        line = str(self.sock.recv(MAXLINE), self.encoding)
        if len(line) > MAXLINE:
            raise Error("got more than %d bytes" % MAXLINE)
        if not line:
            raise EOFError
        return line.rstrip('\r\n')

    def getmultiline(self):
        line = self.getline()
        if line[3:4] == '-':
            code = line[:3]
            while 1:
                nextline = self.getline()
                line = line + ('\n' + nextline)
                if nextline[:3] == code and \
                        nextline[3:4] != '-':
                    break
        return line

    def getresp(self):
        resp = self.getmultiline()
        c = resp[:1]
        if c in ['1', '2', '3']:
            return resp
        if c == '4':
            raise TempError(resp)
        if c == '5':
            raise PermError(resp)
        raise ProtoError(resp)

    def voidresp(self):
        resp = self.getresp()
        if not resp.startswith('2'):
            raise ReplyError(resp)
        return resp

    def sendcmd(self, cmd, re=True):
        cmd += CRLF
        self.sock.send(cmd.encode(self.encoding))
        if re==True:
            return self.getresp()
        else:
            return

    def voidcmd(self, cmd):
        resp = self.sendcmd(cmd)
        if not resp.startswith('2'):
            raise ReplyError(resp)
        return resp

    def makepasv(self):
        host, port = parse227(self.sendcmd('PASV'))
        return host, port

    def transfercmd(self, cmd, fp=None, callback=None, blocksize=MAXLINE, rest=None):
        host, port = self.makepasv()
        cmd_prefix = cmd[:4]
        print(host)
        print(port)
        conn = self._create_connection((self.host, port), self.timeout)
        try:
            if rest is not None:
                self.sendcmd("REST %s" % rest)

            resp = self.sendcmd(cmd)
            if resp[0] == '2':
                resp = self.getresp()
            if resp[0] != '1':
                raise ReplyError(resp)
            while 1:
                if cmd_prefix in ['STOR']:
                    data = fp.read(blocksize)
                elif cmd_prefix in ['LIST', 'RETR', 'NLST']:
                    data = conn.recv(blocksize)
                else:
                    raise ValueError('Unknown Command')
                if not data:
                    break
                if cmd_prefix in ['STOR']:
                    conn.send(data)
                if callback:
                    callback(data)
        except:
            conn.close()
            raise
        conn.close()
        return self.voidresp()

    def stor(self, localname, remotename=None, **kw):
        remotename = localname if not remotename else remotename
        with open(localname, 'rb') as fp:
            return self.transfercmd('STOR ' + remotename, fp=fp, **kw)

    def retr(self, filename, **kw):
        return self.transfercmd('RETR ' + filename, **kw)

    def list(self, *args, **kw):
        return self.transfercmd(" ".join(['LIST'] + list(args)), **kw)

    def abort(self):
        line = b'ABOR' + B_CRLF
        self.sock.send(line, 0x1)
        resp = self.getmultiline()
        if resp[:3] not in ['426', '225', '226']:
            raise ProtoError(resp)
        return resp

    def rename(self, fromname, toname):
        resp = self.sendcmd('RNFR ' + fromname)
        if resp[0] != '3':
            raise ReplyError(resp)
        return self.voidcmd('RNTO ' + toname)

    def delete(self, filename):
        resp = self.sendcmd('DELE ' + filename)
        if resp[:3] in ['250', '200']:
            return resp
        else:
            raise ReplyError(resp)

    def cwd(self, dirname):
        cmd = 'CWD ' + dirname if dirname != '..' else 'CDUP'
        return self.voidcmd(cmd)

    def size(self, filename):
        resp = self.sendcmd('SIZE ' + filename)
        if resp[:3] == '213':
            s = resp[3:].strip()
            return int(s)
        return 0

    def mkd(self, dirname):
        resp = self.voidcmd('MKD ' + dirname)
        return parse257(resp) if resp.startswith('257') else ''

    def rmd(self, dirname):
        return self.voidcmd('RMD ' + dirname)

    def pwd(self):
        resp = self.sendcmd('PWD')
        return '' if not resp.startswith('257') else parse257(resp)


def parse227(resp):
    if not resp.startswith('227'):
        raise ReplyError("Unexpected response: %s" % resp)
    try:
        left = resp.find('(')
        if left < 0:
            raise ValueError("missing left delimiter")
        right = resp.find(')', left + 1)
        if right < 0:
            raise ValueError("missing right delimiter")
        numbers = tuple(int(i) for i in resp[left+1:right].split(',', 6))
        host = '%i.%i.%i.%i' % numbers[:4]
        port = (numbers[4] << 8) + numbers[5]
    except Exception as exc:
        raise ProtoError("Error parsing response '%s': %s" % (resp, exc))

    return host, port

def parse257(resp):
    if resp[3:5] != ' "':
        return ''
    resp = resp.replace('257', '')
    resp = resp.replace('"', '')
    return resp.strip()
