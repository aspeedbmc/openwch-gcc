#!/usr/bin/env bash
# Build deterministic EVT golden artifacts with an official WCH toolchain.
# Usage: scripts/evt-golden.sh <version>
# Supported: darwin-arm64 (15.2.0, 12.2.0 and 8.2.0), linux-amd64 (15.2.0).

set -euo pipefail

export LC_ALL=C
export SOURCE_DATE_EPOCH=1767225600

usage() {
    printf 'usage: %s <15.2.0|12.2.0|8.2.0>\n' "${0##*/}" >&2
}

die() {
    printf 'evt-golden.sh: %s\n' "$*" >&2
    exit 2
}

if [ "$#" -ne 1 ]; then
    usage
    exit 2
fi

version=$1
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

container_image=
if [ "$platform" = linux-amd64 ]; then
    container_image=${EVT_CONTAINER_IMAGE-}
    [ -n "$container_image" ] || \
        die "EVT_CONTAINER_IMAGE must identify the linux-amd64 container image"
    case "$container_image" in
        *$'\n'*|*$'\r'*) die "EVT_CONTAINER_IMAGE must be a single line" ;;
    esac
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd)
projects_tsv="$script_dir/evt-projects.tsv"
evt_root="$repo_root/ref/wch-evt"
converter="$evt_root/tools/wvproj_to_make.py"
toolchain_root="$repo_root/ref/gcc/$platform/$version"
golden_root="$repo_root/tmp/golden"
version_root="$golden_root/$version"
neutral_root="$golden_root/toolchain-current"
manifest_dir="$repo_root/analysis/golden"
manifest="$manifest_dir/$version-$platform.tsv"

[ -f "$projects_tsv" ] || die "missing project table: $projects_tsv"
[ -f "$converter" ] || die "missing converter: $converter"
[ -d "$toolchain_root/bin" ] || die "missing official toolchain: $toolchain_root"

compiler_candidates=("$toolchain_root"/bin/*-gcc)
if [ "${#compiler_candidates[@]}" -ne 1 ] || [ ! -x "${compiler_candidates[0]}" ]; then
    die "expected exactly one executable *-gcc in $toolchain_root/bin"
fi
compiler_name=${compiler_candidates[0]##*/}
cross_prefix=${compiler_name%gcc}
major=${version%%.*}

mkdir -p "$golden_root" "$version_root" "$manifest_dir"
if [ -e "$neutral_root" ] && [ ! -L "$neutral_root" ]; then
    die "refusing to replace non-symlink path: $neutral_root"
fi
# The neutral symlink is shared state; remember where it pointed so cleanup
# can restore it even when the run aborts mid-way.
neutral_previous=$(readlink "$neutral_root" 2>/dev/null || true)
ln -sfn "$toolchain_root" "$neutral_root"

neutral_compiler="$neutral_root/bin/$compiler_name"
neutral_objcopy="$neutral_root/bin/${cross_prefix}objcopy"
[ -x "$neutral_compiler" ] || die "neutral compiler is not executable: $neutral_compiler"
[ -x "$neutral_objcopy" ] || die "neutral objcopy is not executable: $neutral_objcopy"

temporary_dir=$(mktemp -d "$golden_root/.evt-golden.$version.XXXXXX")
temporary_manifest="$manifest_dir/.$version-$platform.tsv.$$"
cleanup() {
    rm -rf -- "$temporary_dir"
    rm -f -- "$temporary_manifest"
    if [ -n "${neutral_previous:-}" ]; then
        ln -sfn "$neutral_previous" "$neutral_root"
    fi
}
trap cleanup EXIT

manifest_body="$temporary_dir/body.tsv"
manifest_meta="$temporary_dir/meta.txt"
version_output="$temporary_dir/gcc-version.txt"
: > "$manifest_body"
: > "$manifest_meta"

if ! "$neutral_compiler" --version > "$version_output" 2>&1; then
    die "cannot execute official compiler through neutral path"
fi
toolchain_version=$(sed -n '1p' "$version_output")
[ -n "$toolchain_version" ] || die "compiler returned an empty version string"

clear_directory() {
    local directory=$1
    case "$directory" in
        "$version_root"/*/work|"$version_root"/*/run1|"$version_root"/*/run2) ;;
        *) die "refusing to clear unexpected directory: $directory" ;;
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

last_error_line() {
    local log_file=$1
    # Under "make -jN" the last line of a failed build is a wrapper such as
    # "make: *** [obj/x.o] Error 1" or "make: *** Waiting for unfinished
    # jobs....", which records nothing about why the build failed.  When the
    # last line is one of those, fall back to the last real diagnostic
    # ("file:line: Error: ...", "fatal error:", "undefined reference"), and
    # only then to the last line that is not a make wrapper.
    awk '
        NF {
            line = $0
            if ($0 !~ /^make(\[[0-9]+\])?: \*\*\*/) non_make = $0
            if ($0 ~ /[Ee]rror:|[Ff]atal error:|undefined reference/) diagnostic = $0
        }
        END {
            if (line ~ /^make(\[[0-9]+\])?: \*\*\*/) {
                if (diagnostic != "") line = diagnostic
                else if (non_make != "") line = non_make
            }
            gsub(/[\t\r\n]/, " ", line)
            if (line == "") line="no diagnostic text"
            print substr(line, 1, 240)
        }
    ' "$log_file"
}

write_harness_makefile() {
    local work=$1
    # Use make's override directive so the converter's complete project flags
    # are retained while both sides receive the same debug-prefix policy.
    printf '%s\n' \
        'override CFLAGS += -fdebug-prefix-map=$(DEBUG_PREFIX_FROM)=$(DEBUG_PREFIX_TO)' \
        'override ASFLAGS += -fdebug-prefix-map=$(DEBUG_PREFIX_FROM)=$(DEBUG_PREFIX_TO)' \
        > "$work/harness.mk"
}

debug_flags_from_makefile() {
    local makefile=$1
    awk '
        /^(TARGET_FLAGS|CPPFLAGS|CFLAGS|ASFLAGS|LDFLAGS)[[:space:]]*:=/ {
            for (i=3; i<=NF; i++) {
                if ($i ~ /^-g/) {
                    if (flags != "") flags=flags ","
                    flags=flags $i
                }
            }
        }
        END { print (flags == "" ? "none" : flags) }
    ' "$makefile"
}

build_once() {
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

artifact_list() {
    local run_dir=$1
    (cd "$run_dir" && find obj -type f -print | sort)
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

success_count=0
excluded_count=0
failure_count=0
nondeterministic_count=0
project_count=0
line_number=0

# Validate the project table up front and record per-slug inputs: a table
# error is a harness misconfiguration and must abort the whole run, which a
# background worker cannot do.
slug_list="$temporary_dir/slugs.txt"
: > "$slug_list"
while IFS=$'\t' read -r slug project_path native_major notes; do
    line_number=$((line_number + 1))
    if [ "$line_number" -eq 1 ]; then
        [ "$slug" = slug ] && [ "$project_path" = project_path ] && \
            [ "$native_major" = native_major ] || die "invalid TSV header"
        continue
    fi
    [ -n "$slug" ] || continue
    project_count=$((project_count + 1))
    case "$slug" in
        *[!a-z0-9-]*|'') die "invalid slug in project table: $slug" ;;
    esac

    project_dir="$evt_root/$project_path"
    [ -d "$project_dir" ] || die "missing project directory for $slug: $project_dir"
    wvproj_candidates=("$project_dir"/*.wvproj)
    if [ "${#wvproj_candidates[@]}" -ne 1 ] || [ ! -f "${wvproj_candidates[0]}" ]; then
        die "expected exactly one .wvproj for $slug"
    fi
    printf '%s\n' "${wvproj_candidates[0]}" > "$temporary_dir/$slug.wvproj"
    printf '%s\n' "$slug" >> "$slug_list"
done < "$projects_tsv"

[ "$project_count" -eq 9 ] || die "project table contains $project_count data rows, expected 9"

process_slug() {
    local slug=$1
    local wvproj
    wvproj=$(cat "$temporary_dir/$slug.wvproj")
    local body="$temporary_dir/$slug.body"
    local meta="$temporary_dir/$slug.meta"
    local counts="$temporary_dir/$slug.counts"
    local status="$temporary_dir/$slug.status"
    : > "$body"
    : > "$meta"
    : > "$status"

    local project_root="$version_root/$slug"
    local work="$project_root/work"
    local run1="$project_root/run1"
    local run2="$project_root/run2"
    local logs="$project_root/logs"
    mkdir -p "$work" "$run1" "$run2" "$logs"
    clear_directory "$work"
    clear_directory "$run1"
    clear_directory "$run2"

    local convert1_log="$logs/run1-convert.log"
    local build1_log="$logs/run1-build.log"
    local convert2_log="$logs/run2-convert.log"
    local build2_log="$logs/run2-build.log"

    printf '# converter[%s]=python3 %s %s --output %s --compiler-path %s --gcc-major %s --quiet\n' \
        "$slug" "$converter" "$wvproj" "$work" "$neutral_compiler" "$major" >> "$meta"

    if ! python3 "$converter" "$wvproj" --output "$work" \
        --compiler-path "$neutral_compiler" --gcc-major "$major" --quiet \
        > "$convert1_log" 2>&1; then
        show_failure_excerpt "$slug" run1-convert "$convert1_log"
        printf '# failure[%s]=converter failed; log=%s; last_error=%s\n' \
            "$slug" "$convert1_log" "$(last_error_line "$convert1_log")" >> "$meta"
        printf '%s %s %s %s\n' 0 0 1 0 > "$counts"
        return 0
    fi

    local debug_flags
    debug_flags=$(debug_flags_from_makefile "$work/Makefile")
    printf '# debug_flags[%s]=%s\n' "$slug" "$debug_flags" >> "$meta"
    write_harness_makefile "$work"

    if ! build_once "$work" "$build1_log"; then
        show_failure_excerpt "$slug" run1-build "$build1_log"
        local reason="run1 build failed; log=$build1_log; last_error=$(last_error_line "$build1_log")"
        if [ "$version" = 12.2.0 ] || [ "$version" = 8.2.0 ]; then
            printf '# excluded[%s]=%s\n' "$slug" "$reason" >> "$meta"
            printf '%s\tEXCLUDED\t%s\n' "$slug" "$reason" >> "$status"
            printf '%s %s %s %s\n' 0 1 0 0 > "$counts"
        else
            printf '# failure[%s]=%s\n' "$slug" "$reason" >> "$meta"
            printf '%s %s %s %s\n' 0 0 1 0 > "$counts"
        fi
        return 0
    fi
    mv "$work/obj" "$run1/obj"

    clear_directory "$work"
    if ! python3 "$converter" "$wvproj" --output "$work" \
        --compiler-path "$neutral_compiler" --gcc-major "$major" --quiet \
        > "$convert2_log" 2>&1; then
        show_failure_excerpt "$slug" run2-convert "$convert2_log"
        printf '# failure[%s]=run2 converter failed; log=%s; last_error=%s\n' \
            "$slug" "$convert2_log" "$(last_error_line "$convert2_log")" >> "$meta"
        printf '%s %s %s %s\n' 0 0 1 0 > "$counts"
        return 0
    fi
    write_harness_makefile "$work"
    if ! build_once "$work" "$build2_log"; then
        show_failure_excerpt "$slug" run2-build "$build2_log"
        printf '# failure[%s]=run2 build failed after run1 succeeded; log=%s; last_error=%s\n' \
            "$slug" "$build2_log" "$(last_error_line "$build2_log")" >> "$meta"
        printf '%s %s %s %s\n' 0 0 1 0 > "$counts"
        return 0
    fi
    mv "$work/obj" "$run2/obj"

    local run1_files="$temporary_dir/$slug-run1.files"
    local run2_files="$temporary_dir/$slug-run2.files"
    artifact_list "$run1" > "$run1_files"
    artifact_list "$run2" > "$run2_files"
    local nondeterministic_reason=
    local artifact run1_hash run2_hash
    if ! cmp -s "$run1_files" "$run2_files"; then
        nondeterministic_reason='artifact file sets differ'
    else
        while IFS= read -r artifact; do
            [ -n "$artifact" ] || continue
            run1_hash=$(sha256_file "$run1/$artifact")
            run2_hash=$(sha256_file "$run2/$artifact")
            if [ "$run1_hash" != "$run2_hash" ]; then
                nondeterministic_reason="SHA256 differs for $artifact ($run1_hash != $run2_hash)"
                break
            fi
        done < "$run1_files"
    fi
    if [ -n "$nondeterministic_reason" ]; then
        printf '# NONDETERMINISTIC[%s]=%s\n' "$slug" "$nondeterministic_reason" >> "$meta"
        printf '%s\tNONDETERMINISTIC\t%s\n' "$slug" "$nondeterministic_reason" >&2
        printf '%s %s %s %s\n' 0 0 0 1 > "$counts"
        return 0
    fi

    local object_count elf_count bin_count
    object_count=$(awk '/\.o$/ { count++ } END { print count+0 }' "$run1_files")
    elf_count=$(awk '/\.elf$/ { count++ } END { print count+0 }' "$run1_files")
    bin_count=$(awk '/\.bin$/ { count++ } END { print count+0 }' "$run1_files")
    if [ "$object_count" -lt 1 ] || [ "$elf_count" -lt 1 ] || [ "$bin_count" -lt 1 ]; then
        printf '# failure[%s]=missing required gate artifacts (.o=%s .elf=%s .bin=%s)\n' \
            "$slug" "$object_count" "$elf_count" "$bin_count" >> "$meta"
        printf '%s\tFAIL\tmissing required gate artifacts\n' "$slug" >&2
        printf '%s %s %s %s\n' 0 0 1 0 > "$counts"
        return 0
    fi

    local artifact_count=0
    local gate_count=0
    local class size hash
    while IFS= read -r artifact; do
        [ -n "$artifact" ] || continue
        artifact_count=$((artifact_count + 1))
        case "$artifact" in
            *.o|*.elf|*.bin)
                class=gate
                gate_count=$((gate_count + 1))
                ;;
            *) class=aux ;;
        esac
        size=$(file_size "$run1/$artifact")
        hash=$(sha256_file "$run1/$artifact")
        printf '%s\t%s\t%s\t%s\t%s\n' "$slug" "$artifact" "$class" "$size" "$hash" >> "$body"
    done < "$run1_files"
    printf '%s\tPASS\tartifacts=%s\tgate=%s\tdebug=%s\n' \
        "$slug" "$artifact_count" "$gate_count" "$debug_flags" >> "$status"
    printf '%s %s %s %s\n' 1 0 0 0 > "$counts"
}

# Project-level concurrency (same worker-pool shape as evt-compare.sh, per
# the 2026-08-15 concurrency contract: 16 project-level workers, make -j2
# inside each project).  Workers write body/meta/status/counter files per
# slug and the parent assembles them in project-table order afterwards, so
# the manifest and the stdout status stream are identical to a serial run.
# Scope of that guarantee: it covers exactly what goes through the per-slug
# files.  Diagnostics that workers write straight to stderr -- the
# show_failure_excerpt log tail, the NONDETERMINISTIC notice and the
# "missing required gate artifacts" line -- are not ordered, so with several
# failing projects those excerpts can interleave on the terminal.  The
# manifest still records each failure separately, so attribution is done from
# the manifest, not from stderr.  bash 3.2 has no "wait -n", so a full pool is
# drained by waiting on its oldest member.
workers=${EVT_GOLDEN_WORKERS:-16}
case "$workers" in
    ''|*[!0-9]*|0) die "EVT_GOLDEN_WORKERS must be a positive integer" ;;
esac

running_pids=()
while IFS= read -r slug; do
    [ -n "$slug" ] || continue
    if [ "${#running_pids[@]}" -ge "$workers" ]; then
        wait "${running_pids[0]}" || true
        running_pids=(${running_pids[@]:1})
    fi
    process_slug "$slug" &
    running_pids+=($!)
done < "$slug_list"
for pid in ${running_pids[@]+"${running_pids[@]}"}; do
    wait "$pid" || true
done

while IFS= read -r slug; do
    [ -n "$slug" ] || continue
    [ -f "$temporary_dir/$slug.counts" ] || die "worker produced no counters for $slug"
    cat "$temporary_dir/$slug.meta" >> "$manifest_meta"
    cat "$temporary_dir/$slug.body" >> "$manifest_body"
    cat "$temporary_dir/$slug.status"
    read -r slug_success slug_excluded slug_failure slug_nondet \
        < "$temporary_dir/$slug.counts"
    success_count=$((success_count + slug_success))
    excluded_count=$((excluded_count + slug_excluded))
    failure_count=$((failure_count + slug_failure))
    nondeterministic_count=$((nondeterministic_count + slug_nondet))
done < "$slug_list"

if [ "$failure_count" -eq 0 ] && [ "$nondeterministic_count" -eq 0 ]; then
    double_run_result="PASS deterministic=$success_count excluded=$excluded_count failures=0"
else
    double_run_result="FAIL deterministic=$success_count excluded=$excluded_count failures=$failure_count nondeterministic=$nondeterministic_count"
fi

generated_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
{
    printf '# golden_manifest_version=1\n'
    printf '# toolchain=%s\n' "$toolchain_version"
    printf '# toolchain_real_root=%s\n' "$toolchain_root"
    printf '# toolchain_invocation_root=%s\n' "$neutral_root"
    printf '# debug_prefix_map=%s=>%s\n' "$toolchain_root" "$neutral_root"
    printf '# debug_path_experiment=IDENTICAL direct_sha256=f387614561fb2f28fe3fec94c2f99c73daa9642589924ada651eda98b9c01534 neutral_sha256=f387614561fb2f28fe3fec94c2f99c73daa9642589924ada651eda98b9c01534; symlink alone ineffective; resolution=fdebug-prefix-map (user-selected)\n'
    printf '# SOURCE_DATE_EPOCH=%s\n' "$SOURCE_DATE_EPOCH"
    if [ "$platform" = linux-amd64 ]; then
        printf '# container_image=%s\n' "$container_image"
    fi
    cat "$manifest_meta"
    printf '# double_run=%s\n' "$double_run_result"
    printf '# generated_at_utc=%s\n' "$generated_at"
    printf 'slug\tartifact\tclass\tsize\tsha256\n'
    cat "$manifest_body"
} > "$temporary_manifest"
mv "$temporary_manifest" "$manifest"

printf 'manifest=%s\n' "$manifest"
printf 'double_run=%s\n' "$double_run_result"

if [ "$failure_count" -ne 0 ] || [ "$nondeterministic_count" -ne 0 ]; then
    exit 1
fi
