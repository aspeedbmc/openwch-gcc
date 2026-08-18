#!/usr/bin/env bash
# Build the GCC 8.2.0/binutils 2.32 compiler-only toolchain at the literal
# WCH xPack paths (x86_64 host under Rosetta, matching the official
# --build/--host=x86_64-apple-darwin17.7.0 configure literal) and inject the
# official target libraries/sysroot bytewise.
# Usage: scripts/build-toolchain-8.2.0.sh
# Set BUILD_JOBS to override parallelism; set CLEAN_HOST_DEPS=1 to rebuild the
# pinned GMP/MPFR/MPC/ISL/zlib host dependency prefix.
# The pre-build patch-series check works on a fresh replay tree as well as on
# the working mirror: it anchors on content (upstream fork tag tree, frozen
# patch tree, stable patch IDs), and the commit-anchored From guard runs only
# where the exporting commit object exists.  See the comment at that check.
#
# Spec sources:
# - gcc configure argv: extracted live from the official gcc -v and replayed
#   verbatim (sha256-pinned below).
# - binutils configure argv: xPack v10.2.0-1.2 framework template
#   (common-apps-functions-source.sh, binutils section) with the literals
#   observed on the official install; binutils does not embed its argv, so its
#   acceptance hangs on observable literals and artifact bytes only.
# - Layout: /Users/wch/Work/riscv-none-embed-gcc-10.2.0-1.2/darwin-x64/
#   {sources,build,install} per the official configure/prefix literals.

set -euo pipefail
umask 022

# The official toolchain is x86_64; the configure literal forces an x86_64
# host build.  Re-exec under Rosetta when invoked from an arm64 shell so that
# uname/configure runtime checks see x86_64.  Note: clang still defaults to
# arm64 code generation even inside an arch -x86_64 shell (measured), so the
# -arch flag must stay in CC/CXX regardless.
if [ "$(uname -m)" != "x86_64" ]; then
    exec arch -x86_64 /bin/bash "$0" "$@"
fi

export LC_ALL=C
export TZ=UTC
export SOURCE_DATE_EPOCH=1767225600
export ZERO_AR_DATE=1
export CC='/usr/bin/clang -arch x86_64'
export CXX='/usr/bin/clang++ -arch x86_64'
export MACOSX_DEPLOYMENT_TARGET=10.13
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
export MAKEINFO=/usr/bin/true
unset CFLAGS CXXFLAGS CPPFLAGS LDFLAGS LIBRARY_PATH CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH
unset AR AS LD NM RANLIB SDKROOT GCC_EXEC_PREFIX COMPILER_PATH

die() {
    printf 'build-toolchain-8.2.0.sh: %s\n' "$*" >&2
    exit 2
}

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
script_self="$script_dir/$(basename -- "${BASH_SOURCE[0]}")"
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
project_root="$repo_root/tmp/toolchain_8.2.0/work"
downloads="$repo_root/tmp/toolchain_8.2.0/downloads"
[ -d "$project_root" ] || die "expected project root does not exist: $project_root"

literal_project=/Users/wch/Work/riscv-none-embed-gcc-10.2.0-1.2
[ -L "$literal_project" ] || die "required literal symlink is missing: $literal_project"
link_target=$(readlink "$literal_project")
[ "$link_target" = "$project_root" ] || \
    die "literal symlink mismatch: expected $project_root, got $link_target"

literal_platform="$literal_project/darwin-x64"
physical_platform="$project_root/darwin-x64"
host_triplet=x86_64-apple-darwin17.7.0
sources="$literal_platform/sources"
build_root="$literal_platform/build"
application="$literal_platform/install/riscv-none-embed-gcc"
deps_install="$literal_platform/install/openwch-host-deps"
logs="$literal_platform/logs/openwch-phase6"
host_deps_logs="$literal_platform/logs/openwch-phase6-host-deps"
build_lock="$literal_platform/.openwch-phase6-build.lock"

gcc_source="$sources/riscv-gcc-10.2.0-1.1"
binutils_source="$sources/riscv-binutils-2.32"
gcc_build="$build_root/riscv-none-embed-gcc-8.2.0-final"
binutils_build="$build_root/riscv-none-embed-binutils-2.32"
official_root="$repo_root/ref/gcc/darwin-arm64/8.2.0"
official_gcc="$official_root/bin/riscv-none-embed-gcc"
target=riscv-none-embed
gcc_version=8.2.0
branding='xPack GNU RISC-V Embedded GCC x86_64'
bugurl=https://github.com/sifive/freedom-tools/issues/
build_jobs=${BUILD_JOBS:-16}
clean_host_deps=${CLEAN_HOST_DEPS:-0}
# The 2018/2019-era sources predate clang's promotion of K&R-isms to hard
# errors (clang 16+): implicit function declarations, implicit int, int/ptr
# conversions, mismatched function pointer types.  Downgrade those back to
# warnings at the build-flag level so the sources stay pristine; none of
# these flags is observable in any gate artifact (host CFLAGS are not part
# of the embedded configure argv).
host_cflags='-O2 -mmacosx-version-min=10.13 -Wno-implicit-function-declaration -Wno-implicit-int -Wno-int-conversion -Wno-incompatible-function-pointer-types'

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

mkdir -p "$literal_platform"
if ! mkdir "$build_lock" 2>/dev/null; then
    die "another Phase 6 build holds $build_lock"
fi
temporary_indexes=()
cleanup() {
    local path
    for path in ${temporary_indexes+"${temporary_indexes[@]}"}; do
        rm -f -- "$path"
    done
    rmdir "$build_lock" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Verified source anchors: xpack-dev-tools fork tag v8.2.0-3.1 (tag object and
# branch commit coincide; see evidence/s2/source-acquisition.md).
gcc_base=0c7a874f0b6f452eeafde57731646e5f460187e4
binutils_base=82b51c7b5087ddb77988287cd7a2dd8921331bfd
gcc_base_tree=19b6cd9577b8a9df3c24e07728911c2a7286591e
binutils_base_tree=40c5ff7d7a79893068eeab936325469807004069

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
    die "GCC HEAD does not descend from the verified fork tag"
verify_source_base "$binutils_source" "$binutils_base" "$binutils_base_tree" || \
    die "binutils HEAD does not descend from the verified fork tag"
[ -z "$(git -C "$gcc_source" status --porcelain=v1)" ] || die "GCC source tree is not clean"
[ -z "$(git -C "$binutils_source" status --porcelain=v1)" ] || die "binutils source tree is not clean"

# Pre-build verification that what is about to be compiled is exactly the
# ordered public patch series in patches/8.2.0/ and nothing else.  Modelled on
# build-toolchain-12.2.0.sh:134-241, with one structural difference: 12.2.0
# keeps a series file per component, while 8.2.0 keeps ONE top-level series
# whose entries carry the component as a path prefix (gcc/, host/, binutils/).
# The host/ slice is a GCC-tree patch kept out of gcc/ so the behaviour surface
# under audit stays exactly the patches that move artifact bytes, which is why
# gcc/ has a visible gap at 0002.  Both gcc/ and host/ therefore route to the
# GCC tree; only binutils/ routes to the binutils tree.  One pass over the
# series feeds two indexes so the interleaved order is preserved per tree.
patch_root="$repo_root/patches/8.2.0"
gcc_frozen_patch_tree=97b81fa8f52fa7037045f428f41e37099ba16fdf
binutils_frozen_patch_tree=8d0d7da3c3b3376d07ef0f76f0f00b6b913dcf40
expected_total_patches=7
expected_gcc_patches=5
expected_binutils_patches=2

[ -f "$patch_root/series" ] || die "missing patch series: $patch_root/series"
[ -f "$patch_root/patch-id.tsv" ] || die "missing stable patch-ID ledger"
# The reads below are positional, so pin the whole header line rather than the
# column count: a future layout change then fails loudly here instead of
# silently selecting the wrong field.
[ "$(head -n 1 "$patch_root/patch-id.tsv")" = \
    "$(printf 'component\tpatch\tstable_patch_id\tsource_commit')" ] || \
    die "unexpected patch-id.tsv schema"

verify_patch_series() {
    local gcc_index binutils_index gcc_added binutils_added
    local entry component patch_name patch_path source_tree index_file
    local expected_patch_id actual_patch_id
    local expected_source_commit actual_source_commit
    local total_count gcc_count binutils_count

    gcc_index=$(mktemp "$repo_root/tmp/.openwch-phase6-index.XXXXXX")
    binutils_index=$(mktemp "$repo_root/tmp/.openwch-phase6-index.XXXXXX")
    gcc_added=$(mktemp "$repo_root/tmp/.openwch-phase6-index.XXXXXX")
    binutils_added=$(mktemp "$repo_root/tmp/.openwch-phase6-index.XXXXXX")
    temporary_indexes+=("$gcc_index" "$binutils_index" "$gcc_added" "$binutils_added")
    rm -f -- "$gcc_index" "$binutils_index"

    GIT_INDEX_FILE="$gcc_index" git -C "$gcc_source" read-tree "$gcc_base"
    GIT_INDEX_FILE="$binutils_index" git -C "$binutils_source" read-tree "$binutils_base"

    total_count=0
    gcc_count=0
    binutils_count=0
    while IFS= read -r entry || [ -n "$entry" ]; do
        [ -n "$entry" ] || die "blank entry in patch series: $patch_root/series"
        # Entries here legitimately contain one slash; reject anything that
        # could escape the patch root or hide a second level.
        case "$entry" in
            */*/*|.*|/*|*..*) die "unsafe patch-series entry: $entry" ;;
        esac
        component=${entry%%/*}
        patch_name=${entry#*/}
        case "$component" in
            gcc|host)  source_tree="$gcc_source";      index_file="$gcc_index" ;;
            binutils)  source_tree="$binutils_source"; index_file="$binutils_index" ;;
            *) die "unknown component in patch series: $entry" ;;
        esac
        patch_path="$patch_root/$entry"
        [ -f "$patch_path" ] || die "missing patch: $patch_path"

        expected_patch_id=$(awk -F '\t' -v component="$component" -v patch="$patch_name" \
            '$1 == component && $2 == patch { print $3 }' "$patch_root/patch-id.tsv")
        [ -n "$expected_patch_id" ] || \
            die "stable patch ID is missing for $entry"
        actual_patch_id=$(git -C "$source_tree" patch-id --stable < "$patch_path" | \
            awk '{print $1}')
        [ "$actual_patch_id" = "$expected_patch_id" ] || \
            die "stable patch ID mismatch for $entry"

        # Doubles as the build-time guard for the From convention: the mbox
        # From line, the ledger's source_commit column and the mirror history
        # must agree, so a reworded commit that was never re-exported (or a
        # re-export that never updated the ledger) fails here.
        expected_source_commit=$(awk -F '\t' -v component="$component" -v patch="$patch_name" \
            '$1 == component && $2 == patch { print $4 }' "$patch_root/patch-id.tsv")
        [ -n "$expected_source_commit" ] || \
            die "source commit is missing for $entry"
        actual_source_commit=$(awk 'NR == 1 && $1 == "From" { print $2; exit }' "$patch_path")
        [ "$actual_source_commit" = "$expected_source_commit" ] || \
            die "source commit mismatch for $entry"
        # Dual anchor: the equality above is the content anchor and holds in any
        # tree, while reachability is the working-mirror guard and is only
        # decidable where the exporting commit object still exists.  A fresh
        # replay (upstream clone + git am) has no such object, so disclose the
        # skipped guard on one line and keep the content anchors as the proof.
        if git -C "$source_tree" cat-file -e "$actual_source_commit^{commit}" 2>/dev/null; then
            git -C "$source_tree" merge-base --is-ancestor "$actual_source_commit" HEAD || \
                die "source commit is not reachable from HEAD: $entry"
        else
            printf 'from_commit_unavailable=%s\n' "$entry"
        fi
        printf 'patch_id=PASS entry=%s id=%s from=%s\n' \
            "$entry" "$actual_patch_id" "$actual_source_commit"

        GIT_INDEX_FILE="$index_file" git -C "$source_tree" apply --cached --check "$patch_path"
        GIT_INDEX_FILE="$index_file" git -C "$source_tree" apply --cached "$patch_path"
        total_count=$((total_count + 1))
        case "$component" in
            binutils) binutils_count=$((binutils_count + 1)) ;;
            *)        gcc_count=$((gcc_count + 1)) ;;
        esac
    done < "$patch_root/series"

    [ "$total_count" -eq "$expected_total_patches" ] || \
        die "series has $total_count patches; expected $expected_total_patches"
    [ "$gcc_count" -eq "$expected_gcc_patches" ] || \
        die "series routes $gcc_count patches to the GCC tree; expected $expected_gcc_patches"
    [ "$binutils_count" -eq "$expected_binutils_patches" ] || \
        die "series routes $binutils_count patches to the binutils tree; expected $expected_binutils_patches"

    verify_component_tree gcc "$gcc_source" "$gcc_base" "$gcc_index" "$gcc_added" \
        "$gcc_frozen_patch_tree" "$gcc_count"
    verify_component_tree binutils "$binutils_source" "$binutils_base" "$binutils_index" \
        "$binutils_added" "$binutils_frozen_patch_tree" "$binutils_count"

    rm -f -- "$gcc_index" "$binutils_index" "$gcc_added" "$binutils_added"
}

verify_component_tree() {
    local component=$1 source_tree=$2 expected_head=$3 expected_index=$4
    local added_paths=$5 frozen_patch_tree=$6 patch_count=$7
    local expected_tree_id actual_tree_id actual_index

    expected_tree_id=$(GIT_INDEX_FILE="$expected_index" git -C "$source_tree" write-tree)
    [ "$expected_tree_id" = "$frozen_patch_tree" ] || \
        die "$component public patch series does not produce the frozen patch tree"

    actual_index=$(mktemp "$repo_root/tmp/.openwch-phase6-index.XXXXXX")
    temporary_indexes+=("$actual_index")
    rm -f -- "$actual_index"
    GIT_INDEX_FILE="$actual_index" git -C "$source_tree" read-tree "$expected_head"
    GIT_INDEX_FILE="$actual_index" git -C "$source_tree" add -u -- .
    # git add -u deliberately omits files introduced by a patch.  Add only the
    # paths the expected patched index classifies as new; unrelated untracked
    # prerequisite archives/directories stay outside the check.
    GIT_INDEX_FILE="$expected_index" git -C "$source_tree" \
        diff --cached --name-only --diff-filter=A -z "$expected_head" > "$added_paths"
    if [ -s "$added_paths" ]; then
        GIT_INDEX_FILE="$actual_index" git -C "$source_tree" add \
            --pathspec-from-file="$added_paths" --pathspec-file-nul
    fi
    actual_tree_id=$(GIT_INDEX_FILE="$actual_index" git -C "$source_tree" write-tree)
    [ "$actual_tree_id" = "$expected_tree_id" ] || \
        die "$component tracked worktree is not exactly the ordered public patch series"

    rm -f -- "$actual_index"
    printf 'series=PASS component=%s patches=%s tree=%s\n' \
        "$component" "$patch_count" "$actual_tree_id"
}

verify_patch_series

for source_dir in \
    gmp-6.2.1 mpfr-4.1.0 mpc-1.2.1 isl-0.18 zlib-1.2.12; do
    if [ ! -d "$sources/$source_dir" ]; then
        archive=$(ls "$downloads/$source_dir".tar.* 2>/dev/null | head -n 1)
        [ -n "$archive" ] || die "missing host dependency archive: $source_dir"
        tar -xf "$archive" -C "$sources"
    fi
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

verify_archive gmp-6.2.1.tar.xz \
    fd4829912cddd12f84181c3451cc752be224643e87fac497b69edddadc49b4f2
verify_archive mpfr-4.1.0.tar.xz \
    0c98a3f1732ff6ca4ea690552079da9c597872d30e96ec28414ee23c95558a7f
verify_archive mpc-1.2.1.tar.gz \
    17503d2c395dfcf106b622dc142683c1199431d095367c6aacba6eec30340459
verify_archive isl-0.18.tar.bz2 \
    6b8b0fd7f81d0a957beb3679c81bbb34ccc7568d5682844d8924424a0dadcb1b
verify_archive zlib-1.2.12.tar.gz \
    91844808532e5ce316b3c010929493c0244f3d37593afd6de04f71821d5136d9

safe_remove() {
    local path=$1
    case "$path" in
        "$gcc_build"|"$binutils_build"|"$application"|"$logs"|\
        "$build_root/gmp-6.2.1"|"$build_root/mpfr-4.1.0"|\
        "$build_root/mpc-1.2.1"|"$build_root/isl-0.18"|\
        "$build_root/zlib-1.2.12"|\
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
    /bin/cp -cR "$source_path" "$destination" 2>/dev/null || \
        /bin/cp -R "$source_path" "$destination"
}

safe_remove "$gcc_build"
safe_remove "$binutils_build"
safe_remove "$application"
safe_remove "$logs"
mkdir -p "$build_root" "$logs"

deps_marker="$deps_install/.openwch-phase6-host-deps"
deps_marker_payload=$(printf '%s\n' \
    'schema=1' \
    'SOURCE_DATE_EPOCH=1767225600' \
    'host_triplet=x86_64-apple-darwin17.7.0' \
    'deployment_target=10.13' \
    'libraries=gmp-6.2.1,mpfr-4.1.0,mpc-1.2.1,isl-0.18,zlib-1.2.12' \
    'mode=static')
if [ "$clean_host_deps" = 0 ] && [ -f "$deps_marker" ] && \
    [ "$(cat "$deps_marker")" != "$deps_marker_payload" ]; then
    die "host dependency marker does not match the pinned build; rerun with CLEAN_HOST_DEPS=1"
fi
if [ "$clean_host_deps" = 1 ] || [ ! -f "$deps_marker" ]; then
    for dep_path in \
        "$build_root/gmp-6.2.1" "$build_root/mpfr-4.1.0" \
        "$build_root/mpc-1.2.1" "$build_root/isl-0.18" \
        "$build_root/zlib-1.2.12" \
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

    mkdir -p "$build_root/isl-0.18"
    (
        cd -L "$build_root/isl-0.18"
        CPPFLAGS="$dep_cppflags" LDFLAGS="$dep_ldflags" \
            "$sources/isl-0.18/configure" \
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
        # zlib 1.2.12's Darwin configure is not a reliable VPATH build; copy
        # the host-only source into the build directory first (xPack helper
        # layout).  Clang predefines TARGET_OS_MAC on modern Darwin; zlib
        # 1.2.12 mistakes it for classic Mac OS and masks fdopen.
        /bin/cp -cR "$sources/zlib-1.2.12/." . 2>/dev/null || \
            /bin/cp -R "$sources/zlib-1.2.12/." .
        CC='/usr/bin/clang -arch x86_64' CFLAGS="$host_cflags -UTARGET_OS_MAC" \
            ./configure --prefix="$deps_install" --static
        make -j"$build_jobs"
        make install
    ) > "$host_deps_logs/host-zlib.log" 2>&1

    for dep_file in \
        include/gmp.h include/mpfr.h include/mpc.h include/isl/ctx.h \
        include/zlib.h lib/libgmp.a lib/libmpfr.a lib/libmpc.a \
        lib/libisl.a lib/libz.a; do
        [ -f "$deps_install/$dep_file" ] || die "host dependency install is incomplete: $dep_file"
    done
    printf '%s\n' "$deps_marker_payload" > "$deps_marker"
fi

dep_cppflags="-I$deps_install/include"
dep_ldflags="-L$deps_install/lib"
export CPPFLAGS="$dep_cppflags"
export CFLAGS="$host_cflags"
export CXXFLAGS="$host_cflags"
export LDFLAGS="$dep_ldflags -mmacosx-version-min=10.13"
mkdir -p "$binutils_build" "$application"
# The official 8.2.0 was built on darwin17.7.0 (macOS 10.13), where libtool's
# darwin branch (libtool.m4:1741-1749) finds -ldl unusable, leaving
# lt_cv_dlopen_libs empty and bfd/Makefile.am's LIBDL empty.  Modern macOS
# SDKs alias libdl.tbd to libSystem.tbd, so -ldl links and libtool places it
# in libbfd.la's dependency_libs ahead of libiberty.a; being the whole of
# libSystem, it wins getopt_long_only/optind/optarg and libiberty's
# getopt.o/getopt1.o are never selected, degrading the tools'
# "unrecognized option" prefix from argv[0] verbatim to basename.  Pin the
# host probe result to reproduce the official link line.  Must be exported
# and visible to both configure and make (recursive sub-configures keep
# their own config.cache); unset after the binutils phase so the GCC phase
# (already zero-deviation) is untouched.
export ac_cv_lib_dl_dlopen=no
(
    cd -L "$binutils_build"
    "$binutils_source/configure" \
        --prefix="$application" \
        --infodir="$application/share/doc/info" \
        --mandir="$application/share/doc/man" \
        --htmldir="$application/share/doc/html" \
        --pdfdir="$application/share/doc/pdf" \
        --build="$host_triplet" \
        --host="$host_triplet" \
        --target="$target" \
        --with-pkgversion="$branding" \
        --with-bugurl="$bugurl" \
        --disable-nls \
        --disable-werror \
        --disable-sim \
        --disable-gdb \
        --enable-interwork \
        --enable-plugins \
        --disable-libdecnumber \
        --disable-libreadline \
        --with-sysroot="$application/$target" \
        --enable-build-warnings=no \
        --with-system-zlib
) > "$logs/binutils-configure.log" 2>&1
(
    cd -L "$binutils_build"
    make -j"$build_jobs" MAKEINFO=/usr/bin/true
) > "$logs/binutils-build.log" 2>&1
(
    cd -L "$binutils_build"
    make install MAKEINFO=/usr/bin/true
) > "$logs/binutils-install.log" 2>&1
unset ac_cv_lib_dl_dlopen

inject_sysroot() {
    local official_target="$official_root/$target"
    local output_target="$application/$target"
    local source_entry base

    safe_replace "$official_target/include" "$output_target/include" "$output_target"
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
            rv*|crtbegin.o|crtend.o|crti.o|crtn.o|libgcc.a|libgcov.a)
                safe_replace "$source_entry" "$output_gcc_lib/$base" "$output_gcc_lib"
                ;;
        esac
    done < <(find "$official_gcc_lib" -mindepth 1 -maxdepth 1 -print | sort)
}

inject_bfd_plugins() {
    # The official darwin 8.2.0 package ships lib/bfd-plugins/liblto_plugin.so
    # flattened from a symlink into a 59-byte text file (a WCH packaging
    # defect; 12.2.0 darwin and 15.2.0 linux carry real binaries there).  nm
    # and friends dlopen it and print a diagnostic; defect fidelity requires
    # shipping the same bytes, not a working plugin or a repaired symlink.
    safe_replace "$official_root/lib/bfd-plugins" \
        "$application/lib/bfd-plugins" "$application"
}

# The final GCC configure probes sysroot headers.  Install the official target
# headers and libraries before configure, then restore them after install-gcc
# so no compiler installation step can replace target payload.
inject_sysroot

export PATH="$application/bin:/usr/bin:/bin:/usr/sbin:/sbin"
mkdir -p "$gcc_build"
(
    cd -L "$gcc_build"
    /usr/bin/python3 - "$official_gcc" "$logs/wch-gcc-v.txt" \
            "$logs/gcc-configure-argv.json" <<'PY'
import hashlib
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
expected_sha = "35d6177c087b25191ad40378bb0e17b3ba621920344e397e37193f7d8f1ea153"
if hashlib.sha256(configured.encode()).hexdigest() != expected_sha:
    raise SystemExit("official Configured with line changed")
argv = shlex.split(lines[0][len("Configured with: "):], posix=True)
expected = "/Users/wch/Work/riscv-none-embed-gcc-10.2.0-1.2/darwin-x64/sources/riscv-gcc-10.2.0-1.1/configure"
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
inject_bfd_plugins

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
    "$official_root/$target/lib/rv32imacxw/ilp32/libc.a" \
    "$application/$target/lib/rv32imacxw/ilp32/libc.a" xw-libc
verify_pair \
    "$official_root/$target/lib/nano.specs" \
    "$application/$target/lib/nano.specs" nano-specs
verify_pair \
    "$official_root/lib/gcc/$target/$gcc_version/libgcc.a" \
    "$application/lib/gcc/$target/$gcc_version/libgcc.a" target-libgcc
verify_pair \
    "$official_root/lib/gcc/$target/$gcc_version/rv32imacxw/ilp32/libgcc.a" \
    "$application/lib/gcc/$target/$gcc_version/rv32imacxw/ilp32/libgcc.a" xw-libgcc
verify_pair \
    "$official_root/$target/lib/crt0.o" \
    "$application/$target/lib/crt0.o" target-crt0
verify_pair \
    "$official_root/lib/bfd-plugins/liblto_plugin.so" \
    "$application/lib/bfd-plugins/liblto_plugin.so" bfd-plugins-lto-stub

[ -x "$application/bin/$target-gcc" ] || die "installed GCC driver is missing"
[ -x "$application/bin/$target-as" ] || die "installed assembler is missing"
[ -x "$application/bin/$target-ld" ] || die "installed linker is missing"
[ -x "$application/libexec/gcc/$target/$gcc_version/cc1" ] || die "installed cc1 is missing"

printf 'project_root=%s\n' "$project_root"
printf 'literal_project=%s\n' "$literal_project"
printf 'host_arch=%s\n' "$(uname -m)"
printf 'gcc_head=%s\n' "$(git -C "$gcc_source" rev-parse HEAD)"
printf 'binutils_head=%s\n' "$(git -C "$binutils_source" rev-parse HEAD)"
printf 'SOURCE_DATE_EPOCH=%s\n' "$SOURCE_DATE_EPOCH"
printf 'script_sha256=%s\n' "$(shasum -a 256 "$script_self" | awk '{print $1}')"
printf 'build_jobs=%s\n' "$build_jobs"
printf 'install_files=%s\n' "$(find -L "$application" -type f | wc -l | tr -d '[:space:]')"
du -sh "$physical_platform/install/riscv-none-embed-gcc"
printf 'compiler=%s\n' "$physical_platform/install/riscv-none-embed-gcc/bin/$target-gcc"
