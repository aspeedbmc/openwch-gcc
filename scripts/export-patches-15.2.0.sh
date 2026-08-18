#!/usr/bin/env bash
# Export the final phase-8 (P8-R) GCC/binutils histories for 15.2.0 as
# replayable zero-commit patch series.  Source histories are never changed.
#
# Usage:
#   scripts/export-patches-15.2.0.sh              # export and install into patches/15.2.0
#   scripts/export-patches-15.2.0.sh --dry-run    # export to a scratch dir and diff
#                                                 # against patches/15.2.0; installs nothing
#
# What it guarantees before anything is installed:
#   * both source trees are clean and sit at the pinned HEAD/tree;
#   * the exported series replays sequentially onto the release base and
#     reproduces the pinned tree;
#   * patch-id.tsv is regenerated in the four-column form (component, patch,
#     stable_patch_id, source_commit) that closure 7-2 settled on, with the
#     source_commit taken from each patch's real `From` sha and double-checked:
#     40 hex digits, and reachable from that component's HEAD.
# Any mismatch dies before the patch directory is touched.
#
# --dry-run is the standing self-proof: on an unchanged tree the export must be
# byte-identical to what is already committed, so `diff -r` prints nothing.

set -euo pipefail
umask 022

export LC_ALL=C
export TZ=UTC

die() {
    printf 'export-patches-15.2.0.sh: %s\n' "$*" >&2
    exit 2
}

dry_run=0
case "${1:-}" in
    "") ;;
    --dry-run) dry_run=1 ;;
    *) printf 'usage: %s [--dry-run]\n' "${0##*/}" >&2; exit 2 ;;
esac

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd -P)
tree_root="$repo_root/tmp/toolchain_15.2.0/riscv-gnu-toolchain"
gcc_source="$tree_root/gcc"
binutils_source="$tree_root/binutils"
patch_root="$repo_root/patches/15.2.0"

# Pinned phase-8 (P8-R) end state.  Update these together with the series.
gcc_base=5115c7e447fc07457443df874bf57840e8316d5f
gcc_head=d14602eb4df12e4660c69d88f389cce509bf7f56
gcc_tree=5bb6a45665c03f5f67eee83f7a7598d135a679e1
binutils_base=2bc7af1ff7732451b6a7b09462a815c3284f9613
binutils_head=eb8e4dc9011fe80e2226faa6f396c71743689ae3
binutils_tree=1321f9e24fd6843db33411451b0d382260f20cb0
# The series carries the mail signature the committed patches were exported
# with; changing it would rewrite all sixteen files.
signature=2.55.0

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
    [ "$(git -C "$source" rev-list --count "$base..HEAD")" = "$expected_count" ] || \
        die "$component commit count changed"
done

stage=$(mktemp -d "$repo_root/tmp/phase8-patch-export.XXXXXX")
cleanup() { [ "$dry_run" = 1 ] || rm -rf -- "$stage"; }
trap cleanup EXIT INT TERM

export_component() {
    local component=$1 source=$2 base=$3 expected_count=$4 expected_tree=$5
    local output="$stage/$component" check="$stage/check-$component" patch replay_tree
    mkdir "$output"
    git -C "$source" format-patch --quiet --signature="$signature" \
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
    mkdir -p "$stage/compare"
    for component in gcc binutils; do
        /bin/cp "$stage/$component"/*.patch "$stage/$component/series" \
            "$stage/compare/" 2>/dev/null || true
    done
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
