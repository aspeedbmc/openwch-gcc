#!/usr/bin/env bash
# Prepare fresh GCC 12.2.0/binutils 2.38 sources from verified archives,
# apply the exported OpenWCH series, build the compiler-only toolchain, inject
# the official target payload, and run the 12.2.0 EVT byte gate.
#
# Usage: scripts/replay-toolchain-12.2.0.sh [replay-project-root]

set -euo pipefail
umask 022

export LC_ALL=C
export TZ=UTC
export SOURCE_DATE_EPOCH=1767225600

die() {
    printf 'replay-toolchain-12.2.0.sh: %s\n' "$*" >&2
    exit 2
}

if [ "$#" -gt 1 ]; then
    printf 'usage: %s [replay-project-root]\n' "${0##*/}" >&2
    exit 2
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
downloads="$repo_root/tmp/toolchain_12.2.0/downloads"
patch_root="$repo_root/patches/12.2.0"
default_replay="$repo_root/tmp/toolchain_12.2.0/pristine-replay/riscv-none-elf-gcc-xpack.git"
replay_argument=${1:-$default_replay}

case "$replay_argument" in
    /*) ;;
    *) replay_argument="$repo_root/$replay_argument" ;;
esac
replay_parent=$(dirname -- "$replay_argument")
replay_name=$(basename -- "$replay_argument")
mkdir -p "$replay_parent"
replay_parent=$(CDPATH= cd -- "$replay_parent" && pwd -P)
replay_argument="$replay_parent/$replay_name"
case "$replay_argument" in
    "$repo_root/tmp/toolchain_12.2.0/pristine-replay/"*|\
    "$repo_root/tmp/toolchain_12.2.0/replay-"*) ;;
    *) die "replay root must be in the dedicated pristine-replay or replay-* namespace below $repo_root/tmp/toolchain_12.2.0" ;;
esac

archive_sha() {
    case "$1" in
        gcc-12.2.0.tar.xz)
            printf '%s\n' e549cf9cf3594a00e27b6589d4322d70e0720cdd213f39beb4181e06926230ff ;;
        binutils-2.38.tar.xz)
            printf '%s\n' e316477a914f567eccc34d5d29785b8b0f5a10208d36bbacedcc39048ecfe024 ;;
        gmp-6.2.1.tar.xz)
            printf '%s\n' fd4829912cddd12f84181c3451cc752be224643e87fac497b69edddadc49b4f2 ;;
        mpfr-4.1.0.tar.xz)
            printf '%s\n' 0c98a3f1732ff6ca4ea690552079da9c597872d30e96ec28414ee23c95558a7f ;;
        mpc-1.2.1.tar.gz)
            printf '%s\n' 17503d2c395dfcf106b622dc142683c1199431d095367c6aacba6eec30340459 ;;
        isl-0.24.tar.xz)
            printf '%s\n' 043105cc544f416b48736fff8caf077fb0663a717d06b1113f16e391ac99ebad ;;
        zlib-1.2.12.tar.gz)
            printf '%s\n' 91844808532e5ce316b3c010929493c0244f3d37593afd6de04f71821d5136d9 ;;
        zstd-1.5.2-release.tar.gz)
            printf '%s\n' 7c42d56fac126929a6a85dbc73ff1db2411d04f104fae9bdea51305663a83fd0 ;;
        *) die "no digest registered for archive: $1" ;;
    esac
}

sha256() {
    shasum -a 256 "$1" | awk '{print $1}'
}

verify_archive() {
    local archive=$1
    local expected
    expected=$(archive_sha "$archive")
    [ -f "$downloads/$archive" ] || die "missing archive: $downloads/$archive"
    [ "$(sha256 "$downloads/$archive")" = "$expected" ] || \
        die "archive digest mismatch: $archive"
    printf 'archive_verified=%s\t%s\n' "$archive" "$expected"
}

safe_clear_replay() {
    local path=$1
    case "$path" in
        "$repo_root/tmp/toolchain_12.2.0/pristine-replay/"*|\
        "$repo_root/tmp/toolchain_12.2.0/replay-"*)
            if [ -L "$path" ]; then
                unlink "$path"
            elif [ -d "$path" ]; then
                find "$path" -depth -mindepth 1 -delete
                rmdir "$path"
            elif [ -e "$path" ]; then
                die "replay root exists but is not a directory: $path"
            fi
            ;;
        *) die "refusing to clear unexpected replay root: $path" ;;
    esac
}

apply_series() {
    local component=$1
    local source=$2
    local series="$patch_root/$component/series"
    local patch

    [ -f "$series" ] || die "missing patch series: $series"
    while IFS= read -r patch; do
        [ -n "$patch" ] || continue
        case "$patch" in \#*) continue ;; esac
        [ -f "$patch_root/$component/$patch" ] || \
            die "missing patch listed by series: $component/$patch"
        git -C "$source" apply --check "$patch_root/$component/$patch"
        printf 'apply_check=%s\t%s\tPASS\n' "$component" "$patch"
        git -C "$source" am --quiet --committer-date-is-author-date \
            "$patch_root/$component/$patch"
    done < "$series"
}

active_project="$repo_root/tmp/toolchain_12.2.0/riscv-none-elf-gcc-xpack.git"
active_gcc="$active_project/build/darwin-arm64/sources/gcc-12.2.0"
active_binutils="$active_project/build/darwin-arm64/sources/binutils-2.38"
[ -d "$active_gcc/.git" ] || die "active GCC source is missing: $active_gcc"
[ -d "$active_binutils/.git" ] || die "active binutils source is missing: $active_binutils"
[ -z "$(git -C "$active_gcc" status --porcelain=v1)" ] || die "active GCC source is dirty"
[ -z "$(git -C "$active_binutils" status --porcelain=v1)" ] || die "active binutils source is dirty"
active_gcc_tree=$(git -C "$active_gcc" rev-parse 'HEAD^{tree}')
active_binutils_tree=$(git -C "$active_binutils" rev-parse 'HEAD^{tree}')

for archive in \
    gcc-12.2.0.tar.xz binutils-2.38.tar.xz \
    gmp-6.2.1.tar.xz mpfr-4.1.0.tar.xz mpc-1.2.1.tar.gz \
    isl-0.24.tar.xz zlib-1.2.12.tar.gz zstd-1.5.2-release.tar.gz; do
    verify_archive "$archive"
done

if [ -e "$replay_argument" ] || [ -L "$replay_argument" ]; then
    safe_clear_replay "$replay_argument"
fi
mkdir -p "$replay_argument/build/darwin-arm64/sources"
sources="$replay_argument/build/darwin-arm64/sources"

tar -xf "$downloads/gcc-12.2.0.tar.xz" -C "$sources"
tar -xf "$downloads/binutils-2.38.tar.xz" -C "$sources"
tar -xf "$downloads/gmp-6.2.1.tar.xz" -C "$sources"
tar -xf "$downloads/mpfr-4.1.0.tar.xz" -C "$sources"
tar -xf "$downloads/mpc-1.2.1.tar.gz" -C "$sources"
tar -xf "$downloads/isl-0.24.tar.xz" -C "$sources"
tar -xf "$downloads/zlib-1.2.12.tar.gz" -C "$sources"
tar -xf "$downloads/zstd-1.5.2-release.tar.gz" -C "$sources"

for component in gcc binutils; do
    if [ "$component" = gcc ]; then
        source="$sources/gcc-12.2.0"
    else
        source="$sources/binutils-2.38"
    fi
    git -C "$source" init -q
    git -C "$source" config user.name 'OpenWCH pristine replay'
    git -C "$source" config user.email 'phase4-replay@openwch.local'
    # GNU release archives contain generated distribution files that their
    # upstream .gitignore rules intentionally ignore (info manuals, catalogs,
    # and test fixtures).  The verified archive import must nevertheless bind
    # every extracted byte, matching the active tarball-import baseline.
    git -C "$source" add -f -A
    GIT_AUTHOR_DATE="@$SOURCE_DATE_EPOCH +0000" \
    GIT_COMMITTER_DATE="@$SOURCE_DATE_EPOCH +0000" \
        git -C "$source" commit -q -m "Import verified upstream release archive"
    apply_series "$component" "$source"
done

replay_gcc_tree=$(git -C "$sources/gcc-12.2.0" rev-parse 'HEAD^{tree}')
replay_binutils_tree=$(git -C "$sources/binutils-2.38" rev-parse 'HEAD^{tree}')
[ "$replay_gcc_tree" = "$active_gcc_tree" ] || \
    die "replayed GCC tree differs from active: $replay_gcc_tree != $active_gcc_tree"
[ "$replay_binutils_tree" = "$active_binutils_tree" ] || \
    die "replayed binutils tree differs from active: $replay_binutils_tree != $active_binutils_tree"
printf 'tree_match=gcc\t%s\tPASS\n' "$replay_gcc_tree"
printf 'tree_match=binutils\t%s\tPASS\n' "$replay_binutils_tree"

literal_project=/Users/mrs/Work/riscv-none-elf-gcc-xpack.git
previous_target=
if [ -L "$literal_project" ]; then
    previous_target=$(readlink "$literal_project")
elif [ -e "$literal_project" ]; then
    die "literal project path exists but is not a symlink: $literal_project"
fi
restore_literal() {
    if [ -n "$previous_target" ]; then
        ln -sfn "$previous_target" "$literal_project"
    else
        unlink "$literal_project" 2>/dev/null || true
    fi
}
trap restore_literal EXIT INT TERM
mkdir -p "$(dirname -- "$literal_project")"
ln -sfn "$replay_argument" "$literal_project"

CLEAN_HOST_DEPS=1 "$script_dir/build-toolchain-12.2.0.sh" "$replay_argument"
application="$replay_argument/build/darwin-arm64/application"
"$script_dir/evt-compare.sh" 12.2.0 "$application"

printf 'replay_project=%s\n' "$replay_argument"
printf 'gcc_head=%s\n' "$(git -C "$sources/gcc-12.2.0" rev-parse HEAD)"
printf 'gcc_tree=%s\n' "$(git -C "$sources/gcc-12.2.0" rev-parse HEAD^{tree})"
printf 'binutils_head=%s\n' "$(git -C "$sources/binutils-2.38" rev-parse HEAD)"
printf 'binutils_tree=%s\n' "$(git -C "$sources/binutils-2.38" rev-parse HEAD^{tree})"
printf 'active_gcc_tree=%s\n' "$active_gcc_tree"
printf 'active_binutils_tree=%s\n' "$active_binutils_tree"
printf 'application=%s\n' "$application"
