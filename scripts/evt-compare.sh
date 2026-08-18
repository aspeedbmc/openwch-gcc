#!/usr/bin/env bash
# Rebuild EVT projects and compare every product with a golden manifest.
# Usage: scripts/evt-compare.sh <version> <toolchain-root-or-gcc-path>
# The second argument accepts both spellings used by the phase-1 prompt.

set -euo pipefail

export LC_ALL=C
export SOURCE_DATE_EPOCH=1767225600

usage() {
    printf 'usage: %s <version> <toolchain-root-or-gcc-path>\n' "${0##*/}" >&2
}

die() {
    printf 'evt-compare.sh: %s\n' "$*" >&2
    exit 2
}

if [ "$#" -ne 2 ]; then
    usage
    exit 2
fi

version=$1
toolchain_argument=$2
case "$version" in
    15.2.0|12.2.0|8.2.0) ;;
    *) die "unsupported version: $version" ;;
esac

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

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
projects_tsv="$script_dir/evt-projects.tsv"
evt_root="$repo_root/ref/wch-evt"
converter="$evt_root/tools/wvproj_to_make.py"
golden_root="$repo_root/tmp/golden"
version_root="$golden_root/$version"
neutral_root="$golden_root/toolchain-current"
manifest="$repo_root/analysis/golden/$version-$platform.tsv"
major=${version%%.*}

[ -f "$projects_tsv" ] || die "missing project table: $projects_tsv"
[ -f "$converter" ] || die "missing converter: $converter"
[ -f "$manifest" ] || die "missing golden manifest: $manifest"

compiler_name=
if [ -d "$toolchain_argument" ]; then
    toolchain_root=$(CDPATH= cd -- "$toolchain_argument" && pwd -P)
    compiler_candidates=("$toolchain_root"/bin/*-gcc)
    if [ "${#compiler_candidates[@]}" -ne 1 ] || [ ! -x "${compiler_candidates[0]}" ]; then
        die "expected exactly one executable *-gcc in $toolchain_root/bin"
    fi
    compiler_name=${compiler_candidates[0]##*/}
elif [ -f "$toolchain_argument" ] && [ -x "$toolchain_argument" ]; then
    compiler_dir=$(CDPATH= cd -- "$(dirname -- "$toolchain_argument")" && pwd -P)
    compiler_name=$(basename -- "$toolchain_argument")
    case "$compiler_name" in
        *-gcc) ;;
        *) die "compiler path must end in -gcc: $toolchain_argument" ;;
    esac
    [ "${compiler_dir##*/}" = bin ] || die "compiler must be inside a toolchain bin directory"
    toolchain_root=$(CDPATH= cd -- "$compiler_dir/.." && pwd -P)
else
    die "toolchain argument is neither a directory nor an executable file: $toolchain_argument"
fi

case "$toolchain_root" in
    "$repo_root"/*) ;;
    *) die "toolchain must be inside the repository: $toolchain_root" ;;
esac

cross_prefix=${compiler_name%gcc}
real_compiler="$toolchain_root/bin/$compiler_name"
real_objcopy="$toolchain_root/bin/${cross_prefix}objcopy"
[ -x "$real_compiler" ] || die "compiler is not executable: $real_compiler"
[ -x "$real_objcopy" ] || die "objcopy is not executable: $real_objcopy"

mkdir -p "$golden_root" "$version_root"
if [ -e "$neutral_root" ] && [ ! -L "$neutral_root" ]; then
    die "refusing to replace non-symlink path: $neutral_root"
fi
# The neutral symlink is shared state; remember where it pointed so cleanup
# can restore it even when the run aborts mid-way.
neutral_previous=$(readlink "$neutral_root" 2>/dev/null || true)
ln -sfn "$toolchain_root" "$neutral_root"
neutral_compiler="$neutral_root/bin/$compiler_name"
neutral_objcopy="$neutral_root/bin/${cross_prefix}objcopy"

temporary_dir=$(mktemp -d "$golden_root/.evt-compare.$version.XXXXXX")
cleanup() {
    rm -rf -- "$temporary_dir"
    if [ -n "${neutral_previous:-}" ]; then
        ln -sfn "$neutral_previous" "$neutral_root"
    fi
}
trap cleanup EXIT

clear_work_directory() {
    local directory=$1
    case "$directory" in
        "$version_root"/*/work) ;;
        *) die "refusing to clear unexpected work directory: $directory" ;;
    esac
    mkdir -p "$directory"
    find "$directory" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
}

show_failure_excerpt() {
    local slug=$1
    local stage=$2
    local log_file=$3
    local excerpt="$temporary_dir/$slug-$stage-excerpt.txt"
    printf '%s\tFAIL\t%s\tlog=%s\n' "$slug" "$stage" "$log_file" >&2
    tail -n 50 "$log_file" > "$excerpt" 2>/dev/null || true
    head -c 65536 "$excerpt" >&2
    printf '\n' >&2
}

write_harness_makefile() {
    local work=$1
    printf '%s\n' \
        'override CFLAGS += -fdebug-prefix-map=$(DEBUG_PREFIX_FROM)=$(DEBUG_PREFIX_TO)' \
        'override ASFLAGS += -fdebug-prefix-map=$(DEBUG_PREFIX_FROM)=$(DEBUG_PREFIX_TO)' \
        > "$work/harness.mk"
}

build_project() {
    local work=$1
    local log_file=$2
    if ! make -C "$work" -f Makefile -f harness.mk -j2 \
        COMPILER_PATH="$neutral_compiler" \
        TOOLCHAIN_BIN="$neutral_root/bin" \
        CROSS_PREFIX="$cross_prefix" \
        DEBUG_PREFIX_FROM="$toolchain_root" \
        DEBUG_PREFIX_TO="$neutral_root" \
        all > "$log_file" 2>&1; then
        return 1
    fi

    local elf_candidates=("$work"/obj/*.elf)
    if [ "${#elf_candidates[@]}" -ne 1 ] || [ ! -f "${elf_candidates[0]}" ]; then
        printf 'expected exactly one ELF below %s/obj\n' "$work" >> "$log_file"
        return 1
    fi
    if ! "$neutral_objcopy" -O binary "${elf_candidates[0]}" "${elf_candidates[0]%.elf}.bin" >> "$log_file" 2>&1; then
        return 1
    fi
}

sha256_file() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        die "neither shasum nor sha256sum is available"
    fi
}

file_size() {
    wc -c < "$1" | tr -d '[:space:]'
}

project_path_for_slug() {
    local wanted=$1
    awk -F '\t' -v slug="$wanted" 'NR > 1 && $1 == slug { print $2; found=1 } END { if (!found) exit 1 }' "$projects_tsv"
}

expected_gate_total=$(awk -F '\t' '$1 !~ /^#/ && $1 != "slug" && $3 == "gate" { count++ } END { print count+0 }' "$manifest")
[ "$expected_gate_total" -gt 0 ] || die "manifest has no gate rows: $manifest"

manifest_slugs="$temporary_dir/manifest-slugs.txt"
awk -F '\t' '$1 !~ /^#/ && $1 != "slug" && !seen[$1]++ { print $1 }' "$manifest" > "$manifest_slugs"
[ -s "$manifest_slugs" ] || die "manifest has no project rows: $manifest"

# Project-level concurrency.  Projects are built in parallel with a fixed pool
# of workers; each project still builds with make -j2 internally.  Nothing
# about conversion, comparison or artifact classification changes: a worker
# writes its rows and its four counters to per-slug files, and the parent
# concatenates them in manifest order afterwards, so the emitted table and the
# summary are the same as a serial run.
workers=${EVT_COMPARE_WORKERS:-16}
case "$workers" in
    ''|*[!0-9]*|0) die "EVT_COMPARE_WORKERS must be a positive integer" ;;
esac

# Slug resolution is a pure table lookup, so it is done up front rather than
# inside a worker: a mismatch between the manifest and the project table is a
# harness misconfiguration and must still abort the whole run, which a
# background subshell cannot do.
while IFS= read -r slug; do
    [ -n "$slug" ] || continue
    if ! project_path=$(project_path_for_slug "$slug"); then
        die "manifest contains unknown slug: $slug"
    fi
    project_dir="$evt_root/$project_path"
    wvproj_candidates=("$project_dir"/*.wvproj)
    if [ "${#wvproj_candidates[@]}" -ne 1 ] || [ ! -f "${wvproj_candidates[0]}" ]; then
        die "expected exactly one .wvproj for $slug"
    fi
    printf '%s\n' "${wvproj_candidates[0]}" > "$temporary_dir/$slug.wvproj"
done < "$manifest_slugs"

process_slug() {
    local slug=$1
    local gate_pass=0
    local gate_fail=0
    local aux_match=0
    local aux_diff=0
    local wvproj
    wvproj=$(cat "$temporary_dir/$slug.wvproj")

    local work="$version_root/$slug/work"
    local logs="$version_root/$slug/logs"
    mkdir -p "$work" "$logs"
    clear_work_directory "$work"
    local convert_log="$logs/compare-convert.log"
    local build_log="$logs/compare-build.log"
    local build_ok=yes

    if ! python3 "$converter" "$wvproj" --output "$work" \
        --compiler-path "$neutral_compiler" --gcc-major "$major" --quiet \
        > "$convert_log" 2>&1; then
        show_failure_excerpt "$slug" compare-convert "$convert_log"
        build_ok=no
    else
        write_harness_makefile "$work"
        if ! build_project "$work" "$build_log"; then
            show_failure_excerpt "$slug" compare-build "$build_log"
            build_ok=no
        fi
    fi

    local expected_files="$temporary_dir/$slug-expected.files"
    local actual_files="$temporary_dir/$slug-actual.files"
    awk -F '\t' -v slug="$slug" '$1 == slug { print $2 }' "$manifest" | sort > "$expected_files"
    if [ "$build_ok" = yes ]; then
        (cd "$work" && find obj -type f -print | sort) > "$actual_files"
    else
        : > "$actual_files"
    fi

    local row_slug artifact class expected_size expected_hash actual actual_size actual_hash
    while IFS=$'\t' read -r row_slug artifact class expected_size expected_hash; do
        [ "$row_slug" = "$slug" ] || continue
        actual="$work/$artifact"
        if [ "$build_ok" != yes ] || [ ! -f "$actual" ]; then
            if [ "$class" = gate ]; then
                printf '%s\t%s\t%s\tFAIL\tmissing or build failed\n' "$slug" "$artifact" "$class"
                gate_fail=$((gate_fail + 1))
            else
                printf '%s\t%s\t%s\tAUX-MISSING\tmissing or build failed\n' "$slug" "$artifact" "$class"
                aux_diff=$((aux_diff + 1))
            fi
            continue
        fi

        actual_size=$(file_size "$actual")
        actual_hash=$(sha256_file "$actual")
        if [ "$actual_size" = "$expected_size" ] && [ "$actual_hash" = "$expected_hash" ]; then
            if [ "$class" = gate ]; then
                printf '%s\t%s\t%s\tPASS\tsha256=%s\n' "$slug" "$artifact" "$class" "$actual_hash"
                gate_pass=$((gate_pass + 1))
            else
                printf '%s\t%s\t%s\tAUX-MATCH\tsha256=%s\n' "$slug" "$artifact" "$class" "$actual_hash"
                aux_match=$((aux_match + 1))
            fi
        else
            if [ "$class" = gate ]; then
                printf '%s\t%s\t%s\tFAIL\texpected_size=%s actual_size=%s expected_sha256=%s actual_sha256=%s\n' \
                    "$slug" "$artifact" "$class" "$expected_size" "$actual_size" "$expected_hash" "$actual_hash"
                gate_fail=$((gate_fail + 1))
            else
                printf '%s\t%s\t%s\tAUX-DIFF\texpected_size=%s actual_size=%s expected_sha256=%s actual_sha256=%s\n' \
                    "$slug" "$artifact" "$class" "$expected_size" "$actual_size" "$expected_hash" "$actual_hash"
                aux_diff=$((aux_diff + 1))
            fi
        fi
    done < "$manifest"

    local extra_files="$temporary_dir/$slug-extra.files"
    comm -13 "$expected_files" "$actual_files" > "$extra_files"
    while IFS= read -r artifact; do
        [ -n "$artifact" ] || continue
        case "$artifact" in
            *.o|*.elf|*.bin)
                printf '%s\t%s\tgate\tFAIL\textra gate artifact\n' "$slug" "$artifact"
                gate_fail=$((gate_fail + 1))
                ;;
            *)
                printf '%s\t%s\taux\tAUX-EXTRA\textra auxiliary artifact\n' "$slug" "$artifact"
                aux_diff=$((aux_diff + 1))
                ;;
        esac
    done < "$extra_files"

    printf '%s %s %s %s\n' "$gate_pass" "$gate_fail" "$aux_match" "$aux_diff" \
        > "$temporary_dir/$slug.counts"
}

# Fan the projects out over the worker pool.  bash 3.2 has no "wait -n", so a
# full pool is drained by waiting on its oldest member; with fewer projects
# than workers every project simply starts at once.
running_pids=()
while IFS= read -r slug; do
    [ -n "$slug" ] || continue
    if [ "${#running_pids[@]}" -ge "$workers" ]; then
        wait "${running_pids[0]}" || true
        running_pids=(${running_pids[@]:1})
    fi
    process_slug "$slug" > "$temporary_dir/$slug.rows" &
    running_pids+=($!)
done < "$manifest_slugs"
for pid in ${running_pids[@]+"${running_pids[@]}"}; do
    wait "$pid" || true
done

# Emit in manifest order, so the table is identical to a serial run.
printf 'slug\tartifact\tclass\tstatus\tdetail\n'
gate_pass=0
gate_fail=0
aux_match=0
aux_diff=0
while IFS= read -r slug; do
    [ -n "$slug" ] || continue
    [ -f "$temporary_dir/$slug.counts" ] || die "worker produced no counters for $slug"
    cat "$temporary_dir/$slug.rows"
    read -r slug_gate_pass slug_gate_fail slug_aux_match slug_aux_diff \
        < "$temporary_dir/$slug.counts"
    gate_pass=$((gate_pass + slug_gate_pass))
    gate_fail=$((gate_fail + slug_gate_fail))
    aux_match=$((aux_match + slug_aux_match))
    aux_diff=$((aux_diff + slug_aux_diff))
done < "$manifest_slugs"

printf 'SUMMARY\tgate_pass=%s\tgate_total=%s\tgate_fail=%s\taux_match=%s\taux_diff=%s\n' \
    "$gate_pass" "$expected_gate_total" "$gate_fail" "$aux_match" "$aux_diff"

if [ "$gate_fail" -ne 0 ] || [ "$gate_pass" -ne "$expected_gate_total" ]; then
    exit 1
fi
