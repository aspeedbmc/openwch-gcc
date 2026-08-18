#!/usr/bin/env bash
# Build the pristine GCC 15.2.0/binutils 2.45 compiler-only toolchain and
# inject the official WCH target libraries/sysroot byte for byte.  binutils is
# configured with zstd and with the mmap probe result the official package has,
# and the official libzstd is shipped next to the programs that load it.
# Usage: scripts/build-toolchain-15.2.0.sh [expected-riscv-gnu-toolchain-root]
# Set BUILD_JOBS to override the default parallelism (8).
#
# Before building, the caller-applied source trees are verified against the
# public patch series exactly as the linux script does: every patch's stable id
# is checked against patches/15.2.0/patch-id.tsv (four columns since closure
# 7-2), the series lengths must be 9/7, and the ordered replay must reproduce
# the frozen trees pinned below.  Any mismatch dies before a single object is
# compiled, so a mutually edited series/ledger pair cannot look authoritative.
# Set SKIP_PATCH_VERIFY=1 only for a deliberately unpatched (pristine) build.

set -euo pipefail

export LC_ALL=C
export SOURCE_DATE_EPOCH=1767225600
export CC=/usr/bin/clang
export CXX=/usr/bin/clang++
unset CPPFLAGS CFLAGS CXXFLAGS LDFLAGS LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH

die() {
    printf 'build-toolchain-15.2.0.sh: %s\n' "$*" >&2
    exit 2
}

if [ "$#" -gt 1 ]; then
    printf 'usage: %s [expected-riscv-gnu-toolchain-root]\n' "${0##*/}" >&2
    exit 2
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
default_tree="$repo_root/tmp/toolchain_15.2.0/riscv-gnu-toolchain"
expected_argument=${1:-$default_tree}
[ -d "$expected_argument" ] || die "expected source tree does not exist: $expected_argument"
expected_tree=$(CDPATH= cd -- "$expected_argument" && pwd -P)
case "$expected_tree" in
    "$repo_root/tmp/"*) ;;
    *) die "expected source tree must be a child of $repo_root/tmp: $expected_tree" ;;
esac

literal_tree=/Users/mrs/riscv-gnu-toolchain
[ -L "$literal_tree" ] || die "required symlink is missing: $literal_tree"
link_target=$(readlink "$literal_tree")
[ "$link_target" = "$expected_tree" ] || \
    die "symlink target mismatch: expected $expected_tree, got $link_target"
[ -d "$literal_tree/gcc" ] || die "missing GCC source below symlink"
[ -d "$literal_tree/binutils" ] || die "missing binutils source below symlink"

gcc_source="$expected_tree/gcc"
binutils_source="$expected_tree/binutils"
build_gcc="$expected_tree/build-gcc"
build_binutils="$expected_tree/build-binutils"
output="$expected_tree/output"
logs="$expected_tree/logs"
official_root="$repo_root/ref/gcc/darwin-arm64/15.2.0"
official_gcc="$official_root/bin/riscv32-wch-elf-gcc"
target=riscv32-wch-elf
gcc_version=15.2.0
build_jobs=${BUILD_JOBS:-8}
# WCH links binutils against the Homebrew zstd 1.5.7 whose install name is
# /opt/homebrew/opt/zstd/lib/libzstd.1.dylib, and ships that library inside the
# package.  This host has no pkg-config, so PKG_CHECK_MODULES has to be fed
# directly; it accepts ZSTD_CFLAGS/ZSTD_LIBS verbatim whenever both are set.
# ZSTD_LIBS must keep the -L/-l shape: libtool records only -l/-L forms in the
# dependency_libs of libbfd.la, and that record is what makes every BFD
# consumer other than readelf inherit zstd, matching the official package.
zstd_cflags='-I/opt/homebrew/include'
zstd_libs='-L/opt/homebrew/lib -lzstd'
zstd_install_name=/opt/homebrew/opt/zstd/lib/libzstd.1.dylib
zstd_loader_name='@loader_path/libzstd.1.dylib'
zstd_bin_sha256=a63c44dbe4a0b7c8f21a039152b3c4b0b66d54cc1daeecc629ce02eee79f274e
zstd_target_sha256=de1dd7fed0e19e83c931fb4fbbb709c5f133faeda24aa5ea6cda1e1e3598d6d7
# AC_FUNC_MMAP compiles and then runs its probe.  On darwin-arm64 the probe is
# killed by the kernel at its MAP_FIXED-over-a-just-unmapped-page step, so the
# result is "no" regardless of whether mmap works.  The official package does
# have HAVE_MMAP: its elfedit carries the x86-feature options, and its BFD
# tools reference _mmap/_munmap.  Preset the autoconf cache variable, which is
# the documented escape hatch for run-time probes on a constrained host.
mmap_cache_override=ac_cv_func_mmap_fixed_mapped=yes
# The exact set of installed Mach-O files the official package links against
# libzstd, restricted to the programs this build produces (WCH also ships gdb
# and run, which are out of scope here).  Reproduced as a hard expectation so a
# change in libtool's dependency propagation fails the build instead of
# silently shipping a partially linked package.
zstd_expected_loader_relative="addr2line ar as c++filt gprof ld ld.bfd nm objcopy objdump ranlib readelf size strings strip"
zstd_expected_target_loader_relative="ar as ld nm objcopy objdump ranlib readelf strip"
# WCH ran install_name_tool over every program except this one, which kept the
# absolute install name.  Reproduce the omission rather than correct it.
zstd_absolute_keep="ld.bfd"

case "$build_jobs" in
    ''|*[!0-9]*) die "BUILD_JOBS must be a positive integer" ;;
    0) die "BUILD_JOBS must be greater than zero" ;;
esac
[ -x "$official_gcc" ] || die "missing official GCC: $official_gcc"
[ -x /usr/bin/clang ] || die "system clang is unavailable"
[ -x /usr/bin/clang++ ] || die "system clang++ is unavailable"
[ -x /bin/cp ] || die "macOS cp is unavailable"
command -v otool >/dev/null || die "otool is unavailable"
command -v install_name_tool >/dev/null || die "install_name_tool is unavailable"
[ -e /opt/homebrew/include/zstd.h ] || die "Homebrew zstd headers are unavailable"
[ -e /opt/homebrew/lib/libzstd.dylib ] || die "Homebrew zstd library is unavailable"

gcc_head=$(git -C "$gcc_source" rev-parse HEAD)
[ "$gcc_head" = 5115c7e447fc07457443df874bf57840e8316d5f ] || \
    die "unexpected GCC HEAD: $gcc_head"
binutils_head=$(git -C "$binutils_source" rev-parse HEAD)
[ "$binutils_head" = 2bc7af1ff7732451b6a7b09462a815c3284f9613 ] || \
    die "unexpected binutils HEAD: $binutils_head"
# The phase-2 vanilla tree must remain pristine.  A different explicitly
# supplied tree is allowed to contain the phase-3 patch series while retaining
# the same release HEAD, which is why cleanliness is conditional here.
if [ "$expected_tree" = "$default_tree" ]; then
    git -C "$gcc_source" diff --quiet || die "GCC tracked tree is modified"
    git -C "$gcc_source" diff --cached --quiet || die "GCC index is modified"
    git -C "$binutils_source" diff --quiet || die "binutils tracked tree is modified"
    git -C "$binutils_source" diff --cached --quiet || die "binutils index is modified"
fi
for prerequisite in gmp mpfr mpc isl; do
    [ -e "$gcc_source/$prerequisite" ] || die "missing in-tree prerequisite: $prerequisite"
done

safe_remove_build_path() {
    local path=$1
    case "$path" in
        "$expected_tree/build-gcc"|"$expected_tree/build-binutils"|"$expected_tree/output"|"$expected_tree/logs") ;;
        *) die "refusing to remove unexpected path: $path" ;;
    esac
    rm -rf -- "$path"
}

injection_stages=()
cleanup() {
    local stage
    for stage in ${injection_stages[@]+"${injection_stages[@]}"}; do
        case "$stage" in
            "$output/lib/gcc/$target/$gcc_version.wch-stage"|\
            "$output/$target/include.wch-stage"|\
            "$output/$target/lib.wch-stage")
                rm -rf -- "$stage"
                ;;
        esac
    done
}
trap cleanup EXIT

# --- 构建前校验：源码树必须正是公开补丁系列（口径与 linux 脚本一致） ---
gcc_base=5115c7e447fc07457443df874bf57840e8316d5f
binutils_base=2bc7af1ff7732451b6a7b09462a815c3284f9613
gcc_frozen_patch_tree=5bb6a45665c03f5f67eee83f7a7598d135a679e1
binutils_frozen_patch_tree=1321f9e24fd6843db33411451b0d382260f20cb0
patch_root="$repo_root/patches/$gcc_version"

git_at() {
    local source_tree=$1
    shift
    git -c safe.directory="$source_tree" -C "$source_tree" "$@"
}

verify_patch_series() {
    local component=$1 source_tree=$2 base=$3 expected_count=$4 frozen_tree=$5
    local series_file="$patch_root/$component/series"
    local index patch_name patch_path expected_id actual_id count tree_id

    [ -f "$series_file" ] || die "missing $component patch series"
    index=$(mktemp "$repo_root/tmp/.openwch-darwin-index.XXXXXX"); rm -f -- "$index"
    GIT_INDEX_FILE="$index" git_at "$source_tree" read-tree "$base"
    count=0
    while IFS= read -r patch_name || [ -n "$patch_name" ]; do
        [ -n "$patch_name" ] || die "blank entry in patch series: $series_file"
        case "$patch_name" in
            */*|.*) die "unsafe patch-series entry: $patch_name" ;;
        esac
        patch_path="$patch_root/$component/$patch_name"
        [ -f "$patch_path" ] || die "missing patch: $patch_path"
        expected_id=$(awk -F '\t' -v c="$component" -v p="$patch_name" \
            '$1 == c && $2 == p { print $3 }' "$patch_root/patch-id.tsv")
        [ -n "$expected_id" ] || die "stable patch ID missing for $component/$patch_name"
        actual_id=$(git_at "$source_tree" patch-id --stable < "$patch_path" | awk '{print $1}')
        [ "$actual_id" = "$expected_id" ] || \
            die "stable patch ID mismatch for $component/$patch_name"
        GIT_INDEX_FILE="$index" git_at "$source_tree" apply --cached --check "$patch_path"
        GIT_INDEX_FILE="$index" git_at "$source_tree" apply --cached "$patch_path"
        count=$((count + 1))
    done < "$series_file"
    [ "$count" -eq "$expected_count" ] || \
        die "$component series has $count patches; expected $expected_count"
    tree_id=$(GIT_INDEX_FILE="$index" git_at "$source_tree" write-tree)
    rm -f -- "$index"
    [ "$tree_id" = "$frozen_tree" ] || \
        die "$component public patch series does not produce the frozen patch tree"
    printf 'patch_series=PASS component=%s patches=%s tree=%s\n' \
        "$component" "$count" "$tree_id"
}

if [ "${SKIP_PATCH_VERIFY:-0}" != 1 ]; then
    [ -f "$patch_root/patch-id.tsv" ] || die "missing stable patch-ID ledger"
    head -1 "$patch_root/patch-id.tsv" | grep -q 'source_commit' || \
        die "patch-id.tsv is not the four-column ledger this script expects"
    verify_patch_series gcc "$gcc_source" "$gcc_base" 9 "$gcc_frozen_patch_tree"
    verify_patch_series binutils "$binutils_source" "$binutils_base" 7 \
        "$binutils_frozen_patch_tree"
fi

safe_remove_build_path "$build_gcc"
safe_remove_build_path "$build_binutils"
safe_remove_build_path "$output"
safe_remove_build_path "$logs"
mkdir -p "$build_gcc" "$build_binutils" "$output" "$logs"
export PATH="$literal_tree/output/bin:$PATH"

# ZSTD_CFLAGS/ZSTD_LIBS and the mmap cache override have to stay exported
# across make as well as configure, because the per-directory configures that
# actually run AC_ZSTD and AC_FUNC_MMAP are started by the top-level Makefile.
# They stay scoped to binutils: GCC must keep configuring exactly as before,
# apart from the assembler compressed-debug probe.
(
    export ZSTD_CFLAGS="$zstd_cflags"
    export ZSTD_LIBS="$zstd_libs"
    export "$mmap_cache_override"
    cd -L "$literal_tree/build-binutils"
    "$literal_tree/binutils/configure" \
        --target="$target" \
        --prefix="$literal_tree/output" \
        --disable-nls \
        --disable-werror \
        --disable-gdb \
        --disable-gdbserver \
        --disable-sim \
        --disable-gprofng \
        --with-isa-spec=2.2 \
        --with-system-zlib \
        --with-zstd \
        > "$logs/binutils-configure.log" 2>&1
    make -j"$build_jobs" > "$logs/binutils-build.log" 2>&1
    make install > "$logs/binutils-install.log" 2>&1
)

for component in bfd gas ld binutils; do
    grep -q '^#define HAVE_ZSTD 1$' "$build_binutils/$component/config.h" || \
        die "binutils $component was configured without zstd"
done
for component in bfd binutils ld; do
    grep -q '^#define HAVE_MMAP 1$' "$build_binutils/$component/config.h" || \
        die "binutils $component was configured without mmap"
done
grep -q -- "-lzstd" "$build_binutils/bfd/libbfd.la" || \
    die "libbfd.la does not record zstd in its dependency_libs"

# Ship the official libzstd next to the programs that load it.  The two copies
# differ in their trailing signature blob only; each location gets its own.
official_zstd_bin="$official_root/bin/libzstd.1.dylib"
official_zstd_target="$official_root/$target/bin/libzstd.1.dylib"
[ -f "$official_zstd_bin" ] || die "missing official libzstd: $official_zstd_bin"
[ -f "$official_zstd_target" ] || die "missing official libzstd: $official_zstd_target"
/bin/cp -c "$official_zstd_bin" "$output/bin/libzstd.1.dylib"
/bin/cp -c "$official_zstd_target" "$output/$target/bin/libzstd.1.dylib"
chmod 0755 "$output/bin/libzstd.1.dylib" "$output/$target/bin/libzstd.1.dylib"
[ "$(shasum -a 256 "$output/bin/libzstd.1.dylib" | cut -d' ' -f1)" = "$zstd_bin_sha256" ] || \
    die "bin/libzstd.1.dylib is not the official copy for that location"
[ "$(shasum -a 256 "$output/$target/bin/libzstd.1.dylib" | cut -d' ' -f1)" = "$zstd_target_sha256" ] || \
    die "$target/bin/libzstd.1.dylib is not the official copy for that location"

retarget_zstd_load_command() {
    local directory=$1
    local keep=$2
    local program
    while IFS= read -r program; do
        case "${program##*/}" in
            libzstd.1.dylib) continue ;;
            "$keep") continue ;;
        esac
        otool -L "$program" | grep -Fq "$zstd_install_name" || continue
        install_name_tool -change "$zstd_install_name" "$zstd_loader_name" "$program"
    done < <(find "$directory" -type f -perm -111 -print | LC_ALL=C sort)
}
retarget_zstd_load_command "$output/bin" ''
retarget_zstd_load_command "$output/$target/bin" "$zstd_absolute_keep"

report_zstd_load_commands() {
    local directory=$1
    local program
    while IFS= read -r program; do
        case "${program##*/}" in
            libzstd.1.dylib) continue ;;
        esac
        otool -L "$program" | \
            awk -v name="${program##*/}" '$1 ~ /libzstd\.1\.dylib$/ {print name"\t"$1}'
    done < <(find "$directory" -type f -perm -111 -print | LC_ALL=C sort)
}
report_zstd_load_commands "$output/bin" > "$logs/zstd-linkage-bin.tsv"
report_zstd_load_commands "$output/$target/bin" > "$logs/zstd-linkage-target.tsv"

observed=$(awk -F'\t' -v prefix="$target-" \
    '$2 == "@loader_path/libzstd.1.dylib" {sub("^"prefix, "", $1); print $1}' \
    "$logs/zstd-linkage-bin.tsv" | LC_ALL=C sort | tr '\n' ' ')
expected=$(printf '%s\n' $zstd_expected_loader_relative | LC_ALL=C sort | tr '\n' ' ')
[ "$observed" = "$expected" ] || \
    die "bin/ zstd load commands differ from the official set: [$observed] != [$expected]"
observed=$(awk -F'\t' '$2 == "@loader_path/libzstd.1.dylib" {print $1}' \
    "$logs/zstd-linkage-target.tsv" | LC_ALL=C sort | tr '\n' ' ')
expected=$(printf '%s\n' $zstd_expected_target_loader_relative | LC_ALL=C sort | tr '\n' ' ')
[ "$observed" = "$expected" ] || \
    die "$target/bin zstd load commands differ from the official set: [$observed] != [$expected]"
observed=$(awk -F'\t' -v want="$zstd_install_name" \
    '$2 == want {print $1}' "$logs/zstd-linkage-target.tsv" | LC_ALL=C sort | tr '\n' ' ')
[ "$observed" = "$zstd_absolute_keep " ] || \
    die "$target/bin absolute zstd load commands differ from the official set: [$observed]"

# Capture the authoritative argv from the official binary on every run.  The
# Python stdlib shlex parser preserves quoted arguments and their internal,
# intentionally irregular spaces before directly executing configure.
(
    cd -L "$literal_tree/build-gcc"
    python3 - "$official_gcc" "$logs/wch-gcc-v.txt" "$logs/gcc-configure-argv.json" <<'PY'
import json
import pathlib
import shlex
import subprocess
import sys

official, version_log, argv_log = sys.argv[1:]
probe = subprocess.run(
    [official, "-v"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    check=True,
)
pathlib.Path(version_log).write_text(probe.stdout)
lines = [line for line in probe.stdout.splitlines() if line.startswith("Configured with: ")]
if len(lines) != 1:
    raise SystemExit(f"expected one Configured with line, found {len(lines)}")
argv = shlex.split(lines[0][len("Configured with: "):], posix=True)
expected = "/Users/mrs/riscv-gnu-toolchain/gcc/configure"
if not argv or argv[0] != expected:
    raise SystemExit(f"unexpected configure path: {argv[0] if argv else '<empty>'}")
pathlib.Path(argv_log).write_text(json.dumps(argv, ensure_ascii=False, indent=2) + "\n")
subprocess.run(argv, check=True)
PY
) > "$logs/gcc-configure.log" 2>&1

# GCC 15.2.0 bundles zlib 1.2.11 because the authoritative configure argv says
# --without-system-zlib.  Current Apple Clang predefines TARGET_OS_MAC, which
# makes that old zlib select a classic-Mac fdopen shim and fail against modern
# stdio.h.  Undefine it only for the host zlib sub-build; __APPLE__ remains set,
# source/configure argv stay untouched, and no target library is built.
(
    cd -L "$literal_tree/build-gcc"
    make configure-zlib
) > "$logs/gcc-configure-zlib.log" 2>&1
(
    cd -L "$literal_tree/build-gcc/zlib"
    make -j"$build_jobs" CPPFLAGS=-UTARGET_OS_MAC
) > "$logs/gcc-build-zlib.log" 2>&1

(
    cd -L "$literal_tree/build-gcc"
    make -j"$build_jobs" all-gcc
) > "$logs/gcc-all-gcc.log" 2>&1

# gcc_GAS_CHECK_FEATURE really runs the assembler for this one, so the value is
# 2 only when the binutils installed above accepted --compress-debug-sections
# with both zlib and zstd.  That in turn is what puts the %{gz=zstd:...} clause
# into *asm_options, matching the official driver specs.  auto-host.h is written
# by the gcc subdirectory's configure, which the top level runs from all-gcc.
grep -q '^#define HAVE_AS_COMPRESS_DEBUG 2$' "$build_gcc/gcc/auto-host.h" || \
    die "GCC did not detect an assembler with zstd compressed-debug support"
(
    cd -L "$literal_tree/build-gcc"
    make install-gcc
) > "$logs/gcc-install-gcc.log" 2>&1

replace_tree() {
    local source_tree=$1
    local destination=$2
    local stage=${destination}.wch-stage
    case "$destination" in
        "$output/lib/gcc/$target/$gcc_version"|"$output/$target/include"|"$output/$target/lib") ;;
        *) die "refusing to inject into unexpected path: $destination" ;;
    esac
    [ -d "$source_tree" ] || die "missing injection source: $source_tree"
    mkdir -p "$(dirname -- "$destination")"
    injection_stages+=("$stage")
    rm -rf -- "$stage"
    mkdir -p "$stage"
    /bin/cp -cR "$source_tree/." "$stage/"
    diff -qr "$source_tree" "$stage" > "$logs/injection-stage-$(basename "$destination").diff" || \
        die "staged injection differs for $destination"
    rm -rf -- "$destination"
    mv "$stage" "$destination"
    diff -qr "$source_tree" "$destination" > "$logs/injection-final-$(basename "$destination").diff" || \
        die "installed injection differs for $destination"
}

replace_tree \
    "$official_root/lib/gcc/$target/$gcc_version" \
    "$output/lib/gcc/$target/$gcc_version"
replace_tree \
    "$official_root/$target/include" \
    "$output/$target/include"
replace_tree \
    "$official_root/$target/lib" \
    "$output/$target/lib"

[ -x "$output/bin/$target-gcc" ] || die "installed GCC driver is missing"
[ -x "$output/bin/$target-as" ] || die "installed assembler is missing"
[ -x "$output/bin/$target-ld" ] || die "installed linker is missing"
[ -x "$output/libexec/gcc/$target/$gcc_version/cc1" ] || die "installed cc1 is missing"

printf 'toolchain_root=%s\n' "$expected_tree"
printf 'gcc_head=%s\n' "$gcc_head"
printf 'binutils_head=%s\n' "$binutils_head"
printf 'SOURCE_DATE_EPOCH=%s\n' "$SOURCE_DATE_EPOCH"
printf 'build_jobs=%s\n' "$build_jobs"
printf 'zstd_cflags=%s\n' "$zstd_cflags"
printf 'zstd_libs=%s\n' "$zstd_libs"
printf 'mmap_cache_override=%s\n' "$mmap_cache_override"
printf 'install_files=%s\n' "$(find "$output" -type f | wc -l | tr -d '[:space:]')"
du -sh "$output"
printf 'compiler=%s\n' "$output/bin/$target-gcc"
