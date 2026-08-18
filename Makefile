# openwch-gcc — publication assembly and verification.
#
# This is a RELEASE MAINTAINER'S tool, not part of the build.  It assembles the
# public repository out of a local private working repository (SRC) and then
# exercises the published tree end to end, so that what gets pushed is known to
# build and to pass the byte gate as published — not merely as developed.
#
# SRC may point at any local copy of the private repository; every path below
# is overridable on the command line (`make sync SRC=/path/to/openwch`).
#
# Targets
#   sync            Mirror SRC's tracked files into this tree, minus the three
#                   classes that must not be published (see EXCLUDE_* below),
#                   then make sure .gitignore covers what the exclusions leave
#                   behind.  Idempotent: re-running restores SRC's .gitignore
#                   and re-appends the two lines, so `git status` stays clean.
#   init            git init -b main plus the first commit.  Refuses to run on
#                   a tree that already has .git.
#   evt             Restore the EVT corpus (ref/wch-evt/Qingke*/) from the
#                   verified pack and apply ref/wch-evt/patches/.  The corpus is
#                   a gate input, so the pack's SHA-256 is checked with no
#                   override — see scripts/fetch-evt.sh.
#   official        Local convenience only: symlink SRC's MounRiver Studio 2
#                   bundle and Linux toolchain package into ref/ and extract
#                   them into ref/gcc/<platform>/<version>/.  External users do
#                   NOT do this — they obtain the official packages themselves
#                   as the README's "Getting the inputs" section describes.
#   verify-12.2.0   Full darwin-arm64 12.2.0 leg in THIS tree: prepare pristine
#                   sources, build at the literal WCH path, generate the golden
#                   manifest from the official package and compare our build
#                   against it.  Asserts the absolute gate denominator (274 gate
#                   rows) before comparing, so a shrunken corpus fails instead
#                   of passing.
#   verify-act      Run the linux CI job locally under act.
#   verify          verify-12.2.0 then verify-act, strictly in that order.
#
# Prerequisites
#   sync            SRC is a git repository; rsync, perl, git.
#   evt             EVT_PACK exists (or edit the recipe to use --url).
#   official        SRC still holds the two vendor packages.
#   verify-12.2.0   macOS on Apple Silicon; `make official` (or an equivalent
#                   ref/gcc/darwin-arm64/12.2.0/) and `make evt` done; the
#                   literal build root /Users/mrs/Work must exist and be
#                   writable (one sudo the first time — see the README).  The
#                   /Users/mrs/Work/riscv-none-elf-gcc-xpack.git symlink is
#                   shared host state: this target records where it pointed,
#                   repoints it at this tree for the build, and restores it
#                   afterwards (also on abort) before re-reading it to confirm.
#   verify-act      act >= 0.2.89 and a running Docker daemon.
#
# Heavy targets (verify-12.2.0, verify-act) must not be run concurrently: they
# take the same literal paths and the same CPU budget.  Hence .NOTPARALLEL.

SHELL := /bin/bash

# ---- paths ----------------------------------------------------------------
HERE            := $(CURDIR)
SRC             ?= ../openwch
SRC_ABS         := $(abspath $(SRC))
EVT_PACK        ?= $(SRC)/tmp/publish/dist/openwch-evt-d5added7.tar.gz
EVT_PACK_ABS    := $(abspath $(EVT_PACK))
MRS_APP         ?= $(SRC_ABS)/ref/MounRiver Studio 2.app
MRS_LINUX       ?= $(SRC_ABS)/ref/MRS_Toolchain_Linux_X64_V250

# ---- publication exclusions ----------------------------------------------
# 1. the EVT corpus: 25065 files, distributed as a verified pack instead
# 2. macOS Finder metadata
# 3. one 344 MB machine-evidence file, above GitHub's per-file limit
EXCLUDE_CORPUS_PREFIX ?= ref/wch-evt/Qingke
EXCLUDE_BIG_FILE      ?= ref/wch-isa-research/errata/06b-chipid-errata-evidence/machine/canonical-unit-domain-records.jsonl.gz
# Kept as two scalars rather than one list: the first contains a glob, and a
# `for` loop over an unquoted list would expand it against the working tree.
GITIGNORE_LINE_1      ?= ref/wch-evt/Qingke*/
GITIGNORE_LINE_2      ?= .DS_Store

# ---- first commit ---------------------------------------------------------
# Left empty on purpose: git then uses the ambient identity.  Set both to give
# the import a project identity instead of the committer's machine account.
GIT_USER_NAME   ?=
GIT_USER_EMAIL  ?=

# ---- 12.2.0 verification --------------------------------------------------
PLATFORM        ?= darwin-arm64
BUILD_JOBS      ?= 16
GATE_TOTAL_12   ?= 274
LITERAL_XPACK   ?= /Users/mrs/Work/riscv-none-elf-gcc-xpack.git
PROJECT_12      ?= $(HERE)/tmp/ci-src/12.2.0/riscv-none-elf-gcc-xpack.git
DOWNLOADS_12    ?= $(HERE)/tmp/toolchain_12.2.0/downloads
SRC_DOWNLOADS_12 ?= $(SRC_ABS)/tmp/toolchain_12.2.0/downloads
MANIFEST_12     := $(HERE)/analysis/golden/12.2.0-$(PLATFORM).tsv

# ---- act ------------------------------------------------------------------
ACT_JOB         ?= linux-15-2-0

.PHONY: all sync init evt official verify verify-12.2.0 verify-act help
.NOTPARALLEL:

all: help

help:
	@sed -n '1,50p' $(firstword $(MAKEFILE_LIST))

# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------
# The file list is `git ls-files -z` — NUL separated, so paths with spaces or
# non-ASCII bytes survive — filtered by perl (also NUL separated) and handed to
# rsync with --from0 --files-from.  Deliberately no --delete: this tree also
# holds build trees and extracted vendor packages that are not in SRC's index.
sync:
	@set -euo pipefail; \
	test -d "$(SRC_ABS)/.git" || { echo "sync: SRC is not a git repository: $(SRC_ABS)" >&2; exit 2; }; \
	mkdir -p "$(HERE)"; \
	list=$$(mktemp "$${TMPDIR:-/tmp}/openwch-sync.XXXXXX"); \
	trap 'rm -f "$$list"' EXIT INT TERM; \
	git -C "$(SRC_ABS)" ls-files -z \
	  | CORPUS='$(EXCLUDE_CORPUS_PREFIX)' BIG='$(EXCLUDE_BIG_FILE)' perl -0 -ne \
	      'chomp; next if index($$_, $$ENV{CORPUS}) == 0; next if m{(?:^|/)\.DS_Store$$}; next if $$_ eq $$ENV{BIG}; print "$$_\0"' \
	  > "$$list"; \
	rsync -a --from0 --files-from="$$list" "$(SRC_ABS)/" "$(HERE)/"; \
	n=$$(tr -dc '\0' < "$$list" | wc -c | tr -d ' '); \
	echo "sync: source=$(SRC_ABS) head=$$(git -C "$(SRC_ABS)" rev-parse HEAD)"; \
	echo "sync: synced_files=$$n"
	@set -euo pipefail; \
	target="$(HERE)/.gitignore"; \
	[ -f "$$target" ] || : > "$$target"; \
	if [ -s "$$target" ] && [ -n "$$(tail -c 1 "$$target")" ]; then printf '\n' >> "$$target"; fi; \
	for line in '$(GITIGNORE_LINE_1)' '$(GITIGNORE_LINE_2)'; do \
	    if ! grep -qxF -- "$$line" "$$target"; then printf '%s\n' "$$line" >> "$$target"; fi; \
	done; \
	echo "sync: gitignore_lines=$$(wc -l < "$$target" | tr -d ' ')"

# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------
init:
	@set -euo pipefail; \
	if [ -e "$(HERE)/.git" ]; then echo "init: $(HERE)/.git already exists; refusing to re-initialise" >&2; exit 2; fi; \
	git -C "$(HERE)" init -q -b main; \
	if [ -n "$(GIT_USER_NAME)" ]; then git -C "$(HERE)" config user.name "$(GIT_USER_NAME)"; fi; \
	if [ -n "$(GIT_USER_EMAIL)" ]; then git -C "$(HERE)" config user.email "$(GIT_USER_EMAIL)"; fi; \
	git -C "$(HERE)" add -A; \
	sha=$$(git -C "$(SRC_ABS)" rev-parse HEAD); \
	{ \
	  printf 'chore: import the public tree from openwch@%s\n\n' "$$sha"; \
	  printf 'Assembled by `make sync` from the private working repository at\n'; \
	  printf 'openwch@%s.  Three classes are excluded from the import:\n\n' "$$sha"; \
	  printf '  * ref/wch-evt/Qingke*/ — the EVT test corpus (25065 files).  It is\n'; \
	  printf '    distributed as a SHA-256 verified pack and restored with\n'; \
	  printf '    scripts/fetch-evt.sh; see the README.\n'; \
	  printf '  * .DS_Store — macOS Finder metadata.\n'; \
	  printf '  * %s\n' '$(EXCLUDE_BIG_FILE)'; \
	  printf '    — 344 MB of raw machine evidence, above GitHub'"'"'s per-file limit.\n\n'; \
	  printf 'The last two are also covered by .gitignore so they cannot come back.\n\n'; \
	  printf 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>\n'; \
	} | git -C "$(HERE)" commit -q -F -; \
	echo "init: commit=$$(git -C "$(HERE)" rev-parse HEAD)"; \
	echo "init: tracked_files=$$(git -C "$(HERE)" ls-files | wc -l | tr -d ' ')"

# ---------------------------------------------------------------------------
# evt
# ---------------------------------------------------------------------------
evt:
	@set -euo pipefail; \
	test -f "$(EVT_PACK_ABS)" || { echo "evt: pack not found: $(EVT_PACK_ABS)" >&2; exit 2; }; \
	cd "$(HERE)" && scripts/fetch-evt.sh --file "$(EVT_PACK_ABS)" --apply

# ---------------------------------------------------------------------------
# official
# ---------------------------------------------------------------------------
# Local verification convenience: it borrows the vendor packages that already
# sit in SRC instead of downloading them again.  External users get the
# official packages themselves — MounRiver Studio 2 from mounriver.com for
# darwin, the Linux package through ref/wch-evt/tools/fetch_wch_toolchain.py —
# exactly as the README's "Getting the inputs" section describes.  Both link
# names are gitignored (ref/*app, ref/MRS_Toolchain_Linux_X64_V250).
official:
	@set -euo pipefail; \
	test -d "$(MRS_APP)" || { echo "official: missing $(MRS_APP)" >&2; exit 2; }; \
	test -d "$(MRS_LINUX)" || { echo "official: missing $(MRS_LINUX)" >&2; exit 2; }; \
	mkdir -p "$(HERE)/ref"; \
	ln -sfn "$(MRS_APP)" "$(HERE)/ref/MounRiver Studio 2.app"; \
	ln -sfn "$(MRS_LINUX)" "$(HERE)/ref/MRS_Toolchain_Linux_X64_V250"; \
	cd "$(HERE)" && scripts/extract-wch-toolchain.sh

# ---------------------------------------------------------------------------
# verify-12.2.0
# ---------------------------------------------------------------------------
verify-12.2.0:
	@set -euo pipefail; \
	cd "$(HERE)"; \
	test -d "ref/gcc/$(PLATFORM)/12.2.0/bin" || { echo "verify-12.2.0: official package missing at ref/gcc/$(PLATFORM)/12.2.0 — run 'make official' or install it per the README" >&2; exit 2; }; \
	ls -d ref/wch-evt/Qingke* >/dev/null 2>&1 || { echo "verify-12.2.0: EVT corpus missing — run 'make evt'" >&2; exit 2; }; \
	if [ -e "$(PROJECT_12)" ]; then \
	    echo "verify-12.2.0: source tree already exists: $(PROJECT_12)" >&2; \
	    echo "verify-12.2.0: prepare-sources.sh refuses to overwrite it; remove it first (rm -rf) to re-run from pristine sources." >&2; \
	    exit 2; \
	fi; \
	if [ -d "$(SRC_DOWNLOADS_12)" ]; then \
	    if [ -d "$(DOWNLOADS_12)" ]; then \
	        echo "verify-12.2.0: downloads already present, left as is: $(DOWNLOADS_12)"; \
	    else \
	        mkdir -p "$$(dirname "$(DOWNLOADS_12)")"; \
	        cp -cR "$(SRC_DOWNLOADS_12)" "$(DOWNLOADS_12)"; \
	        echo "verify-12.2.0: seeded downloads from $(SRC_DOWNLOADS_12) (APFS clone)"; \
	    fi; \
	else \
	    echo "verify-12.2.0: no local downloads seed; prepare-sources.sh will fetch the pinned URLs"; \
	fi; \
	scripts/ci/prepare-sources.sh 12.2.0; \
	project=$$(cd "$(PROJECT_12)" && pwd -P); \
	previous=$$(readlink "$(LITERAL_XPACK)" 2>/dev/null || true); \
	echo "verify-12.2.0: literal_symlink_before=$${previous:-(absent)}"; \
	restore() { if [ -n "$$previous" ]; then ln -sfn "$$previous" "$(LITERAL_XPACK)"; else rm -f "$(LITERAL_XPACK)"; fi; }; \
	trap restore EXIT INT TERM; \
	ln -sfn "$$project" "$(LITERAL_XPACK)"; \
	BUILD_JOBS=$(BUILD_JOBS) scripts/build-toolchain-12.2.0.sh "$$project"; \
	trap - EXIT INT TERM; \
	restore; \
	now=$$(readlink "$(LITERAL_XPACK)" 2>/dev/null || true); \
	[ "$$now" = "$$previous" ] || { echo "verify-12.2.0: literal symlink NOT restored: '$$now' != '$$previous'" >&2; exit 2; }; \
	echo "verify-12.2.0: literal_symlink_after=$${now:-(absent)} (restored)"; \
	scripts/evt-golden.sh 12.2.0; \
	rows=$$(awk -F'\t' '$$1 !~ /^#/ && $$1 != "slug" && $$3 == "gate" { n++ } END { print n+0 }' "$(MANIFEST_12)"); \
	echo "verify-12.2.0: manifest_gate_rows=$$rows expected=$(GATE_TOTAL_12)"; \
	[ "$$rows" -eq $(GATE_TOTAL_12) ] || { echo "verify-12.2.0: manifest gate rows $$rows != $(GATE_TOTAL_12) — the corpus is incomplete; do NOT compare against this manifest" >&2; exit 2; }; \
	application="$$project/build/$(PLATFORM)/application"; \
	log="$(HERE)/tmp/verify-12.2.0-compare.log"; \
	scripts/evt-compare.sh 12.2.0 "$$application" 2>&1 | tee "$$log"; \
	summary=$$(awk -F'\t' '$$1 == "SUMMARY" { print }' "$$log"); \
	[ -n "$$summary" ] || { echo "verify-12.2.0: no SUMMARY row in $$log" >&2; exit 2; }; \
	printf 'verify-12.2.0: %s\n' "$$summary"; \
	echo "$$summary" | grep -q "gate_pass=$(GATE_TOTAL_12)" || { echo "verify-12.2.0: SUMMARY gate_pass is not $(GATE_TOTAL_12)" >&2; exit 2; }; \
	echo "$$summary" | grep -q 'gate_fail=0' || { echo "verify-12.2.0: SUMMARY gate_fail is not 0" >&2; exit 2; }; \
	echo "verify-12.2.0: PASS"

# ---------------------------------------------------------------------------
# verify-act
# ---------------------------------------------------------------------------
verify-act:
	@set -euo pipefail; \
	cd "$(HERE)" && scripts/ci/act-verify.sh $(ACT_JOB)

# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------
verify:
	@$(MAKE) verify-12.2.0
	@$(MAKE) verify-act
