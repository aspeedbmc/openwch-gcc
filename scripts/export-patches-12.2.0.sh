#!/usr/bin/env bash
# Export the final GCC/binutils histories as replayable patch series.  Source
# histories are never changed by this script.
#
# Usage:
#   scripts/export-patches-12.2.0.sh              # export and install into patches/12.2.0
#   scripts/export-patches-12.2.0.sh --dry-run    # export to a scratch dir and diff
#                                                 # against patches/12.2.0; installs nothing
#
# --dry-run is the standing self-proof: on an unchanged tree the export must be
# byte-identical to what is already committed, so `diff -r` prints nothing.

set -euo pipefail
umask 022

export LC_ALL=C
export TZ=UTC

die() {
    printf 'export-patches-12.2.0.sh: %s\n' "$*" >&2
    exit 2
}

dry_run=0
case "${1:-}" in
    "") ;;
    --dry-run) dry_run=1 ;;
    *) printf 'usage: %s [--dry-run]\n' "${0##*/}" >&2; exit 2 ;;
esac
[ "$#" -le 1 ] || { printf 'usage: %s [--dry-run]\n' "${0##*/}" >&2; exit 2; }

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd -P)
project="$repo_root/tmp/toolchain_12.2.0/riscv-none-elf-gcc-xpack.git"
sources="$project/build/darwin-arm64/sources"
gcc_source="$sources/gcc-12.2.0"
binutils_source="$sources/binutils-2.38"
patch_root="$repo_root/patches/12.2.0"

gcc_base=3280576e992d8fcd57fabd4bb85944fcf2bfaddb
gcc_head=9731e5ee701047373429a191b45a6f07f3e149a7
gcc_tree=af74531c952c78bab9089ee93af50e3a7fe992ea
binutils_base=dc5b5e8935f95730fcd9ac603627d834d52fef64
binutils_head=c397a553b1ab0bb3a7063077a825da74dd34519a
binutils_tree=0d01a497ae860ce540c463320ce0a4436e880a05

for spec in \
    "gcc:$gcc_source:$gcc_base:$gcc_head:$gcc_tree:9" \
    "binutils:$binutils_source:$binutils_base:$binutils_head:$binutils_tree:7"; do
    component=${spec%%:*}; rest=${spec#*:}
    source=${rest%%:*}; rest=${rest#*:}
    base=${rest%%:*}; rest=${rest#*:}
    expected_head=${rest%%:*}; rest=${rest#*:}
    expected_tree=${rest%%:*}; expected_count=${rest##*:}
    [ -d "$source/.git" ] || die "missing source Git tree: $source"
    [ -z "$(git -C "$source" status --porcelain=v1)" ] || die "$component source is dirty"
    [ "$(git -C "$source" rev-parse HEAD)" = "$expected_head" ] || die "$component HEAD changed"
    [ "$(git -C "$source" rev-parse 'HEAD^{tree}')" = "$expected_tree" ] || die "$component tree changed"
    [ "$(git -C "$source" rev-list --count "$base..HEAD")" = "$expected_count" ] || die "$component commit count changed"
done

stage=$(mktemp -d "$repo_root/tmp/phase4-patch-export.XXXXXX")
cleanup() { rm -rf -- "$stage"; }
trap cleanup EXIT INT TERM

export_component() {
    local component=$1 source=$2 base=$3 expected_count=$4 expected_tree=$5
    local output="$stage/$component" check="$stage/check-$component" patch replay_tree
    mkdir "$output"
    git -C "$source" format-patch --quiet --no-signature \
        --output-directory "$output" "$base..HEAD"
    find "$output" -mindepth 1 -maxdepth 1 -type f -name '*.patch' \
        -exec basename {} \; | LC_ALL=C sort > "$output/series"
    [ "$(wc -l < "$output/series" | tr -d '[:space:]')" = "$expected_count" ] || \
        die "$component export count mismatch"
    git clone --quiet --shared --no-checkout "$source" "$check"
    git -C "$check" checkout --quiet "$base"
    while IFS= read -r patch; do
        git -C "$check" apply --check "$output/$patch"
        git -C "$check" apply --index "$output/$patch"
    done < "$output/series"
    replay_tree=$(git -C "$check" write-tree)
    [ "$replay_tree" = "$expected_tree" ] || \
        die "$component sequential replay tree mismatch: $replay_tree"
}

export_component gcc "$gcc_source" "$gcc_base" 9 "$gcc_tree"
export_component binutils "$binutils_source" "$binutils_base" 7 "$binutils_tree"

printf 'component\tpatch\tstable_patch_id\tsource_commit\n' > "$stage/patch-id.tsv"
for component in gcc binutils; do
    source=$binutils_source
    [ "$component" = gcc ] && source=$gcc_source
    while IFS= read -r patch; do
        patch_id=$(git patch-id --stable < "$stage/$component/$patch" | awk 'NR == 1 {print $1}')
        [ -n "$patch_id" ] || die "could not compute patch id: $component/$patch"
        source_commit=$(awk 'NR == 1 && $1 == "From" { print $2; exit }' \
            "$stage/$component/$patch")
        case "$source_commit" in
            [0-9a-f]) die "unreadable From line: $component/$patch" ;;
            *[!0-9a-f]* | "") die "unreadable From line: $component/$patch" ;;
        esac
        [ "${#source_commit}" = 40 ] || die "short From sha: $component/$patch"
        git -C "$source" merge-base --is-ancestor "$source_commit" HEAD || \
            die "From sha not reachable from HEAD: $component/$patch"
        printf '%s\t%s\t%s\t%s\n' "$component" "$patch" "$patch_id" "$source_commit" \
            >> "$stage/patch-id.tsv"
    done < "$stage/$component/series"
done

if [ "$dry_run" = 1 ]; then
    status=0
    for component in gcc binutils; do
        diff -r "$patch_root/$component" "$stage/$component" \
            --exclude='.*' > "$stage/diff-$component.txt" 2>&1 || status=1
    done
    diff "$patch_root/patch-id.tsv" "$stage/patch-id.tsv" \
        > "$stage/diff-patch-id.txt" 2>&1 || status=1
    printf 'dry_run_stage=%s\n' "$stage"
    for f in "$stage"/diff-*.txt; do
        if [ -s "$f" ]; then
            printf 'DIFF %s:\n' "${f##*/}"; sed -n '1,20p' "$f"
        else
            printf 'EMPTY %s\n' "${f##*/}"
        fi
    done
    [ "$status" = 0 ] || die "dry run differs from the committed series"
    printf 'DRY-RUN-IDENTICAL gcc=9 binutils=7 patch_id_rows=16\n'
    exit 0
fi

for component in gcc binutils; do
    mkdir -p "$patch_root/$component"
    find "$patch_root/$component" -mindepth 1 -maxdepth 1 -type f \
        \( -name '*.patch' -o -name series \) -delete
    /bin/cp -c "$stage/$component"/*.patch "$patch_root/$component/"
    /bin/cp -c "$stage/$component/series" "$patch_root/$component/series"
done
/bin/cp -c "$stage/patch-id.tsv" "$patch_root/patch-id.tsv"

printf 'gcc_patches=9\n'
printf 'binutils_patches=7\n'
printf 'patch_id_rows=16\n'
printf 'gcc_head=%s\n' "$gcc_head"
printf 'gcc_tree=%s\n' "$gcc_tree"
printf 'binutils_head=%s\n' "$binutils_head"
printf 'binutils_tree=%s\n' "$binutils_tree"
