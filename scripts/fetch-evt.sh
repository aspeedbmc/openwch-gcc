#!/usr/bin/env bash
#
# fetch-evt.sh — 获取并解包 openwch 的 WCH EVT 语料（ref/wch-evt 下的 Qingke*/ 目录树）。
#
# 语料树体积过大（25065 个文件 / 约 205 MiB 压缩包），不入公开仓库；仓库只保留
# ref/wch-evt 的小件（README.md、download-evt.sh、tools/、tests/、patches/）。
# 本脚本把语料包取回并解开到 ref/wch-evt/ 下，得到与「干净 checkout」一致的未打补丁状态；
# 加 --apply 可在解包后运行 ref/wch-evt/patches/apply.sh，与 CI 的 checkout + apply 语义相同。
#
# 依赖：bash 3.2+、tar、coreutils（sha256sum；macOS 上回退到 shasum）。
#       唯一额外依赖 curl —— 仅在使用 --url / EVT_PACK_URL 下载时需要，--file 模式不需要。
#       --apply 另需 ref/wch-evt/patches/apply.sh 自身的依赖（patch、perl）。
#
# 用法：
#   scripts/fetch-evt.sh [--url URL | --file PATH] [--apply] [--force]
#
#   --url URL     从该 URL 下载语料包；缺省取环境变量 EVT_PACK_URL。
#   --file PATH   使用本地已有的语料包，不联网。与 --url 互斥。
#   --apply       解包后运行 ref/wch-evt/patches/apply.sh。
#   --force       ref/wch-evt/ 下已存在 Qingke* 目录时，删除它们后重新解包（默认拒绝）。
#   -h, --help    显示本用法。
#
# 校验：包的 SHA-256 必须与下面的 EVT_PACK_SHA256 常量逐字节相符，否则拒绝解包。
#       该校验没有放宽开关 —— 语料是逐字节一致性 gate 的输入，不容许来源不明的副本。
#
set -euo pipefail

# ---- 语料包常量（随语料树变更同步更新）-------------------------------------
EVT_PACK_NAME='openwch-evt-d5added7.tar.gz'
EVT_PACK_SHA256='18b7ddd6cb6bf148881648800a33097d3ff035019fe3ded55689aa0a3c646b58'
# 包内容 = `git archive HEAD:ref/wch-evt` 的全树（含小件），本脚本只解出 Qingke*/。
EVT_TREE='d5added79482e67807367e3156454c60c00ff646'
EVT_QINGKE_FILES=25065   # 期望解出的文件数（含 2 个 .DS_Store，见下方跳过说明）
# ---------------------------------------------------------------------------

program_name=$(basename -- "$0")

log()  { printf '%s\n' "$*"; }
die()  { printf '%s: %s\n' "$program_name" "$*" >&2; exit 1; }

usage() {
    cat <<EOF
用法：$program_name [--url URL | --file PATH] [--apply] [--force]

获取并解包 WCH EVT 语料（ref/wch-evt 下的 Qingke*/ 目录树，$EVT_QINGKE_FILES 个文件）。

  --url URL     从该 URL 下载语料包；缺省取环境变量 EVT_PACK_URL。
  --file PATH   使用本地已有的语料包，不联网。与 --url 互斥。
  --apply       解包后运行 ref/wch-evt/patches/apply.sh。
  --force       ref/wch-evt/ 下已存在 Qingke* 目录时，删除它们后重新解包（默认拒绝）。
  -h, --help    显示本用法。

语料包：$EVT_PACK_NAME
SHA-256：$EVT_PACK_SHA256
源 tree：$EVT_TREE
校验不通过一律拒绝解包，没有放宽开关。
EOF
}

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum -- "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 -- "$1" | awk '{print $1}'
    else
        die '找不到 sha256sum 或 shasum，无法校验语料包'
    fi
}

# ---- 参数 -----------------------------------------------------------------
pack_url=''
pack_file=''
do_apply=0
do_force=0

while [ $# -gt 0 ]; do
    case "$1" in
        --url)   [ $# -ge 2 ] || die '--url 需要一个参数'; pack_url=$2; shift 2 ;;
        --url=*) pack_url=${1#--url=}; shift ;;
        --file)  [ $# -ge 2 ] || die '--file 需要一个参数'; pack_file=$2; shift 2 ;;
        --file=*) pack_file=${1#--file=}; shift ;;
        --apply) do_apply=1; shift ;;
        --force) do_force=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "未知参数：$1（用 --help 查看用法）" ;;
    esac
done

[ -n "$pack_url" ] && [ -n "$pack_file" ] && die '--url 与 --file 互斥，只能给一个'

# 发布后的正式分发地址（GitHub Release 资产；语料树变更时随 EVT_PACK_NAME/SHA256 同步更新）。
EVT_PACK_DEFAULT_URL='https://github.com/aspeedbmc/openwch-gcc/releases/download/evt-pack-d5added7/openwch-evt-d5added7.tar.gz'

if [ -z "$pack_file" ] && [ -z "$pack_url" ]; then
    pack_url=${EVT_PACK_URL:-$EVT_PACK_DEFAULT_URL}
fi

if [ -z "$pack_file" ] && [ -z "$pack_url" ]; then
    die "未指定语料包来源。三选一：
  1) 设置环境变量 EVT_PACK_URL 指向语料包 ${EVT_PACK_NAME}
  2) 传 --url <URL>
  3) 已有本地副本时传 --file <路径>
语料包也可以自行重建：从 WCH 官网下载 EVT 包后按 ref/wch-evt/README.md 组织目录树。"
fi

# ---- 路径 -----------------------------------------------------------------
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(CDPATH= cd -- "$script_dir/.." && pwd)
dest_dir="$repo_dir/ref/wch-evt"

mkdir -p -- "$dest_dir"

# 已存在的 Qingke* 目录：默认拒绝（小件在库，dest_dir 非空是常态，不作为判据）
existing=()
while IFS= read -r -d '' d; do
    existing+=("$d")
done < <(find "$dest_dir" -maxdepth 1 -type d -name 'Qingke*' -print0 | sort -z)

if [ "${#existing[@]}" -gt 0 ]; then
    if [ "$do_force" -eq 0 ]; then
        printf '%s: %s 下已存在 %d 个 Qingke* 语料目录，拒绝覆盖：\n' \
            "$program_name" "$dest_dir" "${#existing[@]}" >&2
        printf '  %s\n' "${existing[@]##*/}" >&2
        printf '确认要重新解包请加 --force（会先删除上述目录）。\n' >&2
        exit 1
    fi
    log "--force：删除已存在的 ${#existing[@]} 个 Qingke* 语料目录"
    for d in "${existing[@]}"; do
        printf '  rm -rf %s\n' "$d"
        rm -rf -- "$d"
    done
fi

# ---- 临时区（建在 dest_dir 内，保证 mv 是同盘 rename）-----------------------
work_dir=$(mktemp -d "$dest_dir/.fetch-evt.tmp.XXXXXX")
cleanup() { rm -rf -- "$work_dir"; }
trap cleanup EXIT HUP INT TERM

# ---- 取包 -----------------------------------------------------------------
if [ -n "$pack_file" ]; then
    [ -f "$pack_file" ] || die "语料包不存在：$pack_file"
    pack_path=$(CDPATH= cd -- "$(dirname -- "$pack_file")" && pwd)/$(basename -- "$pack_file")
    log "使用本地语料包：$pack_path"
else
    command -v curl >/dev/null 2>&1 || die '下载需要 curl；或改用 --file 指向本地副本'
    pack_path="$work_dir/$EVT_PACK_NAME"
    log "下载语料包：$pack_url"
    curl -fSL --retry 3 --retry-delay 2 -o "$pack_path" -- "$pack_url" \
        || die "下载失败：$pack_url"
fi

# ---- 校验（fail-closed，无放宽开关）----------------------------------------
log '校验 SHA-256 ...'
actual_sha=$(sha256_of "$pack_path")
if [ "$actual_sha" != "$EVT_PACK_SHA256" ]; then
    die "语料包 SHA-256 不匹配，拒绝解包：
  文件   : $pack_path
  期望   : $EVT_PACK_SHA256
  实际   : $actual_sha"
fi
log "SHA-256 OK: $actual_sha"

# ---- 解包 -----------------------------------------------------------------
extract_dir="$work_dir/extract"
mkdir -p -- "$extract_dir"
log '解包 ...'
tar -xzf "$pack_path" -C "$extract_dir"

# 只取 Qingke*/ 成员；包内其余小件（README.md/tools/tests/patches/顶层 .DS_Store）
# 已在仓库里，丢弃即可。
staged=()
while IFS= read -r -d '' d; do
    staged+=("$d")
done < <(find "$extract_dir" -maxdepth 1 -type d -name 'Qingke*' -print0 | sort -z)

[ "${#staged[@]}" -gt 0 ] || die "语料包内没有 Qingke*/ 目录，包结构不符预期：$pack_path"

# 跳过 macOS 目录元数据，不写进用户的树
skipped_ds=0
while IFS= read -r -d '' f; do
    printf '  跳过 %s\n' "${f#$extract_dir/}"
    rm -f -- "$f"
    skipped_ds=$((skipped_ds + 1))
done < <(find "${staged[@]}" -type f -name '.DS_Store' -print0)

for d in "${staged[@]}"; do
    mv -- "$d" "$dest_dir/"
done

extracted=$(cd -- "$dest_dir" && find "${staged[@]##*/}" -type f | wc -l | tr -d ' ')

log "解出 ${#staged[@]} 个语料目录、$extracted 个文件（跳过 $skipped_ds 个 .DS_Store；语料树共 $EVT_QINGKE_FILES 个跟踪文件）"
log "源 tree: $EVT_TREE"

# ---- 打补丁 ---------------------------------------------------------------
if [ "$do_apply" -eq 1 ]; then
    apply_sh="$dest_dir/patches/apply.sh"
    [ -x "$apply_sh" ] || [ -f "$apply_sh" ] \
        || die "找不到 $apply_sh —— 仓库里的 ref/wch-evt/patches/ 缺失？"
    log "运行 $apply_sh"
    sh "$apply_sh"
    log 'apply.sh 完成'
fi

log '完成。'
