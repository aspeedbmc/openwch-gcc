#!/usr/bin/env bash
# Run one linux job of the toolchain workflows locally with act, on a dedicated
# work copy, without touching the frozen worktree or any host path outside the
# evidence directory.
#
# Usage: scripts/ci/act-verify.sh <job-id> [extra act args...]
#
# Why a work copy and not the checkout itself: the job must run
# ref/wch-evt/patches/apply.sh (which modifies tracked EVT files by design) and
# evt-golden.sh writes analysis/golden/<version>-<platform>.tsv (a tracked
# file).  "Leave the tree clean" and "run the real steps" cannot both hold in
# one tree.  The copy is produced with `git ls-files -c -o --exclude-standard`
# (see the work-copy step below), which yields every tracked file plus every
# untracked file git would accept and nothing .gitignore excludes -- i.e. what
# a CI checkout of a commit carrying the current working tree would contain.
# That makes this the more faithful local rehearsal rather than a workaround.
# `git archive HEAD` is deliberately NOT used: it emits the committed tree
# only, so deliverables that are not committed yet -- scripts/ci/* and the two
# new workflows, for most of this phase -- would be missing from the copy, and
# the deliverable-binding check below would then enumerate zero rows and pass
# without having checked anything.
#
# Host-isolation invariants, all from the act probe (S0/act-probe/findings.md):
#   * never --bind: bind mode makes the container write straight into the host
#     tree.  Default copy mode was measured clean.
#   * all three act write surfaces are redirected under the evidence directory;
#     the defaults are ~/.cache/act and ~/.cache/actcache, outside any ledger.
#   * --container-architecture linux/amd64 is mandatory: without it the
#     container is aarch64 and build-toolchain-15.2.0-linux.sh:31 dies.
#   * -P <label>=<image> is mandatory: with no platform mapping act opens an
#     interactive picker and dies with EOF when stdin is closed.
#   * -P <label>=-self-hosted runs the job on the host as the host user.  That
#     is the one configuration that could repoint the real /Users/mrs, so this
#     script refuses it in its own arguments and in every actrc it would read.
#     The flag is absent from `act --help`, so the check is a literal search.

set -euo pipefail

export LC_ALL=C

die() {
    printf 'act-verify.sh: %s\n' "$*" >&2
    exit 2
}

if [ "$#" -lt 1 ]; then
    printf 'usage: %s <job-id> [extra act args...]\n' "${0##*/}" >&2
    exit 2
fi

job_id=$1
shift

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
worktree=$(CDPATH= cd -- "$script_dir/../.." && pwd -P)
[ -f "$worktree/AGENTS.md" ] || die "not running from an openwch repository: $worktree"

# Linux jobs only.  The darwin jobs would need a macOS runner, and act can only
# offer that through -self-hosted, which is exactly what this script forbids.
# GitHub and act both reject a '.' in a job id, so the ids are spelled with
# dashes; the dotted spelling is accepted here and translated.
case "$job_id" in
    linux-15.2.0|linux-15-2-0)
        job_id=linux-15-2-0
        workflow="$worktree/.github/workflows/toolchain-ci.yml"
        ;;
    release-linux-15.2.0|release-linux-15-2-0)
        job_id=release-linux-15-2-0
        workflow="$worktree/.github/workflows/release.yml"
        ;;
    *) die "job-id is not on the linux allow-list (linux-15-2-0, release-linux-15-2-0): $job_id" ;;
esac
# Absolute constant, independent of anything the run produces.
expected_gate_total=274
[ -f "$workflow" ] || die "missing workflow: $workflow"

runner_image=${ACT_RUNNER_IMAGE:-catthehacker/ubuntu:act-24.04}
runner_label=ubuntu-24.04
minimum_act=0.2.89

command -v act >/dev/null 2>&1 || die "act is unavailable"
command -v docker >/dev/null 2>&1 || die "docker is unavailable"
command -v git >/dev/null 2>&1 || die "git is unavailable"

act_version=$(act --version 2>&1 | awk '{print $NF}')
lowest=$(printf '%s\n%s\n' "$act_version" "$minimum_act" | sort -t. -k1,1n -k2,2n -k3,3n | sed -n 1p)
[ "$lowest" = "$minimum_act" ] || \
    die "act $act_version is older than the pinned floor $minimum_act"

# --- -self-hosted rejection ------------------------------------------------
for argument in "$@" "$runner_image"; do
    case "$argument" in
        *self-hosted*) die "refusing an argument that names self-hosted: $argument" ;;
    esac
done
actrc_candidates=(
    "$worktree/.actrc"
    "$HOME/.actrc"
    "${XDG_CONFIG_HOME:-$HOME/.config}/act/actrc"
    "$HOME/Library/Application Support/act/actrc"
)
for candidate in "${actrc_candidates[@]}"; do
    [ -f "$candidate" ] || continue
    if grep -Fq -- self-hosted "$candidate"; then
        die "an actrc act would read contains self-hosted: $candidate"
    fi
    printf 'actrc_scanned=%s\tclean\n' "$candidate"
done

# --- evidence layout -------------------------------------------------------
run_id=${ACT_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}
evidence="$worktree/tmp/p7-evidence/S4"
run_dir="$evidence/$job_id-$run_id"
workspace_parent="$evidence/act-workspace"
workspace="$workspace_parent/$run_id"
mkdir -p "$run_dir" "$workspace_parent" \
    "$evidence/act-cache/actions" "$evidence/act-cache/cacheserver" "$evidence/artifacts"
if [ -e "$workspace" ]; then
    die "work copy already exists (pass a fresh ACT_RUN_ID): $workspace"
fi
log="$run_dir/act-full.log"
timing="$run_dir/timing.tsv"
timing_stages="$run_dir/timing-stages.tsv"
memory="$run_dir/memory.tsv"
disk="$run_dir/disk.tsv"
binding="$run_dir/deliverable-binding.txt"

# An evidence run must be a cold-cache run: the official package download is
# itself the proof that provisioning works end to end.  ACT_RUN_KIND=debug
# marks a re-run that may reuse a cache; the two never share a directory.
run_kind=${ACT_RUN_KIND:-evidence}
case "$run_kind" in
    evidence|debug) ;;
    *) die "ACT_RUN_KIND must be evidence or debug: $run_kind" ;;
esac

# --- frozen-worktree baseline ---------------------------------------------
git -C "$worktree" rev-parse HEAD      > "$run_dir/wt-head-before.txt"
git -C "$worktree" status --porcelain  > "$run_dir/worktree-status-before.txt"

# --- work copy: repository files only, one commit, zero remotes ------------
# The file set is `git ls-files -c -o --exclude-standard`: every tracked file
# plus every untracked file git would accept, and nothing that .gitignore
# excludes.  That is exactly what a CI checkout of a commit carrying the
# current working tree would contain -- and unlike `git archive HEAD` it
# includes deliverables that are not committed yet, which is the normal state
# while this workflow is being developed.
#
# The commit afterwards is not optional.  An extracted tree plus a bare
# `git init` leaves an unborn HEAD, and act derives GITHUB_SHA and the ref from
# the local repository.  One commit also makes this copy the same shape as the
# probe repository the act findings were measured on.
mkdir -p "$workspace"
( cd "$worktree" && git ls-files -c -o --exclude-standard -z ) \
    | tar -c --null -T - -C "$worktree" -f - \
    | tar -x -C "$workspace" -f -
git -C "$workspace" init -q
git -C "$workspace" config user.name 'OpenWCH act verify'
git -C "$workspace" config user.email 'act-verify@openwch.local'
git -C "$workspace" add -A
GIT_AUTHOR_DATE='@1767225600 +0000' GIT_COMMITTER_DATE='@1767225600 +0000' \
    git -C "$workspace" commit -q -m "act work copy of $(git -C "$worktree" rev-parse HEAD)"
[ -z "$(git -C "$workspace" remote)" ] || die "work copy unexpectedly has a remote"

# tmp/ is gitignored, so the copy carries no caches at all -- the run is cold by
# construction.  Assert it anyway so an evidence run can never silently become a
# warm one if that ever changes.
if [ "$run_kind" = evidence ] && [ -e "$workspace/tmp/ci-cache" ]; then
    die "evidence run requires a cold cache but the work copy already has tmp/ci-cache"
fi

# --- deliverable binding ---------------------------------------------------
# Proving something on a copy proves nothing about the deliverable unless the
# two are shown to be the same bytes.  Recorded before the run; re-checked
# after, because the run itself may rewrite files inside the copy.
digest_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}
record_binding() {
    local phase=$1 relative source_digest copy_digest verdict status=0 rows=0
    printf '## %s\n' "$phase" >> "$binding"
    while IFS= read -r relative; do
        [ -n "$relative" ] || continue
        rows=$((rows + 1))
        source_digest=$(digest_of "$worktree/$relative")
        if [ -f "$workspace/$relative" ]; then
            copy_digest=$(digest_of "$workspace/$relative")
        else
            copy_digest=MISSING
        fi
        if [ "$source_digest" = "$copy_digest" ]; then verdict=SAME; else verdict=DIFFERENT; status=1; fi
        printf '%s\t%s\t%s\t%s\n' "$verdict" "$relative" "$source_digest" "$copy_digest" >> "$binding"
    done < <(cd "$worktree" && git ls-files -c -o --exclude-standard -- '.github/workflows' 'scripts/ci')
    printf '# %s rows=%s status=%s\n' "$phase" "$rows" "$status" >> "$binding"
    # An empty enumeration would make this check pass without checking
    # anything, so it is a failure in itself.
    [ "$rows" -gt 0 ] || return 1
    return "$status"
}
: > "$binding"
record_binding before-run || die "work copy diverges from the deliverable before the run"

# --- run -------------------------------------------------------------------
# A host-side memory poller runs alongside act.  The in-job cgroup readings are
# the primary source; this is the independent cross-check that survives a
# kernel without memory.peak.
mem_samples="$run_dir/docker-mem-samples.txt"
: > "$mem_samples"
(
    while : ; do
        docker stats --no-stream --format '{{.Name}}\t{{.MemUsage}}' 2>/dev/null \
            | awk -F'\t' -v now="$(date +%s)" '$1 ~ /^act-/ {print now "\t" $1 "\t" $2}' \
            >> "$mem_samples" || true
        sleep 20
    done
) &
mem_poller=$!
stop_poller() { kill "$mem_poller" 2>/dev/null || true; }
trap stop_poller EXIT INT TERM

started=$(date +%s)
set +e
act push \
    -C "$workspace" \
    -W "$workflow" \
    -j "$job_id" \
    -P "$runner_label=$runner_image" \
    --container-architecture linux/amd64 \
    --action-cache-path "$evidence/act-cache/actions" \
    --cache-server-path "$evidence/act-cache/cacheserver" \
    --artifact-server-path "$evidence/artifacts" \
    --rm \
    "$@" < /dev/null 2>&1 | tee "$log"
act_status=${PIPESTATUS[0]}
set -e
finished=$(date +%s)
stop_poller
trap - EXIT INT TERM

printf '%s\n' "$act_status" > "$run_dir/act-exit-code.txt"

# --- host isolation regression --------------------------------------------
git -C "$worktree" rev-parse HEAD      > "$run_dir/wt-head-after.txt"
git -C "$worktree" status --porcelain  > "$run_dir/worktree-status-after.txt"
diff "$run_dir/wt-head-before.txt" "$run_dir/wt-head-after.txt" || \
    die "the frozen worktree HEAD changed during the act run"
diff "$run_dir/worktree-status-before.txt" "$run_dir/worktree-status-after.txt" || \
    die "the frozen worktree working state changed during the act run"

record_binding after-run || \
    die "work copy diverges from the deliverable after the run"

# --- gate verdicts ---------------------------------------------------------
# The SUMMARY row is copied verbatim, tabs intact: re-spacing it would destroy
# the very separator the assertion depends on.
awk -F'\t' '$1 ~ /SUMMARY$/ {sub(/^.*SUMMARY/, "SUMMARY"); print}' "$log" \
    > "$run_dir/summary-line.txt"
# The expected values go to their own file: this block appends to
# summary-line.txt while the awk below reads that same file, so anything
# written here becomes an extra awk input row.  A comment row carries no
# gate_pass= field and would therefore manufacture a permanent bogus
# "verdict FAIL" (and, being non-empty, would also mask the -s guard below).
printf '# expected: gate_pass=%s gate_total=%s gate_fail=0\n' \
    "$expected_gate_total" "$expected_gate_total" > "$run_dir/summary-expected.txt"
{
    if [ -s "$run_dir/summary-line.txt" ]; then
        awk -F'\t' -v want="$expected_gate_total" '
            {
                pass = fail = total = "absent"
                for (i = 2; i <= NF; i++) {
                    if ($i ~ /^gate_pass=/)  { split($i, a, "="); pass  = a[2] }
                    if ($i ~ /^gate_total=/) { split($i, a, "="); total = a[2] }
                    if ($i ~ /^gate_fail=/)  { split($i, a, "="); fail  = a[2] }
                }
                printf "gate_pass\t%s\ngate_total\t%s\ngate_fail\t%s\n", pass, total, fail
                verdict = (pass == want && total == want && fail == "0") ? "PASS" : "FAIL"
                printf "verdict\t%s\n", verdict
            }' "$run_dir/summary-line.txt"
    else
        printf 'verdict\tFAIL\treason=no SUMMARY row in the log\n'
    fi
} >> "$run_dir/summary-line.txt"

grep -E 'manifest_gate_rows=|manifest_projects=' "$log" > "$run_dir/assertions.txt" || \
    printf '(no assertion output found in the log)\n' > "$run_dir/assertions.txt"
grep -E 'raw_drift_lines=' "$log" > "$run_dir/raw-drift.txt" || \
    printf '(no raw drift output found in the log)\n' > "$run_dir/raw-drift.txt"

# Per-step outcome.  act prints one Success/Failure line per step and an
# exitcode for failures; that is the per-step status, and it is the only
# per-step signal available without editing every run block.
grep -E '(Success|Failure) - (Main|Post|Set up|Complete)|exitcode' "$log" \
    > "$run_dir/step-exit-codes.txt" || \
    printf '(no per-step status lines found)\n' > "$run_dir/step-exit-codes.txt"

# Cold-cache download proof, apt package set, and both toolchain identities.
grep -E 'WCH_TOOLCHAIN_|provision_mode=|official_compiler|archive_download=|archive_verified=|archive_cache_hit=' \
    "$log" > "$run_dir/fetch.log" || printf '(no provisioning lines found)\n' > "$run_dir/fetch.log"
sed -n '/--- installed apt package set ---/,/^.*Success - Main Install container build dependencies/p' \
    "$log" > "$run_dir/apt-packages.txt" || true
awk -F'\t' '$1 ~ /P7_TOOLCHAIN$/ {sub(/^.*P7_TOOLCHAIN/, "P7_TOOLCHAIN"); print}' "$log" \
    > "$run_dir/toolchain-identity.txt"

# Keep the freshly generated manifest: it is the denominator every assertion in
# this run was measured against and cannot be reconstructed later.
if [ -f "$workspace/analysis/golden/15.2.0-linux-amd64.tsv" ]; then
    cp "$workspace/analysis/golden/15.2.0-linux-amd64.tsv" "$run_dir/manifest-fresh.tsv"
fi

# --- timings ---------------------------------------------------------------
# Stage boundaries come from P7_STAGE markers the workflow prints, so the same
# instrumentation produces the same numbers on a real runner.
{
    printf 'stage\tseconds\tdetail\n'
    awk -F'\t' '
        $1 ~ /P7_STAGE$/ && $2 == "begin" { begin[$3] = $4 }
        $1 ~ /P7_STAGE$/ && $2 == "end" && ($3 in begin) {
            printf "%s\t%d\t%s\n", $3, $4 - begin[$3], "from P7_STAGE markers"
        }
    ' "$log"
    printf 'act-total\t%s\tact wall clock including image pull and act overhead\n' \
        "$((finished - started))"
} > "$timing"

# Finer breakdown, from the build script's own `stage=` announcements.  This is
# what allows a structural approximation of the serial fraction from a single
# run: T(n)=T1*(s+(1-s)/n) has two unknowns and one measurement cannot solve it,
# so configure-like phases are read as serial and make-like phases as parallel.
# It is a lower bound (the parallel phases still contain serial sub-steps such
# as single-threaded linking and gengtype) and it is measured under qemu
# emulation, which need not scale serial and parallel work by the same factor.
{
    printf 'substage\tseconds\tdetail\n'
    awk -F'\t' '
        $1 ~ /P7_SUBSTAGE$/ {
            sub(/^.*P7_SUBSTAGE/, "P7_SUBSTAGE")
            if (previous != "") printf "%s\t%d\t%s\n", previous, $3 - previous_at, "from P7_SUBSTAGE markers"
            previous = $2; previous_at = $3
        }
        END { if (previous != "") printf "%s\t%s\t%s\n", previous, "0", "sentinel marker, no duration of its own" }
    ' "$log"
} > "$timing_stages"

# --- memory ----------------------------------------------------------------
{
    printf '# container_memory_max_bytes\t%s\n' \
        "$(awk -F'\t' '$1 ~ /P7_FACT$/ && $2 == "cgroup_memory_max" { print $3 }' "$log" | sed -n 1p)"
    printf '# container_meminfo_total_kb\t%s\n' \
        "$(awk -F'\t' '$1 ~ /P7_FACT$/ && $2 == "meminfo_total_kb" { print $3 }' "$log" | sed -n 1p)"
    printf '# container_nproc\t%s\n' \
        "$(awk -F'\t' '$1 ~ /P7_FACT$/ && $2 == "nproc" { print $3 }' "$log" | sed -n 1p)"
    printf '# host_memory_bytes\t%s\n' "$(sysctl -n hw.memsize 2>/dev/null || echo unavailable)"
    printf '# host_cores\t%s\n' "$( (sysctl -n hw.ncpu 2>/dev/null || nproc) | tr -d '[:space:]')"
    printf '# note\tlinux/amd64 under qemu emulation; extrapolating to darwin/arm64 crosses a platform boundary\n'
    printf 'checkpoint\tbytes\tsource\n'
    awk -F'\t' '$1 ~ /P7_MEM$/ { printf "%s\t%s\t%s\n", $2, $3, $4 }' "$log"
    printf 'docker-stats-peak\t%s\thost-side docker stats poll, max of MemUsage column\n' \
        "$(awk -F'\t' '{split($3, a, " "); print a[1]}' "$mem_samples" 2>/dev/null \
            | sort -h | tail -n 1)"
} > "$memory"

# --- disk ------------------------------------------------------------------
{
    printf 'checkpoint\tkilobytes\tdetail\n'
    awk -F'\t' '$1 ~ /P7_DISK$/ { printf "%s\t%s\t%s\n", $2, $3, $4 }' "$log"
} > "$disk"

# --- environment and binding provenance ------------------------------------
{
    printf 'run_kind\t%s\n' "$run_kind"
    printf 'run_id\t%s\n' "$run_id"
    printf 'job_id\t%s\n' "$job_id"
    printf 'workflow\t%s\n' "$workflow"
    printf 'act_version\t%s\n' "$act_version"
    printf 'platform_mapping\t%s=%s\n' "$runner_label" "$runner_image"
    printf 'container_architecture\tlinux/amd64\n'
    printf 'container_image_digest\t%s\n' \
        "$(awk '/image=debian:bookworm@sha256:/ {for (i = 1; i <= NF; i++) if ($i ~ /^image=/) {print substr($i, 7); exit}}' "$log")"
    printf 'host_cores\t%s\n' "$( (sysctl -n hw.ncpu 2>/dev/null || nproc) | tr -d '[:space:]')"
    printf 'container_nproc\t%s\n' \
        "$(awk -F'\t' '$1 ~ /P7_FACT$/ && $2 == "nproc" { print $3 }' "$log" | sed -n 1p)"
    printf 'concurrent_heavy_run\t%s\n' "${ACT_CONCURRENT_NOTE:-unknown (Manager fills in)}"
    printf 'bind_mode\tnever (--bind is not passed)\n'
    printf 'self_hosted\tnever (rejected in argv and in every actrc read)\n'
} > "$run_dir/env.txt"

# The evidence run's canonical copies live directly under S4/ so the checklist
# paths resolve; debug re-runs stay in their own directory only.
if [ "$run_kind" = evidence ]; then
    for artefact in act-full.log act-exit-code.txt summary-line.txt \
            summary-expected.txt assertions.txt \
            step-exit-codes.txt manifest-fresh.tsv raw-drift.txt timing.tsv \
            timing-stages.tsv memory.tsv disk.tsv env.txt fetch.log \
            apt-packages.txt toolchain-identity.txt deliverable-binding.txt \
            worktree-status-before.txt worktree-status-after.txt; do
        [ -f "$run_dir/$artefact" ] && cp "$run_dir/$artefact" "$evidence/$artefact"
    done
fi

printf 'act_status=%s\n' "$act_status"
printf 'run_kind=%s\n' "$run_kind"
printf 'run_dir=%s\n' "$run_dir"
printf 'workspace=%s\n' "$workspace"
printf 'artifacts=%s\n' "$evidence/artifacts"
exit "$act_status"
