#!/usr/bin/env bash
# Download WCH EVT archives from the URLs recorded by Chrome and unpack them
# into the Qingke-named directories used by this reference tree.

set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
tmp_dir="$script_dir/tmp"
history_override="${CHROME_HISTORY:-}"
dry_run=0
selected=()

# archive name in Chrome history | destination directory in this tree
download_specs=(
  "CH32V006EVT|QingkeV2AC_CH32V00x"
  "CH32V103EVT|QingkeV3A_CH32V103"
  "CH32V205EVT|QingkeV3B_CH32V205"
  "CH587EVT|QingkeV3C_CH587_EVT"
  "CH32X315EVT|QingkeV3F_CH32X315_EVT"
  "CH32V20xEVT|QingkeV4BC_CH32V20x"
  "CH32V307EVT|QingkeV4F_CH32V30x"
  "CH32H417EVT|QingkeV5F_CH32H417EVT"
)

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: ./download-evt.sh [options] [archive-or-directory ...]

Look up completed WCH EVT downloads in Chrome's History database, download
the archive to ./tmp, unpack its EVT/ directory, and rename it to the
corresponding Qingke directory.

Options:
  --dry-run          Print the URLs and commands without changing files.
  --history PATH     Use PATH instead of Chrome's default History database.
  -h, --help         Show this help.

With no archive or directory arguments, all entries are processed. An
existing destination directory is skipped during a normal run. Selectors can
be either archive names such as CH32V20xEVT or destination names such as
QingkeV4BC_CH32V20x.

The CHROME_HISTORY environment variable is equivalent to --history PATH.
EOF
}

while (($# > 0)); do
  case "$1" in
    --dry-run)
      dry_run=1
      shift
      ;;
    --history)
      (($# >= 2)) || die "--history requires a path"
      history_override="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while (($# > 0)); do
        selected+=("$1")
        shift
      done
      ;;
    *)
      selected+=("$1")
      shift
      ;;
  esac
done

for command_name in sqlite3 wget unzip mktemp; do
  command -v "$command_name" >/dev/null 2>&1 || die "required command not found: $command_name"
done

find_history() {
  local user_home="${HOME:-}"
  local candidate
  local candidates=(
    "$user_home/Library/Application Support/Google/Chrome/Default/History"
    "$user_home/Library/Application Support/Chromium/Default/History"
    "$user_home/.config/google-chrome/Default/History"
    "$user_home/.config/chromium/Default/History"
  )

  if [[ -n "$history_override" ]]; then
    [[ -f "$history_override" ]] || die "Chrome History database not found: $history_override"
    printf '%s\n' "$history_override"
    return
  fi

  for candidate in "${candidates[@]}"; do
    if [[ -f "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return
    fi
  done

  die "Chrome History database not found; set CHROME_HISTORY or use --history PATH"
}

find_download_url() {
  local archive_name="$1"
  local history_uri="$2"

  # Chrome stores the page URL in downloads.tab_url, but the actual download
  # URL is in downloads_url_chains. The latest chain entry is the final URL.
  sqlite3 -batch -noheader "$history_uri" "
    SELECT c.url
      FROM downloads AS d
      JOIN downloads_url_chains AS c ON c.id = d.id
     WHERE d.state = 1
       AND lower(d.target_path) LIKE '%' || lower('$archive_name') || '%.zip'
       AND lower(c.url) LIKE '%wch.cn%'
       AND c.chain_index = (
             SELECT max(c2.chain_index)
               FROM downloads_url_chains AS c2
              WHERE c2.id = d.id
           )
     ORDER BY d.end_time DESC, d.id DESC
     LIMIT 1;
  "
}

selector_matches() {
  local archive_name="$1"
  local destination_name="$2"
  local selector

  if (("${#selected[@]} == 0")); then
    return 0
  fi

  for selector in "${selected[@]}"; do
    if [[ "$selector" == "$archive_name" || "$selector" == "$destination_name" ]]; then
      return 0
    fi
  done
  return 1
}

validate_selectors() {
  local selector spec archive_name destination_name found

  if ((${#selected[@]} == 0)); then
    return
  fi

  for selector in "${selected[@]}"; do
    found=0
    for spec in "${download_specs[@]}"; do
      IFS='|' read -r archive_name destination_name <<< "$spec"
      if [[ "$selector" == "$archive_name" || "$selector" == "$destination_name" ]]; then
        found=1
        break
      fi
    done
    ((found)) || die "unknown archive or directory selector: $selector"
  done
}

process_download() {
  local archive_name="$1"
  local destination_name="$2"
  local destination="$script_dir/$destination_name"
  local wch_zip archive_path stage_dir

  if [[ -e "$destination" && "$dry_run" -eq 0 ]]; then
    printf 'skip %s: destination already exists (%s)\n' "$archive_name" "$destination_name"
    return
  fi

  wch_zip="$(find_download_url "$archive_name" "$history_uri")"
  [[ -n "$wch_zip" ]] || die "no completed Chrome download found for $archive_name"

  case "$wch_zip" in
    http://*|https://*) ;;
    *) die "unexpected download URL for $archive_name: $wch_zip" ;;
  esac

  archive_path="$tmp_dir/$archive_name.zip"

  if ((dry_run)); then
    printf '%s -> %s\n' "$archive_name" "$destination_name"
    printf '  URL: %s\n' "$wch_zip"
    printf '  wget -O %q %q\n' "$archive_path" "$wch_zip"
    printf '  unzip %q\n' "$archive_path"
    printf '  mv EVT %q\n' "$destination"
    return
  fi

  mkdir -p "$tmp_dir"
  printf 'download %s -> %s\n' "$archive_name" "$destination_name"
  # In wget, lowercase -o selects a log file; uppercase -O writes the archive.
  wget --tries=3 --timeout=30 -O "$archive_path" "$wch_zip"

  stage_dir="$(mktemp -d "$tmp_dir/${archive_name}.XXXXXX")"
  if ! unzip -q "$archive_path" -d "$stage_dir"; then
    rm -rf "$stage_dir"
    die "cannot unpack $archive_path"
  fi

  if [[ ! -d "$stage_dir/EVT" ]]; then
    rm -rf "$stage_dir"
    die "archive does not contain an EVT/ directory: $archive_path"
  fi

  if [[ -e "$destination" ]]; then
    rm -rf "$stage_dir"
    die "destination appeared during download; refusing to overwrite: $destination"
  fi

  mv "$stage_dir/EVT" "$destination"
  rm -rf "$stage_dir"
}

validate_selectors
history_path="$(find_history)"
history_uri="file:${history_path}?immutable=1"

if ((dry_run == 0)); then
  mkdir -p "$tmp_dir"
fi

for spec in "${download_specs[@]}"; do
  IFS='|' read -r archive_name destination_name <<< "$spec"
  if selector_matches "$archive_name" "$destination_name"; then
    process_download "$archive_name" "$destination_name"
  fi
done
