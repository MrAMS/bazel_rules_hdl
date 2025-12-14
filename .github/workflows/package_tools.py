#!/usr/bin/env python3
"""
Package tools with submodules into archive files with integrity hashes.
"""

import hashlib
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

def clone_with_submodules(owner: str, repo: str, commit: str, temp_dir: Path):
    """Clone repository with submodules at specific commit."""
    clone_dir = temp_dir / repo

    # Clone repository
    subprocess.run([
        'git', 'clone',
        f'https://github.com/{owner}/{repo}.git',
        str(clone_dir)
    ], check=True)

    # Checkout specific commit
    subprocess.run(
        ['git', 'checkout', commit],
        cwd=clone_dir,
        check=True
    )

    # Initialize and update submodules
    subprocess.run(
        ['git', 'submodule', 'update', '--init', '--recursive'],
        cwd=clone_dir,
        check=True
    )

    return clone_dir

def create_tarball(source_dir: Path, output_file: Path):
    """Create tarball from source directory."""
    # Get parent directory and directory name
    parent = source_dir.parent
    dirname = source_dir.name

    subprocess.run([
        'tar',
        '--exclude=.git',
        '-czf',
        str(output_file),
        '-C', str(parent),
        dirname
    ], check=True)

def calculate_integrity(tarball_path: Path) -> str:
    """Calculate Bazel bzlmod integrity hash (sha256-base64)."""
    sha256 = hashlib.sha256()
    with open(tarball_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)

    hash_bytes = sha256.digest()
    hash_base64 = base64.b64encode(hash_bytes).decode('ascii')
    return f"sha256-{hash_base64}"

def calculate_github_archive_integrity(owner: str, repo: str, commit: str) -> str:
    """Download GitHub archive and calculate its integrity hash."""
    import tempfile
    import urllib.request

    archive_url = f"https://github.com/{owner}/{repo}/archive/{commit}.tar.gz"

    # Download to temp file
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)
        try:
            print(f"  Downloading {archive_url}...", file=sys.stderr)
            urllib.request.urlretrieve(archive_url, tmp_path)

            # Calculate integrity
            integrity = calculate_integrity(tmp_path)
            return integrity
        finally:
            # Cleanup
            if tmp_path.exists():
                tmp_path.unlink()

def package_tool(tool: dict, output_dir: Path, tag_name: str) -> dict:
    """Package a tool and return package info."""
    module_name = tool['module_name']
    owner = tool['owner']
    repo = tool['repo']
    commit = tool['commit']

    print(f"📦 Packaging {module_name}...", file=sys.stderr)

    # Create temp directory for cloning
    temp_dir = Path(f'/tmp/package_{module_name}')
    temp_dir.mkdir(exist_ok=True)

    try:
        # Clone with submodules
        clone_dir = clone_with_submodules(owner, repo, commit, temp_dir)

        # Rename directory to match strip_prefix (repo-commit)
        target_dirname = f"{repo}-{commit}"
        target_dir = temp_dir / target_dirname
        if clone_dir != target_dir:
            clone_dir.rename(target_dir)
            clone_dir = target_dir

        # Create tarball
        tarball_name = f"{module_name}-{tag_name}.tar.gz"
        tarball_path = output_dir / tarball_name
        create_tarball(clone_dir, tarball_path)

        # Calculate integrity
        integrity = calculate_integrity(tarball_path)

        # Write integrity to separate file
        integrity_file = output_dir / f"{tarball_name}.sha256"
        integrity_file.write_text(integrity)

        print(f"✅ {module_name}: {integrity}", file=sys.stderr)

        return {
            'module_name': module_name,
            'tarball_name': tarball_name,
            'integrity': integrity,
            'commit': commit,
            'strip_prefix': target_dirname  # Use the renamed directory name
        }

    finally:
        # Cleanup temp directory
        subprocess.run(['rm', '-rf', str(temp_dir)], check=True)

def main():
    if len(sys.argv) != 4:
        print("Usage: package_tools.py <tools_info.json> <output_dir> <tag_name>", file=sys.stderr)
        sys.exit(1)

    tools_info_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    tag_name = sys.argv[3]

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load tools info
    with open(tools_info_path) as f:
        tools_info = json.load(f)

    # Package each tool with submodules
    packages = []
    for tool in tools_info['with_submodules']:
        try:
            package_info = package_tool(tool, output_dir, tag_name)
            packages.append(package_info)
        except Exception as e:
            print(f"❌ Failed to package {tool['module_name']}: {e}", file=sys.stderr)

    # Calculate integrity for tools without submodules
    no_submodule_integrities = []
    for tool in tools_info['without_submodules']:
        try:
            module_name = tool['module_name']
            owner = tool['owner']
            repo = tool['repo']
            commit = tool['commit']

            print(f"🔢 Calculating integrity for {module_name}...", file=sys.stderr)
            integrity = calculate_github_archive_integrity(owner, repo, commit)
            print(f"✅ {module_name}: {integrity}", file=sys.stderr)

            no_submodule_integrities.append({
                'module_name': module_name,
                'owner': owner,
                'repo': repo,
                'commit': commit,
                'integrity': integrity
            })
        except Exception as e:
            print(f"❌ Failed to calculate integrity for {tool['module_name']}: {e}", file=sys.stderr)

    # Write package info
    packages_json = output_dir / 'packages.json'
    with open(packages_json, 'w') as f:
        json.dump(packages, f, indent=2)

    # Write integrity info for tools without submodules
    integrities_json = output_dir / 'no_submodule_integrities.json'
    with open(integrities_json, 'w') as f:
        json.dump(no_submodule_integrities, f, indent=2)

    print(f"\n✅ Packaged {len(packages)} tools with submodules", file=sys.stderr)
    print(f"✅ Calculated integrity for {len(no_submodule_integrities)} tools without submodules", file=sys.stderr)

if __name__ == '__main__':
    main()
