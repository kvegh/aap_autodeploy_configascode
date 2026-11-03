"""Verify one upstream's installed CA and DNS identity without sending credentials."""

import hashlib
import ipaddress
import json
from pathlib import Path
import socket
import ssl
import sys


def verify(address, hostname, ca_file, port=443):
    ipaddress.ip_address(address)
    if not hostname or any(character.isspace() for character in hostname):
        raise ValueError("Invalid upstream identity")
    authority = Path(ca_file)
    if not authority.is_absolute() or not authority.is_file():
        raise ValueError("Missing installed authority")
    context = ssl.create_default_context(cafile=str(authority))
    with socket.create_connection((address, int(port)), timeout=20) as stream:
        with context.wrap_socket(stream, server_hostname=hostname) as connection:
            return {"verified": True, "certificate_sha256": hashlib.sha256(
                connection.getpeercert(binary_form=True)).hexdigest()}


if __name__ == "__main__":
    try:
        output = verify(*sys.argv[1:])
    except ssl.SSLCertVerificationError:
        output = {"verified": False, "reason": "certificate_or_hostname"}
    except (OSError, ValueError, ssl.SSLError, TypeError):
        output = {"verified": False, "reason": "connection_or_installed_authority"}
    print(json.dumps(output))
    sys.exit(0 if output["verified"] else 1)
