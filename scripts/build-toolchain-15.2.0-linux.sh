#!/usr/bin/env bash
# Build the patched GCC 15.2.0/binutils 2.45 compiler-only toolchain on
# linux/amd64, then inject the official Linux WCH target libraries verbatim.
#
# Usage:
#   scripts/build-toolchain-15.2.0-linux.sh \
#     [expected-riscv-gnu-toolchain-root]
#
# The caller must prepare a pristine upstream checkout and apply all sixteen
# patches in patches/15.2.0 before invoking this script.  Set BUILD_JOBS to
# override the default parallelism (8).

set -euo pipefail

export LC_ALL=C
export SOURCE_DATE_EPOCH=1767225600
unset CPPFLAGS CFLAGS CXXFLAGS LDFLAGS LIBRARY_PATH CPATH C_INCLUDE_PATH \
    CPLUS_INCLUDE_PATH GCC_EXEC_PREFIX COMPILER_PATH

die() {
    printf 'build-toolchain-15.2.0-linux.sh: %s\n' "$*" >&2
    exit 2
}

if [ "$#" -gt 1 ]; then
    printf 'usage: %s [expected-riscv-gnu-toolchain-root]\n' "${0##*/}" >&2
    exit 2
fi

[ "$(uname -s)" = Linux ] || die "this script is only for Linux containers"
[ "$(uname -m)" = x86_64 ] || die "this script requires linux/amd64 (uname -m must be x86_64)"
if [ ! -e /.dockerenv ] && [ ! -e /run/.containerenv ] && \
        [ -z "${container:-}" ]; then
    die "container marker not found; run this script inside the linux/amd64 build container"
fi

for command_name in awk bison cmp cp diff dirname find flex git grep make \
        makeinfo mkdir mktemp mv perl python3 readlink rm sed sha256sum tr uname \
        wc; do
    command -v "$command_name" >/dev/null 2>&1 || \
        die "required build command is unavailable: $command_name"
done
[ -x /usr/bin/gcc ] || die "required host compiler is unavailable: /usr/bin/gcc"
[ -x /usr/bin/g++ ] || die "required host compiler is unavailable: /usr/bin/g++"
case "$(/usr/bin/gcc --version | sed -n '1p')" in
    *[Cc]lang*) die "/usr/bin/gcc resolves to clang; a GNU/Linux GCC host compiler is required" ;;
esac
export CC=/usr/bin/gcc
export CXX=/usr/bin/g++

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd -P)
[ -f "$repo_root/AGENTS.md" ] || die "script is not running from an openwch repository"
[ -d "$repo_root/.git" ] || die "repository metadata is missing: $repo_root/.git"

default_tree="$repo_root/tmp/toolchain_15.2.0-linux/riscv-gnu-toolchain"
expected_argument=${1:-$default_tree}
[ -d "$expected_argument" ] || die "expected source tree does not exist: $expected_argument"
expected_tree=$(CDPATH= cd -- "$expected_argument" && pwd -P)
case "$expected_tree" in
    "$repo_root"/tmp/*) ;;
    *) die "expected source tree must be a child of $repo_root/tmp: $expected_tree" ;;
esac

literal_tree=/home/wch/riscv-gnu-toolchain
[ -L "$literal_tree" ] || die "required symlink is missing: $literal_tree"
literal_target=$(readlink -f -- "$literal_tree") || die "cannot resolve symlink: $literal_tree"
[ "$literal_target" = "$expected_tree" ] || \
    die "symlink target mismatch: expected $expected_tree, got $literal_target"

gcc_source="$expected_tree/gcc"
binutils_source="$expected_tree/binutils"
build_gcc="$expected_tree/build-gcc"
build_binutils="$expected_tree/build-binutils"
output="$expected_tree/output"
logs="$expected_tree/logs"
official_root="$repo_root/ref/gcc/linux-amd64/15.2.0"
official_gcc="$official_root/bin/riscv32-wch-elf-gcc"
patch_root="$repo_root/patches/15.2.0"
target=riscv32-wch-elf
gcc_version=15.2.0
gcc_base=5115c7e447fc07457443df874bf57840e8316d5f
binutils_base=2bc7af1ff7732451b6a7b09462a815c3284f9613
gcc_frozen_patch_tree=5bb6a45665c03f5f67eee83f7a7598d135a679e1
binutils_frozen_patch_tree=1321f9e24fd6843db33411451b0d382260f20cb0
build_jobs=${BUILD_JOBS:-8}

# The official multilib table contains XW candidates that temporary xgcc must
# parse while all-gcc is being built.  Selecting a canonical non-XW multilib
# for those build-only probes avoids walking the complete table.  TFLAGS does
# not alter configure argv or the installed driver's multilib table.
gcc_build_tflags='-march=rv32imac_zaamo_zalrsc -mabi=ilp32'

case "$build_jobs" in
    ''|*[!0-9]*) die "BUILD_JOBS must be a positive integer" ;;
    0) die "BUILD_JOBS must be greater than zero" ;;
esac
[ -d "$gcc_source/.git" ] || die "missing GCC checkout: $gcc_source"
[ -d "$binutils_source/.git" ] || die "missing binutils checkout: $binutils_source"
[ -x "$official_gcc" ] || die "missing executable Linux official GCC: $official_gcc"
[ -d "$official_root/lib/gcc/$target/$gcc_version" ] || die "missing official GCC library tree"
[ -d "$official_root/$target/include" ] || die "missing official target headers"
[ -d "$official_root/$target/lib" ] || die "missing official target library tree"
[ -f "$patch_root/gcc/series" ] || die "missing GCC patch series"
[ -f "$patch_root/binutils/series" ] || die "missing binutils patch series"
[ -f "$patch_root/patch-id.tsv" ] || die "missing stable patch-ID ledger"

# The ledger is part of the frozen public input.  Validate its shape before
# using it so duplicate keys, extra rows, or malformed IDs cannot make a
# mutually edited series/ledger pair appear authoritative.
awk -F '\t' '
    NR == 1 {
        # closure 7-2 起台账为四列（第四列 source_commit）。此处只校验前三列，
        # 第四列的取值与可达性由各版本导出脚本负责。
        if (NF != 4 || $1 != "component" || $2 != "patch" ||
            $3 != "stable_patch_id" || $4 != "source_commit")
            exit 1
        next
    }
    {
        if (NF != 4 || ($1 != "gcc" && $1 != "binutils") ||
            $2 == "" || $2 ~ /\// || $2 ~ /^\./ ||
            length($3) != 40 || $3 ~ /[^0-9a-f]/)
            exit 1
        key = $1 SUBSEP $2
        if (seen[key]++)
            exit 1
        count[$1]++
    }
    END {
        if (NR != 17 || count["gcc"] != 9 || count["binutils"] != 7)
            exit 1
    }
' "$patch_root/patch-id.tsv" || die "malformed stable patch-ID ledger"

for prerequisite in gmp mpfr mpc isl; do
    [ -e "$gcc_source/$prerequisite" ] || \
        die "missing in-tree GCC prerequisite: $prerequisite"
done

temporary_indexes=()
injection_stages=()

cleanup() {
    local path
    for path in "${temporary_indexes[@]}"; do
        case "$path" in
            "$repo_root"/tmp/.openwch-linux-index.*) rm -f -- "$path" ;;
        esac
    done
    for path in "${injection_stages[@]}"; do
        case "$path" in
            "$output/lib/gcc/$target/$gcc_version.wch-stage"|\
            "$output/$target/include.wch-stage"|\
            "$output/$target/lib.wch-stage")
                rm -rf -- "$path"
                ;;
        esac
    done
}
trap cleanup EXIT

git_at() {
    local source_tree=$1
    shift
    git -c safe.directory="$source_tree" -C "$source_tree" "$@"
}

# Verify the caller-applied worktree against the ordered public patch series.
# A private temporary index derives both trees from the release HEAD, so staged
# or unstaged patch changes are accepted while any extra tracked edit is not.
verified_patch_count=0
verified_patch_tree=
verify_patched_worktree() {
    local component=$1
    local source_tree=$2
    local expected_head=$3
    local expected_count=$4
    local frozen_patch_tree=$5
    local series_file="$patch_root/$component/series"
    local actual_head expected_index actual_index added_paths patch_name patch_path
    local expected_tree_id actual_tree_id patch_count expected_patch_id actual_patch_id

    actual_head=$(git_at "$source_tree" rev-parse HEAD)
    [ "$actual_head" = "$expected_head" ] || \
        die "unexpected $component HEAD: expected $expected_head, got $actual_head"

    expected_index=$(mktemp "$repo_root/tmp/.openwch-linux-index.XXXXXX")
    actual_index=$(mktemp "$repo_root/tmp/.openwch-linux-index.XXXXXX")
    added_paths=$(mktemp "$repo_root/tmp/.openwch-linux-index.XXXXXX")
    temporary_indexes+=("$expected_index" "$actual_index" "$added_paths")
    rm -f -- "$expected_index" "$actual_index"

    GIT_INDEX_FILE="$expected_index" git_at "$source_tree" read-tree "$expected_head"
    patch_count=0
    while IFS= read -r patch_name || [ -n "$patch_name" ]; do
        [ -n "$patch_name" ] || die "blank entry in patch series: $series_file"
        case "$patch_name" in
            */*|.*) die "unsafe patch-series entry: $patch_name" ;;
        esac
        patch_path="$patch_root/$component/$patch_name"
        [ -f "$patch_path" ] || die "missing patch: $patch_path"
        expected_patch_id=$(awk -F '\t' -v component="$component" -v patch="$patch_name" \
            '$1 == component && $2 == patch { print $3 }' "$patch_root/patch-id.tsv")
        [ -n "$expected_patch_id" ] || \
            die "stable patch ID is missing for $component/$patch_name"
        actual_patch_id=$(git_at "$source_tree" patch-id --stable < "$patch_path" | \
            awk '{print $1}')
        [ "$actual_patch_id" = "$expected_patch_id" ] || \
            die "stable patch ID mismatch for $component/$patch_name"
        printf 'patch_id=PASS component=%s patch=%s id=%s\n' \
            "$component" "$patch_name" "$actual_patch_id"
        GIT_INDEX_FILE="$expected_index" \
            git_at "$source_tree" apply --cached --check "$patch_path"
        GIT_INDEX_FILE="$expected_index" \
            git_at "$source_tree" apply --cached "$patch_path"
        patch_count=$((patch_count + 1))
    done < "$series_file"
    [ "$patch_count" -eq "$expected_count" ] || \
        die "$component series has $patch_count patches; expected $expected_count"
    expected_tree_id=$(GIT_INDEX_FILE="$expected_index" git_at "$source_tree" write-tree)
    [ "$expected_tree_id" = "$frozen_patch_tree" ] || \
        die "$component public patch series does not produce the frozen patch tree"

    GIT_INDEX_FILE="$actual_index" git_at "$source_tree" read-tree "$expected_head"
    GIT_INDEX_FILE="$actual_index" git_at "$source_tree" add -u -- .
    # git add -u deliberately omits files introduced by a patch.  Add only the
    # paths that the expected patched index classifies as new; unrelated
    # untracked prerequisite archives/directories remain outside the check.
    GIT_INDEX_FILE="$expected_index" git_at "$source_tree" \
        diff --cached --name-only --diff-filter=A -z "$expected_head" \
        > "$added_paths"
    if [ -s "$added_paths" ]; then
        GIT_INDEX_FILE="$actual_index" git_at "$source_tree" add \
            --pathspec-from-file="$added_paths" --pathspec-file-nul
    fi
    actual_tree_id=$(GIT_INDEX_FILE="$actual_index" git_at "$source_tree" write-tree)
    [ "$actual_tree_id" = "$expected_tree_id" ] || \
        die "$component tracked worktree is not exactly the ordered public patch series"

    rm -f -- "$expected_index" "$actual_index" "$added_paths"
    verified_patch_count=$patch_count
    verified_patch_tree=$actual_tree_id
}

verify_patched_worktree \
    gcc "$gcc_source" "$gcc_base" 9 "$gcc_frozen_patch_tree"
gcc_patch_count=$verified_patch_count
gcc_patch_tree=$verified_patch_tree
verify_patched_worktree \
    binutils "$binutils_source" "$binutils_base" 7 "$binutils_frozen_patch_tree"
binutils_patch_count=$verified_patch_count
binutils_patch_tree=$verified_patch_tree
[ $((gcc_patch_count + binutils_patch_count)) -eq 16 ] || \
    die "internal patch-count check failed"

safe_remove_build_path() {
    local path=$1
    case "$path" in
        "$build_gcc"|"$build_binutils"|"$output"|"$logs") ;;
        *) die "refusing to remove unexpected path: $path" ;;
    esac
    rm -rf -- "$path"
}

safe_remove_build_path "$build_gcc"
safe_remove_build_path "$build_binutils"
safe_remove_build_path "$output"
safe_remove_build_path "$logs"
mkdir -p "$build_gcc" "$build_binutils" "$output" "$logs"
export PATH="$literal_tree/output/bin:$PATH"

printf 'environment=linux/amd64-container\n'
printf 'toolchain_root=%s\n' "$expected_tree"
printf 'literal_root=%s\n' "$literal_tree"
printf 'logs=%s\n' "$logs"
printf 'patch_series=PASS gcc=%s binutils=%s total=%s\n' \
    "$gcc_patch_count" "$binutils_patch_count" \
    "$((gcc_patch_count + binutils_patch_count))"

printf 'stage=binutils-configure\n'
(
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
        --with-system-zlib
) > "$logs/binutils-configure.log" 2>&1

printf 'stage=binutils-build\n'
(
    cd -L "$literal_tree/build-binutils"
    make -j"$build_jobs"
) > "$logs/binutils-build.log" 2>&1
(
    cd -L "$literal_tree/build-binutils"
    make install
) > "$logs/binutils-install.log" 2>&1

# Extract the authoritative configure command from the Linux official binary
# on every invocation.  shlex removes only shell quoting; it preserves every
# argv byte inside quoted multilib and target-flag arguments.  The extracted
# argv is validated but never rewritten before it is executed.
printf 'stage=gcc-configure-from-official\n'
(
    cd -L "$literal_tree/build-gcc"
    python3 - "$official_gcc" "$logs/wch-gcc-v.txt" \
        "$logs/official-configured-with.txt" "$logs/gcc-configure-argv.json" <<'PY'
import json
import pathlib
import shlex
import subprocess
import sys

official, version_log, line_log, argv_log = sys.argv[1:]
probe = subprocess.run(
    [official, "-v"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    check=True,
)
pathlib.Path(version_log).write_text(probe.stdout, encoding="utf-8")
lines = [line for line in probe.stdout.splitlines()
         if line.startswith("Configured with: ")]
if len(lines) != 1:
    raise SystemExit(f"expected one Configured with line, found {len(lines)}")
line = lines[0]
pathlib.Path(line_log).write_text(line + "\n", encoding="utf-8")
argv = shlex.split(line[len("Configured with: "):], posix=True)
expected_program = "/home/wch/riscv-gnu-toolchain/gcc/configure"
required_arguments = {
    "--target=riscv32-wch-elf",
    "--prefix=/home/wch/riscv-gnu-toolchain/output",
    "--with-sysroot=/home/wch/riscv-gnu-toolchain/output/riscv32-wch-elf",
    "--with-isa-spec=2.2",
    "--with-pkgversion=g5115c7e44-dirty",
}
if not argv or argv[0] != expected_program:
    raise SystemExit(
        f"unexpected configure path: {argv[0] if argv else '<empty>'}")
missing = sorted(required_arguments.difference(argv))
if missing:
    raise SystemExit(f"required configure arguments missing: {missing}")
pathlib.Path(argv_log).write_text(
    json.dumps(argv, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
subprocess.run(argv, check=True)
PY
) > "$logs/gcc-configure.log" 2>&1

printf 'stage=gcc-compiler-only-build\n'
(
    cd -L "$literal_tree/build-gcc"
    make -j"$build_jobs" all-gcc TFLAGS="$gcc_build_tflags"
) > "$logs/gcc-all-gcc.log" 2>&1
(
    cd -L "$literal_tree/build-gcc"
    make install-gcc TFLAGS="$gcc_build_tflags"
) > "$logs/gcc-install-gcc.log" 2>&1

replace_tree() {
    local source_tree=$1
    local destination=$2
    local label=$3
    local stage=${destination}.wch-stage
    case "$destination" in
        "$output/lib/gcc/$target/$gcc_version"|\
        "$output/$target/include"|\
        "$output/$target/lib") ;;
        *) die "refusing to inject into unexpected path: $destination" ;;
    esac
    [ -d "$source_tree" ] || die "missing injection source: $source_tree"
    mkdir -p "$(dirname -- "$destination")"
    injection_stages+=("$stage")
    rm -rf -- "$stage"
    mkdir -p "$stage"
    cp -a -- "$source_tree/." "$stage/"
    diff -qr --no-dereference "$source_tree" "$stage" \
        > "$logs/injection-stage-$label.diff" || \
        die "staged injection differs for $destination"
    rm -rf -- "$destination"
    mv -- "$stage" "$destination"
    diff -qr --no-dereference "$source_tree" "$destination" \
        > "$logs/injection-final-$label.diff" || \
        die "installed injection differs for $destination"
}

printf 'stage=inject-linux-official-libraries\n'
replace_tree \
    "$official_root/lib/gcc/$target/$gcc_version" \
    "$output/lib/gcc/$target/$gcc_version" \
    gcc-runtime
replace_tree \
    "$official_root/$target/include" \
    "$output/$target/include" \
    target-include
replace_tree \
    "$official_root/$target/lib" \
    "$output/$target/lib" \
    target-lib

sample_log="$logs/injection-samples.tsv"
printf 'path\tofficial_sha256\tinstalled_sha256\tstatus\n' > "$sample_log"
injection_sample_count=0
for relative_path in \
        "lib/gcc/$target/$gcc_version/libgcc.a" \
        "lib/gcc/$target/$gcc_version/crtbegin.o" \
        "lib/gcc/$target/$gcc_version/include/stdint.h" \
        "$target/include/stdint.h" \
        "$target/lib/libc.a"; do
    official_file="$official_root/$relative_path"
    installed_file="$output/$relative_path"
    [ -f "$official_file" ] || die "missing injection sample source: $official_file"
    [ -f "$installed_file" ] || die "missing injection sample destination: $installed_file"
    official_hash=$(sha256sum -- "$official_file" | awk '{print $1}')
    installed_hash=$(sha256sum -- "$installed_file" | awk '{print $1}')
    [ "$official_hash" = "$installed_hash" ] || \
        die "injection sample SHA256 mismatch: $relative_path"
    printf '%s\t%s\t%s\tPASS\n' \
        "$relative_path" "$official_hash" "$installed_hash" >> "$sample_log"
    injection_sample_count=$((injection_sample_count + 1))
done
[ "$injection_sample_count" -ge 5 ] || die "fewer than five injection samples verified"

[ -x "$output/bin/$target-gcc" ] || die "installed GCC driver is missing"
[ -x "$output/bin/$target-as" ] || die "installed assembler is missing"
[ -x "$output/bin/$target-ld" ] || die "installed linker is missing"
[ -x "$output/libexec/gcc/$target/$gcc_version/cc1" ] || die "installed cc1 is missing"
[ -x "$output/libexec/gcc/$target/$gcc_version/cc1plus" ] || die "installed cc1plus is missing"

"$output/bin/$target-gcc" -v > "$logs/built-gcc-v.txt" 2>&1
awk '/^Configured with: / { print; count++ } END { if (count != 1) exit 1 }' \
    "$logs/built-gcc-v.txt" > "$logs/built-configured-with.txt" || \
    die "built GCC did not report exactly one Configured with line"
cmp -s "$logs/official-configured-with.txt" "$logs/built-configured-with.txt" || \
    die "built GCC Configured with line differs from the Linux official GCC"
configure_line_sha256=$(sha256sum -- "$logs/built-configured-with.txt" | awk '{print $1}')

"$output/bin/$target-gcc" -print-multi-lib > "$logs/built-multilib.txt"
multilib_count=$(awk 'NF { count++ } END { print count+0 }' "$logs/built-multilib.txt")
[ "$multilib_count" -eq 22 ] || die "built GCC reports $multilib_count multilib entries; expected 22"

"$output/bin/$target-ld" --verbose > "$logs/built-ld-verbose.txt"
search_dir='SEARCH_DIR("/home/wch/riscv-gnu-toolchain/output/riscv32-wch-elf/lib")'
grep -Fq "$search_dir" "$logs/built-ld-verbose.txt" || \
    die "built linker is missing the required /home/wch SEARCH_DIR"

install_file_count=$(find "$output" -type f | wc -l | tr -d '[:space:]')
injected_file_count=$(
    find \
        "$output/lib/gcc/$target/$gcc_version" \
        "$output/$target/include" \
        "$output/$target/lib" \
        -type f | wc -l | tr -d '[:space:]'
)

printf 'gcc_head=%s\n' "$gcc_base"
printf 'binutils_head=%s\n' "$binutils_base"
printf 'gcc_patch_tree=%s\n' "$gcc_patch_tree"
printf 'binutils_patch_tree=%s\n' "$binutils_patch_tree"
printf 'SOURCE_DATE_EPOCH=%s\n' "$SOURCE_DATE_EPOCH"
printf 'build_jobs=%s\n' "$build_jobs"
printf 'binutils_isa_spec=2.2\n'
printf 'gcc_build=compiler-only all-gcc+install-gcc\n'
printf 'configured_with=PASS sha256=%s\n' "$configure_line_sha256"
printf 'linux_library_injection=PASS trees=3 files=%s samples=%s sample_log=%s\n' \
    "$injected_file_count" "$injection_sample_count" "$sample_log"
printf 'search_dir=PASS path=/home/wch/riscv-gnu-toolchain/output/riscv32-wch-elf/lib\n'
printf 'multilib=PASS entries=%s\n' "$multilib_count"
printf 'install_files=%s\n' "$install_file_count"
printf 'compiler=%s\n' "$output/bin/$target-gcc"
