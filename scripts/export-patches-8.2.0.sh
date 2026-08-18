#!/usr/bin/env bash
# Export the final Phase 6 / Phase 8 GCC 8.2.0 and binutils 2.32 histories as a
# replayable zero-commit patch series.  Source histories are never changed.
#
# Usage:
#   scripts/export-patches-8.2.0.sh              write patches/8.2.0/ in place
#   scripts/export-patches-8.2.0.sh --dry-run    export to a scratch stage and
#                                                diff it against patches/8.2.0/
#                                                byte for byte; write nothing
#
# Layout notes specific to 8.2.0 (it differs from 12.2.0 and 15.2.0):
#   * ONE top-level series file, patches/8.2.0/series, whose entries carry the
#     destination directory as a path prefix and stay in source-stack order.
#   * The GCC tree contributes one five-commit stack.  Its host-adaptation
#     commit is filed under host/ instead of gcc/ so the behaviour surface under
#     audit is exactly the patches that move artifact bytes; that leaves a
#     visible gap at 0002 in gcc/.  The commit is selected by its subject
#     prefix "host:", not by stack position.
#   * Every exported mail gets a unified From: identity; the mbox "From <sha>"
#     line still carries the real source commit, which patch-id.tsv records and
#     build-toolchain-8.2.0.sh re-checks at build time.

set -euo pipefail
umask 022

export LC_ALL=C
export TZ=UTC

die() {
    printf 'export-patches-8.2.0.sh: %s\n' "$*" >&2
    exit 2
}

dry_run=0
case "${1-}" in
    --dry-run) dry_run=1 ;;
    "") ;;
    *) die "unknown argument: $1 (use --dry-run or no argument)" ;;
esac

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd -P)
sources="$repo_root/tmp/toolchain_8.2.0/work/darwin-x64/sources"
gcc_source="$sources/riscv-gcc-10.2.0-1.1"
binutils_source="$sources/riscv-binutils-2.32"
patch_root="$repo_root/patches/8.2.0"

# Verified fork tag v8.2.0-3.1 (xpack-dev-tools) and the phase-8 final trees.
gcc_base=0c7a874f0b6f452eeafde57731646e5f460187e4
gcc_head=02be7a6dd317eebe55c172d72ce6ad5c9da6dc1e
gcc_tree=97b81fa8f52fa7037045f428f41e37099ba16fdf
binutils_base=82b51c7b5087ddb77988287cd7a2dd8921331bfd
binutils_head=8a0da1b4237cbcfd46a64c9b8127b8745193bbb0
binutils_tree=8d0d7da3c3b3376d07ef0f76f0f00b6b913dcf40
gcc_count=5
binutils_count=2
unified_from='From: OpenWCH Phase 6 <phase6@openwch.local>'

for spec in \
    "gcc:$gcc_source:$gcc_base:$gcc_head:$gcc_tree:$gcc_count" \
    "binutils:$binutils_source:$binutils_base:$binutils_head:$binutils_tree:$binutils_count"; do
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
cleanup() { rm -rf -- "$stage"; }
trap cleanup EXIT INT TERM

# ---- export one component, unify From:, replay-check the result -------------
export_component() {
    local component=$1 source=$2 base=$3 expected_count=$4 expected_tree=$5
    local output="$stage/$component" check="$stage/check-$component"
    local patch replay_tree count
    mkdir -p "$output"
    # No --no-signature here: unlike 12.2.0/15.2.0, the delivered 8.2.0 mails
    # carry git's default "-- \n<version>" trailer, so suppressing it would not
    # reproduce them.  The trailer therefore pins the exporting git version.
    git -C "$source" format-patch --quiet \
        --output-directory "$output" "$base..HEAD"
    find "$output" -mindepth 1 -maxdepth 1 -type f -name '*.patch' \
        -exec basename {} \; | LC_ALL=C sort > "$output/order"
    count=$(wc -l < "$output/order" | tr -d '[:space:]')
    [ "$count" = "$expected_count" ] || die "$component export count mismatch: $count"
    while IFS= read -r patch; do
        [ "$(awk 'NR == 2 && $1 == "From:"' "$output/$patch" | wc -l | tr -d ' ')" = 1 ] || \
            die "unexpected mail layout, no From: on line 2: $component/$patch"
        awk -v f="$unified_from" 'NR == 2 { print f; next } { print }' \
            "$output/$patch" > "$output/$patch.tmp"
        mv -- "$output/$patch.tmp" "$output/$patch"
    done < "$output/order"
    git clone --quiet --shared --no-checkout "$source" "$check"
    git -C "$check" checkout --quiet "$base"
    while IFS= read -r patch; do
        git -C "$check" apply --check "$output/$patch"
        git -C "$check" apply --index "$output/$patch"
    done < "$output/order"
    replay_tree=$(git -C "$check" write-tree)
    [ "$replay_tree" = "$expected_tree" ] || \
        die "$component sequential replay tree mismatch: $replay_tree"
}

export_component gcc "$gcc_source" "$gcc_base" "$gcc_count" "$gcc_tree"
export_component binutils "$binutils_source" "$binutils_base" "$binutils_count" "$binutils_tree"

# ---- file each mail under gcc/, host/ or binutils/, in stack order ----------
mkdir -p "$stage/out/gcc" "$stage/out/host" "$stage/out/binutils"
: > "$stage/out/series"
host_seen=0
while IFS= read -r patch; do
    subject=$(awk '/^Subject: /{sub(/^Subject: (\[PATCH[^]]*\] )?/, ""); print; exit}' \
        "$stage/gcc/$patch")
    case "$subject" in
        host:*) dir=host; host_seen=$((host_seen + 1)) ;;
        *)      dir=gcc ;;
    esac
    /bin/cp -c "$stage/gcc/$patch" "$stage/out/$dir/$patch"
    printf '%s/%s\n' "$dir" "$patch" >> "$stage/out/series"
done < "$stage/gcc/order"
[ "$host_seen" = 1 ] || die "expected exactly one host: commit in the GCC stack, found $host_seen"
while IFS= read -r patch; do
    /bin/cp -c "$stage/binutils/$patch" "$stage/out/binutils/$patch"
    printf 'binutils/%s\n' "$patch" >> "$stage/out/series"
done < "$stage/binutils/order"

# ---- ledger: component is the destination directory, patch is the basename --
printf 'component\tpatch\tstable_patch_id\tsource_commit\n' > "$stage/out/patch-id.tsv"
while IFS= read -r entry; do
    component=${entry%%/*}
    patch=${entry#*/}
    source=$gcc_source
    [ "$component" = binutils ] && source=$binutils_source
    patch_id=$(git patch-id --stable < "$stage/out/$entry" | awk 'NR == 1 {print $1}')
    [ -n "$patch_id" ] || die "could not compute patch id: $entry"
    source_commit=$(awk 'NR == 1 && $1 == "From" { print $2; exit }' "$stage/out/$entry")
    case "$source_commit" in
        *[!0-9a-f]* | "") die "unreadable From line: $entry" ;;
    esac
    [ "${#source_commit}" = 40 ] || die "short From sha: $entry"
    git -C "$source" merge-base --is-ancestor "$source_commit" HEAD || \
        die "From sha not reachable from HEAD: $entry"
    printf '%s\t%s\t%s\t%s\n' "$component" "$patch" "$patch_id" "$source_commit" \
        >> "$stage/out/patch-id.tsv"
done < "$stage/out/series"

# ---- publish, or (dry run) diff the stage against the delivered tree --------
if [ "$dry_run" = 1 ]; then
    differences=0
    while IFS= read -r entry; do
        if ! cmp -s "$stage/out/$entry" "$patch_root/$entry"; then
            printf 'DIFF %s\n' "$entry"; differences=$((differences + 1))
        fi
    done < "$stage/out/series"
    for meta in series patch-id.tsv; do
        if ! cmp -s "$stage/out/$meta" "$patch_root/$meta"; then
            printf 'DIFF %s\n' "$meta"; differences=$((differences + 1))
        fi
    done
    # Anything present on disk but not re-exported is a leftover.
    while IFS= read -r existing; do
        grep -qxF "$existing" "$stage/out/series" || {
            printf 'EXTRA %s\n' "$existing"; differences=$((differences + 1)); }
    done < <(cd "$patch_root" && find gcc host binutils -type f -name '*.patch' | LC_ALL=C sort)
    printf 'dry_run_differences=%s\n' "$differences"
    [ "$differences" = 0 ] || die "dry run does not reproduce patches/8.2.0 byte for byte"
    printf 'dry_run=PASS files=%s\n' "$(( $(wc -l < "$stage/out/series" | tr -d ' ') + 2 ))"
    exit 0
fi

for dir in gcc host binutils; do
    mkdir -p "$patch_root/$dir"
    find "$patch_root/$dir" -mindepth 1 -maxdepth 1 -type f -name '*.patch' -delete
    /bin/cp -c "$stage/out/$dir"/*.patch "$patch_root/$dir/"
done
/bin/cp -c "$stage/out/series" "$patch_root/series"
/bin/cp -c "$stage/out/patch-id.tsv" "$patch_root/patch-id.tsv"

printf 'gcc_patches=%s\n' "$gcc_count"
printf 'binutils_patches=%s\n' "$binutils_count"
printf 'patch_id_rows=%s\n' "$((gcc_count + binutils_count))"
printf 'gcc_head=%s\n' "$gcc_head"
printf 'gcc_tree=%s\n' "$gcc_tree"
printf 'binutils_head=%s\n' "$binutils_head"
printf 'binutils_tree=%s\n' "$binutils_tree"
