#!/usr/bin/env bash
# Build the GCC 12.2.0/binutils 2.38 compiler-only toolchain at the literal
# WCH xPack paths and inject the official target libraries/sysroot bytewise.
# Usage: scripts/build-toolchain-12.2.0.sh [expected-xpack-project-root]
# Set BUILD_JOBS to override parallelism; set CLEAN_HOST_DEPS=1 to rebuild the
# pinned GMP/MPFR/MPC/ISL/zlib/zstd host dependency prefix.
# The pre-build patch-series check works on a fresh replay tree as well as on
# the working mirror: it anchors on content (imported tree, frozen patch tree,
# stable patch IDs), and the commit-anchored guards run only where the anchored
# objects exist.  See the comments at the checks themselves.

set -euo pipefail
umask 022

export LC_ALL=C
export TZ=UTC
export SOURCE_DATE_EPOCH=1767225600
export ZERO_AR_DATE=1
export CC=/usr/bin/clang
export CXX=/usr/bin/clang++
export MACOSX_DEPLOYMENT_TARGET=11.0
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
export MAKEINFO=/usr/bin/true
unset CFLAGS CXXFLAGS CPPFLAGS LDFLAGS LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH
unset AR AS LD NM RANLIB SDKROOT GCC_EXEC_PREFIX COMPILER_PATH

die() {
    printf 'build-toolchain-12.2.0.sh: %s\n' "$*" >&2
    exit 2
}

if [ "$#" -gt 1 ]; then
    printf 'usage: %s [expected-xpack-project-root]\n' "${0##*/}" >&2
    exit 2
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
default_project="$repo_root/tmp/toolchain_12.2.0/riscv-none-elf-gcc-xpack.git"
project_argument=${1:-$default_project}
[ -d "$project_argument" ] || die "expected project root does not exist: $project_argument"
project_root=$(CDPATH= cd -- "$project_argument" && pwd -P)
case "$project_root" in
    "$repo_root/tmp/"*) ;;
    *) die "expected project root must be a child of $repo_root/tmp: $project_root" ;;
esac
downloads="$repo_root/tmp/toolchain_12.2.0/downloads"

literal_project=/Users/mrs/Work/riscv-none-elf-gcc-xpack.git
[ -L "$literal_project" ] || die "required literal symlink is missing: $literal_project"
link_target=$(readlink "$literal_project")
[ "$link_target" = "$project_root" ] || \
    die "literal symlink mismatch: expected $project_root, got $link_target"

literal_platform="$literal_project/build/darwin-arm64"
physical_platform="$project_root/build/darwin-arm64"
host_triplet=aarch64-apple-darwin23.6.0
host_root="$literal_platform/$host_triplet"
sources="$literal_platform/sources"
build_root="$host_root/build"
deps_install="$host_root/install"
application="$literal_platform/application"
logs="$host_root/logs/openwch-phase4"
host_deps_logs="$host_root/logs/openwch-phase4-host-deps"
build_lock="$host_root/.openwch-phase4-build.lock"

gcc_source="$sources/gcc-12.2.0"
binutils_source="$sources/binutils-2.38"
gcc_build="$build_root/riscv-wch-elf-gcc-12.2.0-final"
binutils_build="$build_root/riscv-wch-elf-binutils-2.38"
official_root="$repo_root/ref/gcc/darwin-arm64/12.2.0"
official_gcc="$official_root/bin/riscv-wch-elf-gcc"
target=riscv-wch-elf
gcc_version=12.2.0
branding='xPack GNU RISC-V Embedded GCC arm64'
build_jobs=${BUILD_JOBS:-8}
clean_host_deps=${CLEAN_HOST_DEPS:-0}
host_cflags='-O2 -mmacosx-version-min=11.0'

case "$build_jobs" in
    ''|*[!0-9]*) die "BUILD_JOBS must be a positive integer" ;;
    0) die "BUILD_JOBS must be greater than zero" ;;
esac
case "$clean_host_deps" in
    0|1) ;;
    *) die "CLEAN_HOST_DEPS must be 0 or 1" ;;
esac

[ -x /usr/bin/clang ] || die "system clang is unavailable"
[ -x /usr/bin/clang++ ] || die "system clang++ is unavailable"
[ -x "$official_gcc" ] || die "official GCC is unavailable: $official_gcc"
[ -d "$gcc_source/.git" ] || die "missing GCC patch-management tree"
[ -d "$binutils_source/.git" ] || die "missing binutils patch-management tree"

mkdir -p "$host_root"
if ! mkdir "$build_lock" 2>/dev/null; then
    die "another Phase 4 build holds $build_lock"
fi
temporary_indexes=()
cleanup() {
    rmdir "$build_lock" 2>/dev/null || true
    local path
    for path in ${temporary_indexes+"${temporary_indexes[@]}"}; do
        rm -f -- "$path"
    done
}
trap cleanup EXIT INT TERM

gcc_base=3280576e992d8fcd57fabd4bb85944fcf2bfaddb
binutils_base=dc5b5e8935f95730fcd9ac603627d834d52fef64
gcc_base_tree=e66ae7537f9afc0ad8af700e2f19eb6b8b35c9d2
binutils_base_tree=d66ce22b2d9b8ecdf6348b9a85137b63cd93e4bd

verify_source_base() {
    local source_tree=$1
    local known_commit=$2
    local expected_tree=$3
    local candidate

    if git -C "$source_tree" merge-base --is-ancestor "$known_commit" HEAD \
        2>/dev/null; then
        candidate=$known_commit
    else
        candidate=$(git -C "$source_tree" rev-list --max-parents=0 HEAD | head -n 1)
    fi
    [ -n "$candidate" ] && \
        [ "$(git -C "$source_tree" rev-parse "$candidate^{tree}")" = "$expected_tree" ]
}

verify_source_base "$gcc_source" "$gcc_base" "$gcc_base_tree" || \
    die "GCC HEAD does not descend from the verified tarball import"
verify_source_base "$binutils_source" "$binutils_base" "$binutils_base_tree" || \
    die "binutils HEAD does not descend from the verified tarball import"
[ -z "$(git -C "$gcc_source" status --porcelain=v1)" ] || die "GCC source tree is not clean"
[ -z "$(git -C "$binutils_source" status --porcelain=v1)" ] || die "binutils source tree is not clean"

# Pre-build verification that what is about to be compiled is exactly the
# ordered public patch series in patches/12.2.0/ and nothing else.  Modelled on
# build-toolchain-15.2.0-linux.sh:171-248.
patch_root="$repo_root/patches/12.2.0"
gcc_frozen_patch_tree=af74531c952c78bab9089ee93af50e3a7fe992ea
binutils_frozen_patch_tree=0d01a497ae860ce540c463320ce0a4436e880a05

[ -f "$patch_root/patch-id.tsv" ] || die "missing stable patch-ID ledger"
# patch-id.tsv gained a fourth column (source_commit) when the From lines were
# unified; the reads below are positional, so pin the schema instead of the
# column count to make a future layout change fail loudly here rather than
# silently select the wrong field.
[ "$(head -n 1 "$patch_root/patch-id.tsv")" = \
    "$(printf 'component\tpatch\tstable_patch_id\tsource_commit')" ] || \
    die "unexpected patch-id.tsv schema"

verify_patched_worktree() {
    local component=$1 source_tree=$2 base_tree=$3 expected_count=$4
    local frozen_patch_tree=$5
    local series_file="$patch_root/$component/series"
    local expected_index actual_index added_paths patch_name patch_path
    local expected_tree_id actual_tree_id patch_count
    local expected_patch_id actual_patch_id expected_source_commit actual_source_commit

    [ -f "$series_file" ] || die "missing patch series: $series_file"

    expected_index=$(mktemp "$repo_root/tmp/.openwch-phase4-index.XXXXXX")
    actual_index=$(mktemp "$repo_root/tmp/.openwch-phase4-index.XXXXXX")
    added_paths=$(mktemp "$repo_root/tmp/.openwch-phase4-index.XXXXXX")
    temporary_indexes+=("$expected_index" "$actual_index" "$added_paths")
    rm -f -- "$expected_index" "$actual_index"

    GIT_INDEX_FILE="$expected_index" git -C "$source_tree" read-tree "$base_tree"
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
        actual_patch_id=$(git -C "$source_tree" patch-id --stable < "$patch_path" | \
            awk '{print $1}')
        [ "$actual_patch_id" = "$expected_patch_id" ] || \
            die "stable patch ID mismatch for $component/$patch_name"
        expected_source_commit=$(awk -F '\t' -v component="$component" -v patch="$patch_name" \
            '$1 == component && $2 == patch { print $4 }' "$patch_root/patch-id.tsv")
        actual_source_commit=$(awk 'NR == 1 && $1 == "From" { print $2; exit }' "$patch_path")
        [ "$actual_source_commit" = "$expected_source_commit" ] || \
            die "source commit mismatch for $component/$patch_name"
        # Dual anchor: the equality above is the content anchor and holds in any
        # tree, while reachability is the working-mirror guard and is only
        # decidable where the exporting commit object still exists.  A fresh
        # replay (archive import + git am) has no such object, so disclose the
        # skipped guard on one line and keep the content anchors as the proof.
        if git -C "$source_tree" cat-file -e "$actual_source_commit^{commit}" 2>/dev/null; then
            git -C "$source_tree" merge-base --is-ancestor "$actual_source_commit" HEAD || \
                die "source commit is not reachable from HEAD: $component/$patch_name"
        else
            printf 'from_commit_unavailable=%s/%s\n' "$component" "$patch_name"
        fi
        printf 'patch_id=PASS component=%s patch=%s id=%s from=%s\n' \
            "$component" "$patch_name" "$actual_patch_id" "$actual_source_commit"
        GIT_INDEX_FILE="$expected_index" \
            git -C "$source_tree" apply --cached --check "$patch_path"
        GIT_INDEX_FILE="$expected_index" \
            git -C "$source_tree" apply --cached "$patch_path"
        patch_count=$((patch_count + 1))
    done < "$series_file"
    [ "$patch_count" -eq "$expected_count" ] || \
        die "$component series has $patch_count patches; expected $expected_count"
    expected_tree_id=$(GIT_INDEX_FILE="$expected_index" git -C "$source_tree" write-tree)
    [ "$expected_tree_id" = "$frozen_patch_tree" ] || \
        die "$component public patch series does not produce the frozen patch tree"

    GIT_INDEX_FILE="$actual_index" git -C "$source_tree" read-tree "$base_tree"
    GIT_INDEX_FILE="$actual_index" git -C "$source_tree" add -u -- .
    # git add -u deliberately omits files introduced by a patch.  Add only the
    # paths that the expected patched index classifies as new; unrelated
    # untracked prerequisite archives/directories stay outside the check.
    GIT_INDEX_FILE="$expected_index" git -C "$source_tree" \
        diff --cached --name-only --diff-filter=A -z "$base_tree" > "$added_paths"
    if [ -s "$added_paths" ]; then
        GIT_INDEX_FILE="$actual_index" git -C "$source_tree" add \
            --pathspec-from-file="$added_paths" --pathspec-file-nul
    fi
    actual_tree_id=$(GIT_INDEX_FILE="$actual_index" git -C "$source_tree" write-tree)
    [ "$actual_tree_id" = "$expected_tree_id" ] || \
        die "$component tracked worktree is not exactly the ordered public patch series"

    rm -f -- "$expected_index" "$actual_index" "$added_paths"
    printf 'series=PASS component=%s patches=%s tree=%s\n' \
        "$component" "$patch_count" "$actual_tree_id"
}

# Dual anchor: the read-tree base is the imported *tree*, which every faithful
# import reproduces, whereas the import commit exists only in this working
# mirror; the commit anchor stays in verify_source_base above, where it is a
# guard rather than the identity of what gets compiled.
verify_patched_worktree gcc "$gcc_source" "$gcc_base_tree" 9 "$gcc_frozen_patch_tree"
verify_patched_worktree binutils "$binutils_source" "$binutils_base_tree" 7 \
    "$binutils_frozen_patch_tree"

multilib_file="$gcc_source/gcc/config/riscv/t-elf-multilib"
multilib_sha=$(shasum -a 256 "$multilib_file" | awk '{print $1}')
[ "$multilib_sha" = 0f658db9868bd36123d72cc66981747b918b9e25ddd37af1b2a5d821e0c94f32 ] || \
    die "unexpected WCH multilib configuration: $multilib_sha"

for source_dir in \
    gmp-6.2.1 mpfr-4.1.0 mpc-1.2.1 isl-0.24 zlib-1.2.12 zstd-1.5.2; do
    [ -d "$sources/$source_dir" ] || die "missing host dependency source: $source_dir"
done

verify_archive() {
    local file=$1
    local expected_sha=$2
    local actual_sha
    [ -f "$downloads/$file" ] || die "missing verified source archive: $file"
    actual_sha=$(shasum -a 256 "$downloads/$file" | awk '{print $1}')
    [ "$actual_sha" = "$expected_sha" ] || die "source archive hash mismatch: $file"
}

verify_archive gcc-12.2.0.tar.xz \
    e549cf9cf3594a00e27b6589d4322d70e0720cdd213f39beb4181e06926230ff
verify_archive binutils-2.38.tar.xz \
    e316477a914f567eccc34d5d29785b8b0f5a10208d36bbacedcc39048ecfe024
verify_archive gmp-6.2.1.tar.xz \
    fd4829912cddd12f84181c3451cc752be224643e87fac497b69edddadc49b4f2
verify_archive mpfr-4.1.0.tar.xz \
    0c98a3f1732ff6ca4ea690552079da9c597872d30e96ec28414ee23c95558a7f
verify_archive mpc-1.2.1.tar.gz \
    17503d2c395dfcf106b622dc142683c1199431d095367c6aacba6eec30340459
verify_archive isl-0.24.tar.xz \
    043105cc544f416b48736fff8caf077fb0663a717d06b1113f16e391ac99ebad
verify_archive zlib-1.2.12.tar.gz \
    91844808532e5ce316b3c010929493c0244f3d37593afd6de04f71821d5136d9
verify_archive zstd-1.5.2-release.tar.gz \
    7c42d56fac126929a6a85dbc73ff1db2411d04f104fae9bdea51305663a83fd0

safe_remove() {
    local path=$1
    case "$path" in
        "$gcc_build"|"$binutils_build"|"$application"|"$logs"|\
        "$build_root/gmp-6.2.1"|"$build_root/mpfr-4.1.0"|\
        "$build_root/mpc-1.2.1"|"$build_root/isl-0.24"|\
        "$build_root/zlib-1.2.12"|"$build_root/zstd-1.5.2"|\
        "$deps_install"|"$host_deps_logs")
            rm -rf -- "$path"
            ;;
        *) die "refusing to remove unexpected path: $path" ;;
    esac
}

safe_replace() {
    local source_path=$1
    local destination=$2
    local allowed_root=$3
    [ -e "$source_path" ] || die "missing injection source: $source_path"
    case "$destination" in
        "$allowed_root"/*) ;;
        *) die "refusing to replace outside $allowed_root: $destination" ;;
    esac
    rm -rf -- "$destination"
    mkdir -p "$(dirname -- "$destination")"
    /bin/cp -cR "$source_path" "$destination"
}

safe_remove "$gcc_build"
safe_remove "$binutils_build"
safe_remove "$application"
safe_remove "$logs"
mkdir -p "$build_root" "$logs"

deps_marker="$deps_install/.openwch-phase4-host-deps"
deps_marker_payload=$(printf '%s\n' \
    'schema=1' \
    'SOURCE_DATE_EPOCH=1767225600' \
    'host_triplet=aarch64-apple-darwin23.6.0' \
    'deployment_target=11.0' \
    'libraries=gmp-6.2.1,mpfr-4.1.0,mpc-1.2.1,isl-0.24,zlib-1.2.12,zstd-1.5.2' \
    'mode=static' \
    "multilib_sha256=$multilib_sha")
if [ "$clean_host_deps" = 0 ] && [ -f "$deps_marker" ] && \
    [ "$(cat "$deps_marker")" != "$deps_marker_payload" ]; then
    die "host dependency marker does not match the pinned build; rerun with CLEAN_HOST_DEPS=1"
fi
if [ "$clean_host_deps" = 1 ] || [ ! -f "$deps_marker" ]; then
    for dep_path in \
        "$build_root/gmp-6.2.1" "$build_root/mpfr-4.1.0" \
        "$build_root/mpc-1.2.1" "$build_root/isl-0.24" \
        "$build_root/zlib-1.2.12" "$build_root/zstd-1.5.2" \
        "$deps_install" "$host_deps_logs"; do
        safe_remove "$dep_path"
    done
    mkdir -p "$deps_install" "$build_root" "$host_deps_logs"

    dep_cppflags="-I$deps_install/include"
    dep_ldflags="-L$deps_install/lib"

    mkdir -p "$build_root/gmp-6.2.1"
    (
        cd -L "$build_root/gmp-6.2.1"
        "$sources/gmp-6.2.1/configure" \
            --prefix="$deps_install" \
            --build="$host_triplet" \
            --host="$host_triplet" \
            --disable-shared \
            --enable-static \
            --enable-cxx \
            --enable-fat \
            --enable-fft \
            --with-pic
        make -j"$build_jobs"
        make install
    ) > "$host_deps_logs/host-gmp.log" 2>&1

    mkdir -p "$build_root/mpfr-4.1.0"
    (
        cd -L "$build_root/mpfr-4.1.0"
        CPPFLAGS="$dep_cppflags" LDFLAGS="$dep_ldflags" \
            "$sources/mpfr-4.1.0/configure" \
                --prefix="$deps_install" \
                --build="$host_triplet" \
                --host="$host_triplet" \
                --with-gmp="$deps_install" \
                --disable-shared \
                --enable-static \
                --enable-thread-safe
        make -j"$build_jobs"
        make install
    ) > "$host_deps_logs/host-mpfr.log" 2>&1

    mkdir -p "$build_root/mpc-1.2.1"
    (
        cd -L "$build_root/mpc-1.2.1"
        CPPFLAGS="$dep_cppflags" LDFLAGS="$dep_ldflags" \
            "$sources/mpc-1.2.1/configure" \
                --prefix="$deps_install" \
                --build="$host_triplet" \
                --host="$host_triplet" \
                --with-gmp="$deps_install" \
                --with-mpfr="$deps_install" \
                --disable-shared \
                --enable-static
        make -j"$build_jobs"
        make install
    ) > "$host_deps_logs/host-mpc.log" 2>&1

    mkdir -p "$build_root/isl-0.24"
    (
        cd -L "$build_root/isl-0.24"
        CPPFLAGS="$dep_cppflags" LDFLAGS="$dep_ldflags" \
            "$sources/isl-0.24/configure" \
                --prefix="$deps_install" \
                --build="$host_triplet" \
                --host="$host_triplet" \
                --with-gmp=system \
                --with-gmp-prefix="$deps_install" \
                --disable-shared \
                --enable-static
        make -j"$build_jobs"
        make install
    ) > "$host_deps_logs/host-isl.log" 2>&1

    mkdir -p "$build_root/zlib-1.2.12"
    (
        cd -L "$build_root/zlib-1.2.12"
        # zlib 1.2.12's Darwin configure is not a reliable VPATH build.  The
        # public xPack helper copies this host-only source into its build
        # directory before configuring it, so retain that layout here.
        /bin/cp -cR "$sources/zlib-1.2.12/." .
        # Clang 21 predefines TARGET_OS_MAC for modern Darwin.  zlib 1.2.12
        # mistakes that macro for classic Mac OS and masks fdopen; undefine it
        # only in this host dependency while retaining __APPLE__/__MACH__.
        CC=/usr/bin/clang CFLAGS="$host_cflags -UTARGET_OS_MAC" \
            ./configure --prefix="$deps_install" --static
        make -j"$build_jobs"
        make install
    ) > "$host_deps_logs/host-zlib.log" 2>&1

    mkdir -p "$build_root/zstd-1.5.2"
    (
        zstd_archive="$build_root/zstd-1.5.2/static/libzstd.a"
        make -C "$sources/zstd-1.5.2/lib" \
            -j"$build_jobs" \
            BUILD_DIR="$build_root/zstd-1.5.2" \
            "$zstd_archive"
        /usr/bin/install -m 0644 "$zstd_archive" "$deps_install/lib/libzstd.a"
        /usr/bin/install -m 0644 \
            "$sources/zstd-1.5.2/lib/zstd.h" \
            "$sources/zstd-1.5.2/lib/zstd_errors.h" \
            "$sources/zstd-1.5.2/lib/zdict.h" \
            "$deps_install/include/"
    ) > "$host_deps_logs/host-zstd.log" 2>&1

    for dep_file in \
        include/gmp.h include/mpfr.h include/mpc.h include/isl/ctx.h \
        include/zlib.h include/zstd.h lib/libgmp.a lib/libmpfr.a lib/libmpc.a \
        lib/libisl.a lib/libz.a lib/libzstd.a; do
        [ -f "$deps_install/$dep_file" ] || die "host dependency install is incomplete: $dep_file"
    done
    printf '%s\n' "$deps_marker_payload" > "$deps_marker"
fi

dep_cppflags="-I$deps_install/include"
dep_ldflags="-L$deps_install/lib"
export PKG_CONFIG_PATH="$deps_install/lib/pkgconfig"
# GCC's top-level configure records CPPFLAGS_FOR_BUILD, but the later
# gcc/configure recursion reads CPPFLAGS from its inherited environment.
# Keep the pinned dependency flags exported across configure and make so the
# child detects zstd.h (and therefore retains the official ZSTD LTO format).
export CPPFLAGS="$dep_cppflags"
export CFLAGS="$host_cflags"
export CXXFLAGS="$host_cflags"
export LDFLAGS="$dep_ldflags -mmacosx-version-min=11.0"
mkdir -p "$binutils_build" "$application"
(
    cd -L "$binutils_build"
    CPPFLAGS="$dep_cppflags -UFORTIFY_SOURCE" \
        "$binutils_source/configure" \
            --prefix="$application" \
            --infodir="$deps_install/share/info" \
            --mandir="$deps_install/share/man" \
            --htmldir="$deps_install/share/html" \
            --pdfdir="$deps_install/share/pdf" \
            --build="$host_triplet" \
            --host="$host_triplet" \
            --target="$target" \
            --program-prefix="$target-" \
            --program-suffix= \
            --disable-nls \
            --disable-gdb \
            --disable-gdbtk \
            --disable-sim \
            --disable-werror \
            --enable-initfini-array \
            --enable-lto \
            --enable-plugins \
            --enable-build-warnings=no \
            --without-gdb \
            --without-x \
            --without-tcl \
            --without-tk \
            --with-pkgversion="$branding" \
            --with-system-zlib \
            --with-isa-spec=2.2
) > "$logs/binutils-configure.log" 2>&1
(
    cd -L "$binutils_build"
    make -j"$build_jobs" MAKEINFO=/usr/bin/true
) > "$logs/binutils-build.log" 2>&1
(
    cd -L "$binutils_build"
    make install MAKEINFO=/usr/bin/true
) > "$logs/binutils-install.log" 2>&1

inject_sysroot() {
    local official_target="$official_root/$target"
    local output_target="$application/$target"
    local source_entry base

    safe_replace "$official_target/include" "$output_target/include" "$output_target"
    safe_replace "$official_target/picolibc" "$output_target/picolibc" "$output_target"
    mkdir -p "$output_target/lib"
    while IFS= read -r source_entry; do
        base=${source_entry##*/}
        [ "$base" = ldscripts ] && continue
        safe_replace "$source_entry" "$output_target/lib/$base" "$output_target"
    done < <(find "$official_target/lib" -mindepth 1 -maxdepth 1 -print | sort)
}

inject_gcc_payload() {
    local official_gcc_lib="$official_root/lib/gcc/$target/$gcc_version"
    local output_gcc_lib="$application/lib/gcc/$target/$gcc_version"
    local source_entry base

    mkdir -p "$output_gcc_lib"
    while IFS= read -r source_entry; do
        base=${source_entry##*/}
        case "$base" in
            rv*|crtbegin.o|crtend.o|crti.o|crtn.o|libgcc.a|libgcov.a|\
            libcaf_single.a|picolibc.specs|picolibcpp.specs|finclude)
                safe_replace "$source_entry" "$output_gcc_lib/$base" "$output_gcc_lib"
                ;;
        esac
    done < <(find "$official_gcc_lib" -mindepth 1 -maxdepth 1 -print | sort)
}

# The final GCC configure probes sysroot/include/stdio.h.  Install the official
# target headers and libraries before configure, then restore them after
# install-gcc so no compiler installation step can replace target payload.
inject_sysroot

export PATH="$application/bin:/usr/bin:/bin:/usr/sbin:/sbin"
mkdir -p "$gcc_build"
(
    cd -L "$gcc_build"
    /usr/bin/python3 - "$official_gcc" "$logs/wch-gcc-v.txt" \
            "$logs/gcc-configure-argv.json" <<'PY'
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
configured = lines[0] + "\n"
expected_sha = "3028beb3525140d50c5a8417aac51ddfcd04859d6657cb0881246e758886aad4"
import hashlib
if hashlib.sha256(configured.encode()).hexdigest() != expected_sha:
    raise SystemExit("official Configured with line changed")
argv = shlex.split(lines[0][len("Configured with: "):], posix=True)
expected = "/Users/mrs/Work/riscv-none-elf-gcc-xpack.git/build/darwin-arm64/sources/gcc-12.2.0/configure"
if not argv or argv[0] != expected:
    raise SystemExit(f"unexpected configure path: {argv[0] if argv else '<empty>'}")
pathlib.Path(argv_log).write_text(json.dumps(argv, ensure_ascii=False, indent=2) + "\n")
subprocess.run(argv, check=True)
PY
) > "$logs/gcc-configure.log" 2>&1
(
    cd -L "$gcc_build"
    make -j"$build_jobs" all-gcc MAKEINFO=/usr/bin/true
) > "$logs/gcc-all-gcc.log" 2>&1
(
    cd -L "$gcc_build"
    make install-gcc MAKEINFO=/usr/bin/true
) > "$logs/gcc-install-gcc.log" 2>&1

inject_sysroot
inject_gcc_payload

verify_pair() {
    local source_file=$1
    local output_file=$2
    local label=$3
    local source_sha output_sha
    [ -f "$source_file" ] || die "missing official injected file: $source_file"
    [ -f "$output_file" ] || die "missing output injected file: $output_file"
    source_sha=$(shasum -a 256 "$source_file" | awk '{print $1}')
    output_sha=$(shasum -a 256 "$output_file" | awk '{print $1}')
    [ "$source_sha" = "$output_sha" ] || die "injection mismatch: $label"
    printf '%s\t%s\t%s\n' "$label" "$source_sha" "$output_sha" \
        >> "$logs/injection-samples.tsv"
}

: > "$logs/injection-samples.tsv"
verify_pair \
    "$official_root/$target/include/stdio.h" \
    "$application/$target/include/stdio.h" target-stdio
verify_pair \
    "$official_root/$target/lib/libc.a" \
    "$application/$target/lib/libc.a" target-libc
verify_pair \
    "$official_root/$target/lib/rv32imac_xw/ilp32/libc.a" \
    "$application/$target/lib/rv32imac_xw/ilp32/libc.a" xw-libc
verify_pair \
    "$official_root/lib/gcc/$target/$gcc_version/libgcc.a" \
    "$application/lib/gcc/$target/$gcc_version/libgcc.a" target-libgcc
verify_pair \
    "$official_root/lib/gcc/$target/$gcc_version/rv32imac_xw/ilp32/libgcc.a" \
    "$application/lib/gcc/$target/$gcc_version/rv32imac_xw/ilp32/libgcc.a" xw-libgcc
verify_pair \
    "$official_root/lib/gcc/$target/$gcc_version/picolibc.specs" \
    "$application/lib/gcc/$target/$gcc_version/picolibc.specs" picolibc-specs

[ -x "$application/bin/$target-gcc" ] || die "installed GCC driver is missing"
[ -x "$application/bin/$target-as" ] || die "installed assembler is missing"
[ -x "$application/bin/$target-ld" ] || die "installed linker is missing"
[ -x "$application/libexec/gcc/$target/$gcc_version/cc1" ] || die "installed cc1 is missing"

printf 'project_root=%s\n' "$project_root"
printf 'literal_project=%s\n' "$literal_project"
printf 'gcc_head=%s\n' "$(git -C "$gcc_source" rev-parse HEAD)"
printf 'binutils_head=%s\n' "$(git -C "$binutils_source" rev-parse HEAD)"
printf 'SOURCE_DATE_EPOCH=%s\n' "$SOURCE_DATE_EPOCH"
printf 'multilib_sha256=%s\n' "$multilib_sha"
printf 'build_jobs=%s\n' "$build_jobs"
printf 'install_files=%s\n' "$(find -L "$application" -type f | wc -l | tr -d '[:space:]')"
du -sh "$physical_platform/application"
printf 'compiler=%s\n' "$physical_platform/application/bin/$target-gcc"
