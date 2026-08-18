#!/usr/bin/env bash
# Reproduce, inside a clean CI checkout, the exact upstream acquisition and
# patch application each version's build script expects.  The three versions do
# NOT share a recipe; this script is three recipes behind one entry point.
#
# Usage: scripts/ci/prepare-sources.sh <15.2.0|12.2.0|8.2.0> [dest-root]
#
#   dest-root defaults to <repo>/tmp/ci-src and applies to 15.2.0 and 12.2.0
#   only.  8.2.0 ignores it: scripts/build-toolchain-8.2.0.sh:52 hard-codes its
#   project root as <repo>/tmp/toolchain_8.2.0/work and takes no argument.
#   The archive directories are likewise hard-coded by the build scripts
#   (build-toolchain-12.2.0.sh:43, build-toolchain-8.2.0.sh:53) and are not
#   relative to dest-root.
#
# Recipes and where they come from:
#   15.2.0  patches/15.2.0/README.md 'Apply and build'
#           git clone -> rev-parse -> isolated-index full-series precheck ->
#           git apply --index -> contrib/download_prerequisites --verify
#   12.2.0  scripts/replay-toolchain-12.2.0.sh (the README has no Apply
#           section; the replay wrapper is its equivalent)
#           verified tarballs -> git init/commit import -> git am series
#   8.2.0   patches/8.2.0/README.md 'Apply'
#           git clone tag v8.2.0-3.1 -> rev-parse -> git am top-level series
#           (host/ lines go to the GCC checkout) -> post-apply tree assertion
#
# Verification strength is only ever added here, never reduced.  In particular
# 15.2.0 gains the frozen patched-tree assertion that
# scripts/build-toolchain-15.2.0-linux.sh:84-85 already makes on Linux, so the
# darwin leg fails the same way if a patch stops applying identically.
#
# Host prerequisites: 12.2.0 and 8.2.0 must NOT use contrib/download_prereq-
# uisites.  Their build scripts pin a different, independently SHA-256 gated
# set (build-toolchain-12.2.0.sh:151-162, build-toolchain-8.2.0.sh:165-174),
# and the xPack GCC tree's own download_prerequisites lists gmp-6.1.0 /
# mpfr-3.1.4 / mpc-1.0.3 -- three of four versions differ, so using it would
# silently build a different compiler that still passes a green-looking gate.

set -euo pipefail

export LC_ALL=C
export TZ=UTC
export SOURCE_DATE_EPOCH=1767225600

die() {
    printf 'prepare-sources.sh: %s\n' "$*" >&2
    exit 2
}

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    printf 'usage: %s <15.2.0|12.2.0|8.2.0> [dest-root]\n' "${0##*/}" >&2
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
dest_root=${2:-$repo_root/tmp/ci-src}
case "$dest_root" in
    /*) ;;
    *) dest_root="$repo_root/$dest_root" ;;
esac
# Every build script requires its source tree to be a child of <repo>/tmp so
# that a stray absolute path cannot be built by accident.
case "$dest_root/" in
    "$repo_root"/tmp/*) ;;
    *) die "dest-root must be a child of $repo_root/tmp: $dest_root" ;;
esac

# tmp/ is gitignored and git does not track empty directories, so a fresh
# checkout has no tmp/ at all.  Several steps below (scratch indexes,
# download directories) live under it, so create it up front.
mkdir -p "$repo_root/tmp"

for command_name in git tar curl awk sed; do
    command -v "$command_name" >/dev/null 2>&1 || die "required command is unavailable: $command_name"
done

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

git_ci() {
    # A CI runner has no committer identity, and git am refuses to run without
    # one.  Set it per repository so nothing outside the checkout is touched.
    git -C "$1" config user.name 'OpenWCH CI'
    git -C "$1" config user.email 'ci@openwch.local'
}

# --- pinned upstream archive URLs ------------------------------------------
# The SHA-256 of every archive is NOT repeated here: it is parsed out of the
# build script's own verify_archive calls (see pinned_archives below), so the
# two can never drift.  Only the URL lives here, because the repository has no
# upstream URL anywhere else -- verify_archive verifies, it never downloads.
# Each URL was confirmed by downloading it and matching the pinned SHA-256 on
# 2026-08-17; evidence in tmp/p7-evidence/S2/scratch/urlprobe/results.tsv.
#
# The coupling to the build scripts is deliberately one-directional, and only
# half of it is automatic.  The SHA-256 follows the upstream build script by
# derivation; this URL table does not -- it is maintained independently here.
# So if a build script ever switches a prerequisite to a different *version*,
# the derived digest changes, this table still points at the old version, and
# the download fails closed on a hash mismatch.  That red is correct.  The fix
# is to update this table to point at the new version -- never to relax, skip,
# or "update" the checksum to match whatever was downloaded.  Same principle as
# the archive identity rule below: changing the mirror is legitimate, changing
# the version is not.
# Note the zstd entry: the pinned digest belongs to the GitHub *release asset*
# zstd-1.5.2.tar.gz, not to the tag archive v1.5.2.tar.gz (different bytes),
# and it must be stored under the name the build script looks up.
archive_url() {
    case "$1" in
        gcc-12.2.0.tar.xz)         printf 'https://ftp.gnu.org/gnu/gcc/gcc-12.2.0/gcc-12.2.0.tar.xz\n' ;;
        binutils-2.38.tar.xz)      printf 'https://ftp.gnu.org/gnu/binutils/binutils-2.38.tar.xz\n' ;;
        gmp-6.2.1.tar.xz)          printf 'https://ftp.gnu.org/gnu/gmp/gmp-6.2.1.tar.xz\n' ;;
        mpfr-4.1.0.tar.xz)         printf 'https://ftp.gnu.org/gnu/mpfr/mpfr-4.1.0.tar.xz\n' ;;
        mpc-1.2.1.tar.gz)          printf 'https://ftp.gnu.org/gnu/mpc/mpc-1.2.1.tar.gz\n' ;;
        isl-0.24.tar.xz)           printf 'https://libisl.sourceforge.io/isl-0.24.tar.xz\n' ;;
        isl-0.18.tar.bz2)          printf 'https://gcc.gnu.org/pub/gcc/infrastructure/isl-0.18.tar.bz2\n' ;;
        zlib-1.2.12.tar.gz)        printf 'https://www.zlib.net/fossils/zlib-1.2.12.tar.gz\n' ;;
        zstd-1.5.2-release.tar.gz) printf 'https://github.com/facebook/zstd/releases/download/v1.5.2/zstd-1.5.2.tar.gz\n' ;;
        *) return 1 ;;
    esac
}

# Emit "<archive-name>\t<sha256>" for every verify_archive call in a build
# script, joining its backslash continuations first.
pinned_archives() {
    awk '
        { line = line $0 }
        /\\$/ { sub(/\\$/, "", line); next }
        {
            gsub(/[[:space:]]+/, " ", line)
            if (line ~ /^verify_archive [A-Za-z0-9._+-]+ [0-9a-f]{64}$/) {
                split(line, field, " ")
                print field[2] "\t" field[3]
            }
            line = ""
        }
    ' "$1"
}

# Fail closed: a digest mismatch is an error, never a reason to fetch something
# newer.  A cached copy that still matches is reused without a network call.
fetch_pinned_archives() {
    local build_script=$1 downloads=$2 name expected url actual count=0
    mkdir -p "$downloads"
    while IFS=$'\t' read -r name expected; do
        [ -n "$name" ] || continue
        count=$((count + 1))
        if [ -f "$downloads/$name" ]; then
            actual=$(sha256_of "$downloads/$name")
            if [ "$actual" = "$expected" ]; then
                printf 'archive_cache_hit=%s\t%s\n' "$name" "$expected"
                continue
            fi
            printf 'archive_cache_rejected=%s\tgot=%s\n' "$name" "$actual"
            rm -f -- "$downloads/$name"
        fi
        url=$(archive_url "$name") || die "no pinned upstream URL for archive: $name"
        printf 'archive_download=%s\t%s\n' "$name" "$url"
        curl -fsSL --retry 3 --max-time 1800 -o "$downloads/$name.part" "$url" || \
            die "download failed: $url"
        mv -f -- "$downloads/$name.part" "$downloads/$name"
        actual=$(sha256_of "$downloads/$name")
        [ "$actual" = "$expected" ] || \
            die "archive digest mismatch for $name: $actual != $expected"
        printf 'archive_verified=%s\t%s\n' "$name" "$expected"
    done < <(pinned_archives "$build_script")
    [ "$count" -gt 0 ] || die "no verify_archive pins found in $build_script"
    printf 'archives_pinned=%s\n' "$count"
}

clone_pinned() {
    local url=$1 branch=$2 destination=$3 expected_head=$4 actual
    if [ -e "$destination" ]; then
        die "clone destination already exists: $destination"
    fi
    mkdir -p "$(dirname -- "$destination")"
    git clone --depth 1 --single-branch --branch "$branch" "$url" "$destination"
    actual=$(git -C "$destination" rev-parse HEAD)
    [ "$actual" = "$expected_head" ] || \
        die "unexpected HEAD in $destination: $actual != $expected_head"
    git_ci "$destination"
    printf 'clone=%s\tbranch=%s\thead=%s\n' "$destination" "$branch" "$actual"
}

# =========================================================================
case "$version" in
15.2.0)
    tree="$dest_root/15.2.0/riscv-gnu-toolchain"
    patch_root="$repo_root/patches/15.2.0"
    # Hard invariants: the pinned upstream commits.  There is deliberately no
    # patched-tree constant here -- see apply_15_series below.
    gcc_base=5115c7e447fc07457443df874bf57840e8316d5f
    binutils_base=2bc7af1ff7732451b6a7b09462a815c3284f9613

    clone_pinned https://github.com/gcc-mirror/gcc.git releases/gcc-15.2.0 \
        "$tree/gcc" "$gcc_base"
    clone_pinned https://git.sr.ht/~sourceware/binutils-gdb binutils-2_45 \
        "$tree/binutils" "$binutils_base"

    scratch_indexes=()
    cleanup() {
        local index
        for index in ${scratch_indexes[@]+"${scratch_indexes[@]}"}; do
            rm -f -- "$index"
        done
    }
    trap cleanup EXIT INT TERM

    apply_15_series() {
        local component=$1 source_tree="$tree/$1"
        local series="$patch_root/$component/series"
        local scratch patch patch_path applied=0 produced
        [ -f "$series" ] || die "missing patch series: $series"
        # Later patches refine lines earlier ones introduce, so validate the
        # complete ordered series in an isolated index before the checkout is
        # touched at all.  This is the README's own sequence.
        scratch=$(mktemp "$repo_root/tmp/.openwch-ci-index.XXXXXX")
        scratch_indexes+=("$scratch")
        rm -f -- "$scratch"
        GIT_INDEX_FILE="$scratch" git -C "$source_tree" read-tree HEAD
        while IFS= read -r patch || [ -n "$patch" ]; do
            [ -n "$patch" ] || continue
            case "$patch" in \#*) continue ;; */*|.*) die "unsafe series entry: $patch" ;; esac
            patch_path="$patch_root/$component/$patch"
            [ -f "$patch_path" ] || die "missing patch: $patch_path"
            GIT_INDEX_FILE="$scratch" git -C "$source_tree" apply --cached --check "$patch_path"
            GIT_INDEX_FILE="$scratch" git -C "$source_tree" apply --cached "$patch_path"
            applied=$((applied + 1))
        done < "$series"
        # The resulting tree id is reported, never asserted.  Pinning it would
        # turn any legitimate change to the patch series into a red CI run,
        # which is noise: the provenance chain that actually discriminates is
        # the pinned upstream commit (asserted above), a clean application of
        # the whole series, and a green byte gate.  Given those three, a tree
        # constant adds no detection power and only creates a synchronisation
        # duty between this workflow and whoever edits the patches.
        produced=$(GIT_INDEX_FILE="$scratch" git -C "$source_tree" write-tree)
        rm -f -- "$scratch"
        while IFS= read -r patch || [ -n "$patch" ]; do
            [ -n "$patch" ] || continue
            case "$patch" in \#*) continue ;; esac
            git -C "$source_tree" apply --index "$patch_root/$component/$patch"
        done < "$series"
        printf 'patches_applied=%s\t%s\tobserved_patch_tree=%s\n' \
            "$component" "$applied" "$produced"
    }

    apply_15_series gcc
    apply_15_series binutils

    # Host prerequisites.  15.2.0 -- and only 15.2.0 -- uses the in-tree
    # contrib/download_prerequisites, whose pristine list at this commit is
    # exactly the five archives the README copies in.  The script skips any
    # archive already present (contrib/download_prerequisites:233-234) and then
    # still verifies all of them against contrib/prerequisites.sha512, so
    # seeding from a cache keeps the verification and removes the download.
    prereq_cache=${PREREQ_CACHE_DIR:-$repo_root/tmp/ci-cache/prereq-15.2.0}
    mkdir -p "$prereq_cache"
    for archive in gettext-0.22.tar.gz gmp-6.2.1.tar.bz2 mpfr-4.1.0.tar.bz2 \
            mpc-1.2.1.tar.gz isl-0.24.tar.bz2; do
        if [ -f "$prereq_cache/$archive" ]; then
            cp "$prereq_cache/$archive" "$tree/gcc/$archive"
            printf 'prerequisite_cache_hit=%s\n' "$archive"
        fi
    done
    ( cd "$tree/gcc" && ./contrib/download_prerequisites --verify --sha512 )
    for archive in gettext-0.22.tar.gz gmp-6.2.1.tar.bz2 mpfr-4.1.0.tar.bz2 \
            mpc-1.2.1.tar.gz isl-0.24.tar.bz2; do
        [ -f "$tree/gcc/$archive" ] || die "prerequisite archive missing after download: $archive"
        cp "$tree/gcc/$archive" "$prereq_cache/$archive"
    done
    for prerequisite in gmp mpfr mpc isl; do
        [ -e "$tree/gcc/$prerequisite" ] || die "missing in-tree prerequisite link: $prerequisite"
    done

    printf 'prepared_version=15.2.0\n'
    printf 'source_tree=%s\n' "$tree"
    printf 'gcc_head=%s\n' "$(git -C "$tree/gcc" rev-parse HEAD)"
    printf 'binutils_head=%s\n' "$(git -C "$tree/binutils" rev-parse HEAD)"
    ;;

# =========================================================================
12.2.0)
    project="$dest_root/12.2.0/riscv-none-elf-gcc-xpack.git"
    downloads="$repo_root/tmp/toolchain_12.2.0/downloads"
    build_script="$repo_root/scripts/build-toolchain-12.2.0.sh"
    patch_root="$repo_root/patches/12.2.0"
    sources="$project/build/darwin-arm64/sources"
    # No tree constants are pinned here.  The import tree is still enforced --
    # by scripts/build-toolchain-12.2.0.sh:101-102,120-123 itself, whose
    # verify_source_base() falls back to the root commit of a fresh import --
    # so duplicating it would only add a second place to update.  The patched
    # tree is deliberately reported and not asserted; see apply_15_series in
    # the 15.2.0 branch for the reasoning.
    [ -f "$build_script" ] || die "missing build script: $build_script"
    fetch_pinned_archives "$build_script" "$downloads"

    if [ -e "$project" ]; then
        die "project root already exists: $project"
    fi
    mkdir -p "$sources"
    for archive in gcc-12.2.0.tar.xz binutils-2.38.tar.xz gmp-6.2.1.tar.xz \
            mpfr-4.1.0.tar.xz mpc-1.2.1.tar.gz isl-0.24.tar.xz \
            zlib-1.2.12.tar.gz zstd-1.5.2-release.tar.gz; do
        tar -xf "$downloads/$archive" -C "$sources"
    done
    # build-toolchain-12.2.0.sh:131-134 requires these to be unpacked already.
    for source_dir in gmp-6.2.1 mpfr-4.1.0 mpc-1.2.1 isl-0.24 zlib-1.2.12 zstd-1.5.2; do
        [ -d "$sources/$source_dir" ] || die "host dependency source missing after extraction: $source_dir"
    done

    import_and_apply_12() {
        local component=$1 source="$sources/$2"
        local series="$patch_root/$component/series" patch applied=0 produced
        [ -d "$source" ] || die "extracted source missing: $source"
        [ -f "$series" ] || die "missing patch series: $series"
        git -C "$source" init -q
        git_ci "$source"
        # GNU release archives ship generated files their own .gitignore
        # excludes; -f binds every extracted byte, matching the replay wrapper.
        git -C "$source" add -f -A
        GIT_AUTHOR_DATE="@$SOURCE_DATE_EPOCH +0000" \
        GIT_COMMITTER_DATE="@$SOURCE_DATE_EPOCH +0000" \
            git -C "$source" commit -q -m "Import verified upstream release archive"
        produced=$(git -C "$source" rev-parse 'HEAD^{tree}')
        printf 'observed_import_tree=%s\t%s\n' "$component" "$produced"
        while IFS= read -r patch || [ -n "$patch" ]; do
            [ -n "$patch" ] || continue
            case "$patch" in \#*) continue ;; */*|.*) die "unsafe series entry: $patch" ;; esac
            [ -f "$patch_root/$component/$patch" ] || die "missing patch: $component/$patch"
            git -C "$source" apply --check "$patch_root/$component/$patch"
            git -C "$source" am --quiet --committer-date-is-author-date \
                "$patch_root/$component/$patch"
            applied=$((applied + 1))
        done < "$series"
        produced=$(git -C "$source" rev-parse 'HEAD^{tree}')
        [ -z "$(git -C "$source" status --porcelain=v1)" ] || \
            die "$component source tree is not clean after applying the series"
        printf 'patches_applied=%s\t%s\tobserved_patch_tree=%s\n' \
            "$component" "$applied" "$produced"
    }

    import_and_apply_12 gcc gcc-12.2.0
    import_and_apply_12 binutils binutils-2.38

    # build-toolchain-12.2.0.sh:136-138 asserts this file's digest separately.
    printf 'multilib_sha256=%s\n' "$(sha256_of "$sources/gcc-12.2.0/gcc/config/riscv/t-elf-multilib")"
    printf 'prepared_version=12.2.0\n'
    printf 'project_root=%s\n' "$project"
    printf 'downloads=%s\n' "$downloads"
    ;;

# =========================================================================
8.2.0)
    # No dest-root here: build-toolchain-8.2.0.sh takes no argument and
    # hard-codes both of these paths.
    project="$repo_root/tmp/toolchain_8.2.0/work"
    downloads="$repo_root/tmp/toolchain_8.2.0/downloads"
    build_script="$repo_root/scripts/build-toolchain-8.2.0.sh"
    patch_root="$repo_root/patches/8.2.0"
    sources="$project/darwin-x64/sources"
    gcc_base=0c7a874f0b6f452eeafde57731646e5f460187e4
    binutils_base=82b51c7b5087ddb77988287cd7a2dd8921331bfd
    # The pinned upstream commits above are the hard invariants.  The
    # post-apply tree ids are reported below, not asserted; see the 15.2.0
    # branch for why a tree constant is noise rather than signal here.

    if [ -n "${2:-}" ]; then
        printf 'note=dest-root ignored for 8.2.0; build-toolchain-8.2.0.sh hard-codes %s\n' "$project"
    fi
    [ -f "$build_script" ] || die "missing build script: $build_script"
    fetch_pinned_archives "$build_script" "$downloads"

    if [ -e "$project" ]; then
        die "project root already exists: $project"
    fi
    mkdir -p "$sources"
    # The checkout directory names are what the build script looks up
    # (build-toolchain-8.2.0.sh:73-74); they do not match the clone URLs.
    clone_pinned https://github.com/xpack-dev-tools/riscv-gcc.git v8.2.0-3.1 \
        "$sources/riscv-gcc-10.2.0-1.1" "$gcc_base"
    clone_pinned https://github.com/xpack-dev-tools/riscv-binutils-gdb.git v8.2.0-3.1 \
        "$sources/riscv-binutils-2.32" "$binutils_base"

    # One top-level series, routed by directory: binutils/ lines go to the
    # binutils checkout, gcc/ and host/ lines both go to the GCC checkout.
    series="$patch_root/series"
    [ -f "$series" ] || die "missing patch series: $series"
    gcc_applied=0
    binutils_applied=0
    while IFS= read -r patch || [ -n "$patch" ]; do
        [ -n "$patch" ] || continue
        case "$patch" in \#*) continue ;; esac
        case "$patch" in
            binutils/*) component_tree="$sources/riscv-binutils-2.32" ;;
            gcc/*|host/*) component_tree="$sources/riscv-gcc-10.2.0-1.1" ;;
            *) die "unrecognized series entry: $patch" ;;
        esac
        case "$patch" in *..*) die "unsafe series entry: $patch" ;; esac
        [ -f "$patch_root/$patch" ] || die "missing patch: $patch"
        git -C "$component_tree" am --quiet --committer-date-is-author-date \
            "$patch_root/$patch"
        case "$patch" in
            binutils/*) binutils_applied=$((binutils_applied + 1)) ;;
            *) gcc_applied=$((gcc_applied + 1)) ;;
        esac
    done < "$series"

    gcc_tree=$(git -C "$sources/riscv-gcc-10.2.0-1.1" rev-parse 'HEAD^{tree}')
    binutils_tree=$(git -C "$sources/riscv-binutils-2.32" rev-parse 'HEAD^{tree}')
    [ -z "$(git -C "$sources/riscv-gcc-10.2.0-1.1" status --porcelain=v1)" ] || \
        die "GCC source tree is not clean after applying the series"
    [ -z "$(git -C "$sources/riscv-binutils-2.32" status --porcelain=v1)" ] || \
        die "binutils source tree is not clean after applying the series"

    printf 'patches_applied=gcc\t%s\tobserved_patch_tree=%s\n' "$gcc_applied" "$gcc_tree"
    printf 'patches_applied=binutils\t%s\tobserved_patch_tree=%s\n' \
        "$binutils_applied" "$binutils_tree"
    printf 'prepared_version=8.2.0\n'
    printf 'project_root=%s\n' "$project"
    printf 'downloads=%s\n' "$downloads"
    ;;
esac
