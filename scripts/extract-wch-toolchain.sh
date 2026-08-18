#!/usr/bin/env bash
# Extract the WCH GCC toolchains bundled with MounRiver Studio into ref/gcc/<platform>/<gcc-version>/.
# Sources currently present in this repository:
#   ref/MounRiver Studio 2.app        -> darwin-arm64 (RISC-V GCC 8.2.0 and
#                                         arm-none-eabi GCC 9.3.1 are
#                                         x86_64/Rosetta host builds)
#   ref/MRS_Toolchain_Linux_X64_V250  -> linux-amd64 (the current input only
#                                         contains RISC-V Embedded GCC15)
# The platform component names the host distribution.  Compiler triples name
# targets independently; arm-none-eabi is not Darwin-specific, and a Linux
# package can be added to the Linux source input without changing that model.
# The version directory name is taken from lib/gcc/<triple>/<version>/ inside each toolchain.
set -euo pipefail
shopt -s nullglob

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DARWIN_SRC="$ROOT/ref/MounRiver Studio 2.app/Contents/Resources/app/resources/darwin/components/WCH/Toolchain"
LINUX_SRC="$ROOT/ref/MRS_Toolchain_Linux_X64_V250/Toolchain"
DEST_BASE="$ROOT/ref/gcc"

seen=""
summary=""

extract_one() {
  local src="$1" platform="$2"
  local name ver dest
  name="$(basename "$src")"

  local vdirs=("$src"/lib/gcc/*/[0-9]*/)
  if [ "${#vdirs[@]}" -ne 1 ]; then
    echo "ERROR: $name: expected exactly one lib/gcc/<triple>/<version>/, found ${#vdirs[@]}" >&2
    return 1
  fi
  ver="$(basename "${vdirs[0]}")"

  case " $seen " in
    *" $platform/$ver "*)
      echo "ERROR: $name: duplicate version $platform/$ver" >&2
      return 1
      ;;
  esac
  seen="$seen $platform/$ver"

  dest="$DEST_BASE/$platform/$ver"
  echo ">> $name -> ref/gcc/$platform/$ver"
  rm -rf "$dest"
  mkdir -p "$dest"
  # -c: APFS clonefile — instant and space-free on the same volume
  cp -cR "$src/." "$dest/"

  local gccs=("$dest"/bin/*-gcc)
  if [ "${#gccs[@]}" -eq 0 ] || [ ! -x "${gccs[0]}" ]; then
    echo "ERROR: $platform/$ver: no executable bin/*-gcc after copy" >&2
    return 1
  fi
  summary="$summary  $platform  $ver  $(basename "${gccs[0]}")\n"
}

[ -d "$DARWIN_SRC" ] || { echo "ERROR: darwin source not found: $DARWIN_SRC" >&2; exit 1; }
[ -d "$LINUX_SRC" ] || { echo "ERROR: linux source not found: $LINUX_SRC" >&2; exit 1; }

for tc in "$DARWIN_SRC"/*/; do
  extract_one "${tc%/}" darwin-arm64
done
for tc in "$LINUX_SRC"/*/; do
  extract_one "${tc%/}" linux-amd64
done

printf '\nExtracted (ref/gcc/<platform>/<version>  <gcc>):\n'
printf '%b' "$summary"
