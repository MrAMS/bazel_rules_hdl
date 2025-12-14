#!/usr/bin/env python3
"""
Generate release notes with archive_override examples for ALL tools from git_override.
"""

import json
import sys
from pathlib import Path

def main():
    if len(sys.argv) != 5:
        print("Usage: generate_release_notes.py <packages_dir> <tools_info_json> <tag_name> <repository>", file=sys.stderr)
        sys.exit(1)

    packages_dir = Path(sys.argv[1])
    tools_info_path = Path(sys.argv[2])
    tag_name = sys.argv[3]
    repository = sys.argv[4]

    # Load tools info (all git_override tools)
    with open(tools_info_path) as f:
        tools_info = json.load(f)

    # Load packaged tools (tools with submodules)
    packages_json = packages_dir / 'packages.json'
    with open(packages_json) as f:
        packaged_tools = json.load(f)

    # Load integrity info for tools without submodules
    integrities_json = packages_dir / 'no_submodule_integrities.json'
    no_submodule_integrities = []
    if integrities_json.exists():
        with open(integrities_json) as f:
            no_submodule_integrities = json.load(f)

    # Create lookup dict for packaged tools
    packaged_lookup = {pkg['module_name']: pkg for pkg in packaged_tools}

    # Create lookup dict for no-submodule integrities
    integrity_lookup = {item['module_name']: item for item in no_submodule_integrities}

    # Generate release notes
    notes = f"""Automated CI release - archive_override for all git_override tools.

---

## 📦 What's Included

This release provides **archive_override** configurations for ALL tools that use `git_override` in MODULE.bazel:

### Tools WITH Submodules (pre-packaged with submodules included)
"""

    for tool in tools_info['with_submodules']:
        commit_url = f"https://github.com/{tool['owner']}/{tool['repo']}/commit/{tool['commit']}"
        notes += f"- **{tool['module_name']}** (commit [`{tool['commit'][:7]}`]({commit_url}))\n"

    notes += f"""
### Tools WITHOUT Submodules (using GitHub archive URLs)
"""

    for tool in tools_info['without_submodules']:
        commit_url = f"https://github.com/{tool['owner']}/{tool['repo']}/commit/{tool['commit']}"
        notes += f"- **{tool['module_name']}** (commit [`{tool['commit'][:7]}`]({commit_url}))\n"

    notes += f"""

---

## 🚀 Usage in Your Project

Replace `git_override` with `archive_override` for faster CI builds:

```bzl
"""

    # First output tools WITH submodules (from packaged archives)
    notes += """# =============================================================================
# Tools WITH submodules - use CI-packaged archives
# =============================================================================

"""
    for tool in tools_info['with_submodules']:
        module_name = tool['module_name']
        if module_name in packaged_lookup:
            pkg = packaged_lookup[module_name]
            url = f"https://github.com/{repository}/releases/download/{tag_name}/{pkg['tarball_name']}"
            notes += f"""bazel_dep(name = "{module_name}", version = "1.0.0")
archive_override(
    module_name = "{module_name}",
    urls = ["{url}"],
    strip_prefix = "{pkg['strip_prefix']}",
    integrity = "{pkg['integrity']}",
)

"""

    # Then output tools WITHOUT submodules (direct GitHub archive)
    notes += """# =============================================================================
# Tools WITHOUT submodules - use direct GitHub archive
# =============================================================================

"""
    for tool in tools_info['without_submodules']:
        module_name = tool['module_name']
        owner = tool['owner']
        repo = tool['repo']
        commit = tool['commit']

        # Use GitHub's archive URL
        archive_url = f"https://github.com/{owner}/{repo}/archive/{commit}.tar.gz"
        strip_prefix = f"{repo}-{commit}"

        # Check if we have pre-calculated integrity
        if module_name in integrity_lookup:
            integrity = integrity_lookup[module_name]['integrity']
            notes += f"""bazel_dep(name = "{module_name}", version = "1.0.0")
archive_override(
    module_name = "{module_name}",
    urls = ["{archive_url}"],
    strip_prefix = "{strip_prefix}",
    integrity = "{integrity}",
)

"""
        else:
            # Fallback: no integrity available
            notes += f"""bazel_dep(name = "{module_name}", version = "1.0.0")
archive_override(
    module_name = "{module_name}",
    urls = ["{archive_url}"],
    strip_prefix = "{strip_prefix}",
    # Note: No integrity hash provided for GitHub archives
    # You can calculate it with: curl -L <url> | sha256sum | xxd -r -p | base64 -w0
)

"""

    notes += """```

---

## 📝 Notes

### For Tools WITH Submodules
- Pre-packaged archives include **all submodules initialized**
- These are ready to use - just copy the `archive_override` block

### For Tools WITHOUT Submodules
- Direct GitHub archive URLs are provided
- **Integrity hashes are pre-calculated** by CI for security and reproducibility
- Ready to use - just copy the `archive_override` block

### Why Use archive_override?
- ✅ **Much faster** in CI/CD environments (no git operations)
- ✅ **Reproducible** builds with integrity hashes
- ✅ **No git required** in build environment
- ❌ Less convenient for active development (prefer `git_override` for development)

## ⚙️ How This Release Was Generated

1. Scanned `MODULE.bazel` for all `git_override` declarations
2. Checked each repository for `.gitmodules` file
3. **For tools WITH submodules:**
   - Cloned with `git clone --recursive`
   - Created tarballs excluding `.git` directories
   - Calculated `sha256-base64` integrity hashes
4. **For tools WITHOUT submodules:**
   - Downloaded GitHub archive URLs
   - Calculated `sha256-base64` integrity hashes

---

**Generated by** [rules_hdl CI](https://github.com/{repository}/actions)
"""

    print(notes)

if __name__ == '__main__':
    main()
