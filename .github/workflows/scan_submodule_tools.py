#!/usr/bin/env python3
"""
Scan MODULE.bazel for git_override declarations and check which tools have submodules.
Outputs JSON with tool information.
"""

import json
import re
import subprocess
import sys
from typing import Dict, List

def parse_git_overrides(module_bazel_path: str) -> List[Dict[str, str]]:
    """Parse git_override declarations from MODULE.bazel."""
    with open(module_bazel_path, 'r') as f:
        content = f.read()

    # Match git_override blocks
    pattern = r'git_override\s*\(\s*module_name\s*=\s*"([^"]+)"[^)]*commit\s*=\s*"([^"]+)"[^)]*remote\s*=\s*"([^"]+)"'
    matches = re.findall(pattern, content, re.DOTALL)

    tools = []
    for module_name, commit, remote in matches:
        # Extract owner/repo from remote URL
        repo_match = re.search(r'github\.com[:/]([^/]+)/([^/\.]+)', remote)
        if repo_match:
            owner = repo_match.group(1)
            repo = repo_match.group(2)
            tools.append({
                'module_name': module_name,
                'commit': commit,
                'remote': remote,
                'owner': owner,
                'repo': repo
            })

    return tools

def check_submodules(owner: str, repo: str, commit: str) -> bool:
    """Check if a repository has submodules at the given commit."""
    gitmodules_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{commit}/.gitmodules"
    try:
        result = subprocess.run(
            ['curl', '-sf', gitmodules_url],
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except:
        return False

def main():
    tools = parse_git_overrides('MODULE.bazel')

    tools_with_submodules = []
    tools_without_submodules = []

    for tool in tools:
        has_submodules = check_submodules(tool['owner'], tool['repo'], tool['commit'])
        tool['has_submodules'] = has_submodules

        if has_submodules:
            tools_with_submodules.append(tool)
        else:
            tools_without_submodules.append(tool)

    output = {
        'with_submodules': tools_with_submodules,
        'without_submodules': tools_without_submodules
    }

    print(json.dumps(output, indent=2))

if __name__ == '__main__':
    main()
