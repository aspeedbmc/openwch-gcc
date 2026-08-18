#!/bin/sh
set -eu

patch_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(CDPATH= cd -- "$patch_dir/.." && pwd)

# Some WCH project files use CRLF while the unified patch is stored with LF.
# Normalize only the files touched by these patches while patch(1) runs, then
# put their original line-ending style back before returning to the caller.
temporary_dir=$(mktemp -d "${TMPDIR:-/tmp}/wch-evt-patch.XXXXXX")
crlf_files="$temporary_dir/crlf-files"
restore_line_endings() {
    if [ -f "$crlf_files" ]; then
        while IFS= read -r target; do
            [ -f "$target" ] || continue
            perl -pi -e 's/\r?\n/\r\n/g' "$target"
        done < "$crlf_files"
    fi
}
cleanup() {
    restore_line_endings
    rm -rf "$temporary_dir"
}
trap cleanup EXIT HUP INT TERM

for patch_file in "$patch_dir"/*.patch; do
    while IFS= read -r relative; do
        [ -n "$relative" ] || continue
        target="$repo_dir/$relative"
        if [ -f "$target" ] && grep -q "$(printf '\r')" "$target"; then
            printf '%s\n' "$target" >> "$crlf_files"
            perl -pi -e 's/\r\n/\n/g' "$target"
        fi
    done <<EOF
$(sed -n 's#^diff --git a/\(.*\) b/.*$#\1#p' "$patch_file")
EOF

    if patch --dry-run --batch -N -l -d "$repo_dir" -p1 < "$patch_file" >/dev/null 2>&1; then
        patch --batch -N -l -d "$repo_dir" -p1 < "$patch_file"
    elif patch --dry-run --batch -N -R -l -d "$repo_dir" -p1 < "$patch_file" >/dev/null 2>&1; then
        echo "already applied: $(basename "$patch_file")"
    else
        echo "cannot apply: $(basename "$patch_file")" >&2
        exit 1
    fi
done
