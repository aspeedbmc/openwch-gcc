#!/usr/bin/env bash
# Provision the official WCH toolchain for one version into the exact tree
# layout scripts/evt-golden.sh and scripts/evt-compare.sh hard-code, namely
# <repo>/ref/gcc/<platform>/<version>/.  Both gate scripts derive that path
# themselves (evt-golden.sh:60, evt-compare.sh:51), so nothing downstream takes
# a toolchain argument: putting the package here is the whole interface.
#
# Usage: scripts/ci/provision-official.sh <15.2.0|12.2.0|8.2.0>
#
# Environment:
#   OFFICIAL_DEST_ROOT  destination root, default <repo>/ref/gcc
#   OFFICIAL_CACHE_DIR  archive cache, default <repo>/tmp/ci-cache/official
#   OFFICIAL_ARCHIVE    use this already-downloaded archive instead of the API
#   COMPILER_PATH       opt-in override: point the destination at an existing
#                       toolchain instead of downloading anything.  This exists
#                       for fast local iteration only; an evidence run must
#                       leave it unset so the download is real.
#
# Sources of every pinned constant below:
#   linux-amd64/15.2.0  ref/wch-evt/tools/fetch_wch_toolchain.py (reused as is)
#   darwin-arm64/*      tmp/p7-evidence/S0/darwin-pkg/darwin-verdict.md
#
# The MounRiver signed download URL embeds the caller's egress IP and expires,
# so it can never be pinned; the resourceId, the archive size and the archive
# SHA-256 are what get pinned, and the URL is resolved inside the job.

set -euo pipefail

export LC_ALL=C

die() {
    printf 'provision-official.sh: %s\n' "$*" >&2
    exit 2
}

if [ "$#" -ne 1 ]; then
    printf 'usage: %s <15.2.0|12.2.0|8.2.0>\n' "${0##*/}" >&2
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

# Platform detection follows scripts/evt-golden.sh:32-36 verbatim.  Do not
# invent a second spelling: the manifest file name is <version>-<platform>.tsv
# and a divergent platform string silently splits the gate baseline.
host_os=$(uname -s)
host_arch=$(uname -m)
case "$host_os/$host_arch" in
    Darwin/arm64) platform=darwin-arm64 ;;
    Linux/x86_64|Linux/amd64) platform=linux-amd64 ;;
    *) die "unsupported host platform: $host_os/$host_arch" ;;
esac
case "$platform/$version" in
    darwin-arm64/15.2.0|darwin-arm64/12.2.0|darwin-arm64/8.2.0|linux-amd64/15.2.0) ;;
    *) die "unsupported version/platform combination: $version/$platform" ;;
esac

dest_root=${OFFICIAL_DEST_ROOT:-$repo_root/ref/gcc}
destination="$dest_root/$platform/$version"
cache_dir=${OFFICIAL_CACHE_DIR:-$repo_root/tmp/ci-cache/official}

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

# Per-version identity of the shipped driver.  Checking it makes the whole
# provisioning step idempotent and turns a truncated or half-extracted tree
# into a hard failure instead of a confusing build error later.
case "$version" in
    15.2.0)
        compiler_relative=bin/riscv32-wch-elf-gcc
        expected_machine=riscv32-wch-elf
        ;;
    12.2.0)
        compiler_relative=bin/riscv-wch-elf-gcc
        expected_machine=riscv-wch-elf
        ;;
    8.2.0)
        compiler_relative=bin/riscv-none-embed-gcc
        expected_machine=riscv-none-embed
        ;;
esac
case "$platform/$version" in
    linux-amd64/15.2.0)
        compiler_sha256=9527827d2004aaddfeb3ecac030d0a0ec19678e9601e3ffdb18f9a3100b9bd99 ;;
    darwin-arm64/15.2.0)
        compiler_sha256=339104dfa2792244e90a3f44bd1f1ff3435917a7668ab83f33241d5d9c2c2829 ;;
    darwin-arm64/12.2.0)
        compiler_sha256=6848518844ec7757e68055108702efd2910e614c36193d29e83183a5d5ebdbb9 ;;
    darwin-arm64/8.2.0)
        compiler_sha256=9d693fae19e3c9aa52e57683612235571e7c91ce7f1d0025b053df728f4fa14f ;;
esac

report_and_exit() {
    local compiler="$destination/$compiler_relative"
    local machine
    [ -x "$compiler" ] || die "provisioned compiler is not executable: $compiler"
    [ "$(sha256_of "$compiler")" = "$compiler_sha256" ] || \
        die "provisioned compiler SHA-256 mismatch: $compiler"
    machine=$("$compiler" -dumpmachine)
    [ "$machine" = "$expected_machine" ] || \
        die "provisioned compiler reports $machine, expected $expected_machine"
    printf 'official_platform=%s\n' "$platform"
    printf 'official_version=%s\n' "$version"
    printf 'official_root=%s\n' "$destination"
    printf 'official_compiler=%s\n' "$compiler"
    printf 'official_compiler_sha256=%s\n' "$compiler_sha256"
    printf 'official_identity=%s\n' "$("$compiler" --version | sed -n 1p)"
    exit 0
}

# --- opt-in override -------------------------------------------------------
# COMPILER_PATH names an already-extracted toolchain; the destination becomes a
# symlink to its root so the gate scripts still find ref/gcc/<platform>/<ver>.
# Default (unset) is a real download; evidence runs must not set it.
if [ -n "${COMPILER_PATH:-}" ]; then
    [ -x "$COMPILER_PATH" ] || die "COMPILER_PATH is not executable: $COMPILER_PATH"
    override_bin=$(CDPATH= cd -- "$(dirname -- "$COMPILER_PATH")" && pwd -P)
    [ "${override_bin##*/}" = bin ] || die "COMPILER_PATH must live in a toolchain bin directory"
    override_root=$(CDPATH= cd -- "$override_bin/.." && pwd -P)
    mkdir -p "$(dirname -- "$destination")"
    if [ -L "$destination" ] || [ -e "$destination" ]; then
        [ -L "$destination" ] || die "refusing to replace non-symlink destination: $destination"
        rm -f -- "$destination"
    fi
    ln -s "$override_root" "$destination"
    printf 'provision_mode=compiler-path-override\n'
    report_and_exit
fi

# --- already provisioned ---------------------------------------------------
if [ -x "$destination/$compiler_relative" ] && \
        [ "$(sha256_of "$destination/$compiler_relative")" = "$compiler_sha256" ]; then
    printf 'provision_mode=already-present\n'
    report_and_exit
fi

mkdir -p "$cache_dir"

if [ "$platform" = linux-amd64 ]; then
    # Reuse the repository's existing, already-audited fetcher rather than
    # writing a second downloader with its own pins.  It verifies archive size,
    # archive SHA-256 and the extracted driver's SHA-256 before returning.
    fetcher="$repo_root/ref/wch-evt/tools/fetch_wch_toolchain.py"
    [ -f "$fetcher" ] || die "missing fetcher: $fetcher"
    printf 'provision_mode=linux-fetch-script\n'
    if [ -n "${OFFICIAL_ARCHIVE:-}" ]; then
        [ -f "$OFFICIAL_ARCHIVE" ] || die "OFFICIAL_ARCHIVE does not exist: $OFFICIAL_ARCHIVE"
        python3 "$fetcher" --destination "$destination" --archive "$OFFICIAL_ARCHIVE"
    else
        python3 "$fetcher" --destination "$destination" --cache-dir "$cache_dir"
    fi
    report_and_exit
fi

# --- darwin ----------------------------------------------------------------
# One MounRiver macOS package carries all three RISC-V toolchains, so the
# archive cache is shared by the three darwin jobs and keyed on its SHA-256.
darwin_archive_name=MounRiver_Studio_MacOS_ARM64_V2.5.0.tar.gz
darwin_archive_bytes=1434575083
darwin_archive_sha256=189fdb95e898ec3f5ce4028166dd06c829f503227b6f8ae1a13bace9ec04937e
darwin_resource_id=2071922455275941890
darwin_download_api=https://api.mounriver.com/mountriver/api/version/getDownloadUrl
darwin_prefix='./MounRiver Studio 2.app/Contents/Resources/app/resources/darwin/components/WCH/Toolchain'
case "$version" in
    15.2.0) darwin_member='RISC-V Embedded GCC15' ;;
    12.2.0) darwin_member='RISC-V Embedded GCC12' ;;
    8.2.0)  darwin_member='RISC-V Embedded GCC' ;;
esac

command -v curl >/dev/null || die "curl is unavailable"
command -v python3 >/dev/null || die "python3 is unavailable"
command -v tar >/dev/null || die "tar is unavailable"

validate_darwin_archive() {
    local path=$1 bytes
    [ -f "$path" ] || return 1
    bytes=$(wc -c < "$path" | tr -d '[:space:]')
    [ "$bytes" = "$darwin_archive_bytes" ] || return 1
    [ "$(sha256_of "$path")" = "$darwin_archive_sha256" ] || return 1
    return 0
}

archive="$cache_dir/$darwin_archive_name"
if [ -n "${OFFICIAL_ARCHIVE:-}" ]; then
    archive=$OFFICIAL_ARCHIVE
    validate_darwin_archive "$archive" || die "OFFICIAL_ARCHIVE failed size/SHA-256 verification: $archive"
    printf 'provision_mode=darwin-local-archive\n'
elif validate_darwin_archive "$archive"; then
    printf 'provision_mode=darwin-cache-hit\n'
    printf 'WCH_TOOLCHAIN_CACHE_HIT archive=%s\n' "$archive"
else
    rm -f -- "$archive"
    printf 'provision_mode=darwin-network-download\n'
    signed_url=$(curl -fsS -H 'Accept: application/json' \
        "$darwin_download_api?resourceId=$darwin_resource_id" | \
        python3 -c 'import json,sys,urllib.parse
payload = json.load(sys.stdin)
url = payload.get("result") if isinstance(payload, dict) else None
parts = urllib.parse.urlsplit(url or "")
if parts.scheme != "https" or not parts.netloc:
    raise SystemExit("MounRiver API returned an invalid HTTPS download URL")
print(url)') || die "cannot resolve the MounRiver signed download URL"
    printf 'WCH_TOOLCHAIN_NETWORK_DOWNLOAD archive=%s\n' "$darwin_archive_name"
    curl -fsSL --retry 3 --max-time 1800 -o "$archive.part" "$signed_url" || \
        die "download failed for $darwin_archive_name"
    mv -f -- "$archive.part" "$archive"
    validate_darwin_archive "$archive" || \
        die "downloaded archive failed size/SHA-256 verification: $archive"
fi

# tmp/ is gitignored, so a fresh checkout does not have it: git does not
# track empty directories.  Create it before mktemp rather than assuming.
mkdir -p "$repo_root/tmp"
workdir=$(mktemp -d "$repo_root/tmp/.provision-official.XXXXXX")
cleanup() {
    rm -rf -- "$workdir"
}
trap cleanup EXIT INT TERM

# -p keeps the package's own permission bits.  Without it the extraction runs
# through the caller's umask, which is what flattened the directory modes in
# the hand-installed copy of this package (darwin-verdict.md 3.2).
tar -xzp -f "$archive" -C "$workdir" "$darwin_prefix/$darwin_member"
[ -d "$workdir/$darwin_prefix/$darwin_member" ] || \
    die "expected member missing from archive: $darwin_prefix/$darwin_member"

mkdir -p "$(dirname -- "$destination")"
if [ -e "$destination" ] || [ -L "$destination" ]; then
    case "$destination" in
        "$dest_root/$platform/$version") rm -rf -- "$destination" ;;
        *) die "refusing to remove unexpected destination: $destination" ;;
    esac
fi
mv -- "$workdir/$darwin_prefix/$darwin_member" "$destination"

# Observed on the 8.2.0 executables only, and not enforced on this host.  Probe
# before acting: an unconditional xattr sweep would hide a real Gatekeeper
# change behind a step that always "succeeds".
if command -v xattr >/dev/null 2>&1; then
    if xattr -p com.apple.quarantine "$destination/$compiler_relative" >/dev/null 2>&1; then
        printf 'quarantine_attribute=present action=stripped\n'
        xattr -dr com.apple.quarantine "$destination"
    else
        printf 'quarantine_attribute=absent action=none\n'
    fi
fi

report_and_exit
