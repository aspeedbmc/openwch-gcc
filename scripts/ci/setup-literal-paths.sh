#!/usr/bin/env bash
# Create the literal build-path symlink one version's build script requires.
#
# Usage: scripts/ci/setup-literal-paths.sh <version> [source-tree]
#
# The WCH toolchains embed their original build prefix in DWARF and in the
# configure string, so every build script refuses to run unless a symlink at
# the vendor's literal path points at the prepared source tree:
#
#   15.2.0 darwin  /Users/mrs/riscv-gnu-toolchain
#   15.2.0 linux   /home/wch/riscv-gnu-toolchain
#   12.2.0 darwin  /Users/mrs/Work/riscv-none-elf-gcc-xpack.git
#   8.2.0  darwin  /Users/wch/Work/riscv-none-embed-gcc-10.2.0-1.2
#
# THIS SCRIPT WRITES OUTSIDE THE REPOSITORY BY DESIGN.  It is therefore refused
# anywhere that is not a disposable CI environment.  The predicate below is the
# whole safety story, so it runs before anything else -- in particular before
# any sudo call, so a refusal never sits behind a password prompt.
#
# Allowed if and only if:
#   (container marker: /.dockerenv or /run/.containerenv or $container set)
#   OR (GITHUB_ACTIONS=true AND ACT unset)
#
# The second clause deliberately excludes act: `act -P <label>=-self-hosted`
# runs jobs directly on the host with GITHUB_ACTIONS=true, and that is exactly
# the configuration that would repoint a developer's real /Users/mrs.

set -euo pipefail

export LC_ALL=C

die() {
    printf 'setup-literal-paths.sh: %s\n' "$*" >&2
    exit 2
}

refuse() {
    cat >&2 <<'MESSAGE'
setup-literal-paths.sh: refusing to run.
This script creates symlinks at absolute vendor paths outside the repository
(/Users/mrs, /Users/wch, /home/wch).  It is only allowed inside a container or
on a GitHub-hosted runner.

Allowed when: a container marker exists (/.dockerenv, /run/.containerenv, or a
non-empty $container), or GITHUB_ACTIONS=true with ACT unset.

Observed: no container marker, and the GitHub Actions clause is not satisfied
(either GITHUB_ACTIONS is not "true", or ACT is set, which means act -- act can
be pointed at the host with -P <label>=-self-hosted, so it is never trusted for
this operation).
MESSAGE
    exit 3
}

in_container=0
if [ -e /.dockerenv ] || [ -e /run/.containerenv ] || [ -n "${container:-}" ]; then
    in_container=1
fi
on_github_runner=0
if [ "${GITHUB_ACTIONS:-}" = "true" ] && [ -z "${ACT:-}" ]; then
    on_github_runner=1
fi
if [ "$in_container" -ne 1 ] && [ "$on_github_runner" -ne 1 ]; then
    refuse
fi

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    printf 'usage: %s <15.2.0|12.2.0|8.2.0> [source-tree]\n' "${0##*/}" >&2
    exit 2
fi

version=$1
case "$version" in
    15.2.0|12.2.0|8.2.0) ;;
    *) die "unsupported version: $version" ;;
esac

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(CDPATH= cd -- "$script_dir/../.." && pwd -P)
[ -f "$repo_root/AGENTS.md" ] || die "not running from an openwch repository: $repo_root"

host_os=$(uname -s)
host_arch=$(uname -m)
case "$host_os/$host_arch" in
    Darwin/arm64) platform=darwin-arm64 ;;
    Linux/x86_64|Linux/amd64) platform=linux-amd64 ;;
    *) die "unsupported host platform: $host_os/$host_arch" ;;
esac

default_root=${CI_SRC_ROOT:-$repo_root/tmp/ci-src}
case "$platform/$version" in
    darwin-arm64/15.2.0)
        literal=/Users/mrs/riscv-gnu-toolchain
        target=${2:-$default_root/15.2.0/riscv-gnu-toolchain}
        ;;
    linux-amd64/15.2.0)
        literal=/home/wch/riscv-gnu-toolchain
        target=${2:-$default_root/15.2.0/riscv-gnu-toolchain}
        ;;
    darwin-arm64/12.2.0)
        literal=/Users/mrs/Work/riscv-none-elf-gcc-xpack.git
        target=${2:-$default_root/12.2.0/riscv-none-elf-gcc-xpack.git}
        ;;
    darwin-arm64/8.2.0)
        # build-toolchain-8.2.0.sh:52 hard-codes this project root.
        literal=/Users/wch/Work/riscv-none-embed-gcc-10.2.0-1.2
        target=${2:-$repo_root/tmp/toolchain_8.2.0/work}
        ;;
    *) die "unsupported version/platform combination: $version/$platform" ;;
esac

[ -d "$target" ] || die "source tree does not exist: $target"
target=$(CDPATH= cd -- "$target" && pwd -P)

# The build scripts compare readlink(literal) against the resolved tree, so the
# link must carry the physical path, not a path with symlinks in it.
parent=$(dirname -- "$literal")

# A GitHub-hosted macOS runner user cannot create /Users/<name>: those are root
# territory.  The runner provides passwordless sudo for exactly this kind of
# setup step.  Inside a container the process is already root, so sudo is
# neither present nor needed.  Try unprivileged first and escalate only on a
# real failure, so the container path never depends on sudo existing.
escalate() {
    if [ "$(id -u)" -eq 0 ]; then
        die "$1"
    fi
    command -v sudo >/dev/null 2>&1 || die "$1 (and sudo is unavailable)"
    privileged=sudo
}

privileged=none
if ! mkdir -p "$parent" 2>/dev/null; then
    escalate "cannot create $parent"
    sudo mkdir -p "$parent"
fi
if [ -e "$literal" ] && [ ! -L "$literal" ]; then
    die "literal path exists and is not a symlink: $literal"
fi
if ! ln -sfn "$target" "$literal" 2>/dev/null; then
    escalate "cannot create the symlink $literal"
    sudo ln -sfn "$target" "$literal"
fi

actual=$(readlink "$literal")
[ "$actual" = "$target" ] || die "symlink verification failed: $actual != $target"

printf 'literal_path=%s\n' "$literal"
printf 'literal_target=%s\n' "$target"
printf 'privileged=%s\n' "$privileged"
