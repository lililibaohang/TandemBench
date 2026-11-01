"""Check distribution file hashes without API access or model execution."""
import hashlib
import json
from pathlib import Path


def main():
    root=Path(__file__).resolve().parent
    manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for name,expected in manifest['files'].items():
        file=root/name
        if file.is_symlink() or not file.resolve().is_relative_to(root) or not file.is_file():
            raise ValueError('Missing or invalid package path: '+name)
        if hashlib.sha256(file.read_bytes()).hexdigest()!=expected:
            raise ValueError('Hash mismatch: '+name)
    print(f"Verified {len(manifest['files'])} files; version {manifest['kit_version']}")


if __name__=='__main__':main()
