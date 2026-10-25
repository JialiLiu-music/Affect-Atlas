"""Download only the verified existing source head over pinned SSH.

Password comes from MER_SSH_PASSWORD in process memory. No credentials or
remote commands are stored. Refuses host-key changes and unknown head bytes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import paramiko

HEAD_SHA = '18a8f83c9ed879a6c214f8f21332a048dcf9196c2d8766f89b4cf35e6f3c469d'
REMOTE_HEAD = '/root/autodl-tmp/music-emotion-rebuild-20261008/runs/static-emotion-v2-20261008/mean_mlp-seed20261011/best.pt'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--host-key-record', type=Path, required=True)
    args = parser.parse_args()
    expected = json.loads(args.host_key_record.read_text(encoding='utf-8'))['sha256_hex']
    class PinnedKey(paramiko.MissingHostKeyPolicy):
        def missing_host_key(self, client, hostname, key):
            actual = hashlib.sha256(key.asbytes()).hexdigest()
            if actual != expected:
                raise paramiko.SSHException('Observed SSH host key differs from recorded identity')
            client.get_host_keys().add(hostname, key.get_name(), key)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(PinnedKey())
    destination = args.destination.resolve()
    if destination.exists():
        if hashlib.sha256(destination.read_bytes()).hexdigest() != HEAD_SHA:
            raise RuntimeError('Existing destination has unexpected bytes; refusing overwrite')
        print('HEAD_ALREADY_VERIFIED', HEAD_SHA)
        return
    partial = destination.with_suffix('.pt.part')
    try:
        client.connect('connect.nmb2.seetacloud.com', port=31740, username='root',
                       password=os.environ.pop('MER_SSH_PASSWORD'), timeout=20,
                       auth_timeout=20, banner_timeout=20, look_for_keys=False, allow_agent=False)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with client.open_sftp() as sftp:
            sftp.get(REMOTE_HEAD, str(partial))
        digest = hashlib.sha256(partial.read_bytes()).hexdigest()
        if digest != HEAD_SHA:
            raise RuntimeError('Downloaded source head failed experiment SHA256 check')
        partial.replace(destination)
        print('HEAD_DOWNLOADED_AND_VERIFIED', str(destination), digest)
    finally:
        partial.unlink(missing_ok=True)
        client.close()


if __name__ == '__main__':
    main()
