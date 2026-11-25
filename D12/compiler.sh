#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
projet="$PWD"
revision=09d0b4d15228b3efb6fd765f1e1574f521df2e27
cible=mks_robin_nano_v3_usb_flash_drive
travail="$(mktemp -d)"
trap 'rm -rf "$travail"' EXIT
python3 -m venv "$travail/venv"
"$travail/venv/bin/python" -m pip install 'platformio==6.1.18'
git clone --depth 1 --branch 2.1.2.1 https://github.com/MarlinFirmware/Marlin.git "$travail/Marlin"
cd "$travail/Marlin"
test "$(git rev-parse HEAD)" = "$revision"
git apply "$projet/butee-Y.patch"
cp "$projet/Configuration.h" "$projet/Configuration_adv.h" Marlin/
"$travail/venv/bin/pio" run -e "$cible"
"$travail/venv/bin/python" "$projet/verifier.py" ".pio/build/$cible/Robin_nano_v3.bin"
sortie="$(mktemp -d "$projet/compilation-XXXXXXXX")"
cp ".pio/build/$cible/Robin_nano_v3.bin" "$sortie/"
if [[ -d ".pio/build/$cible/assets" ]]; then
  cp -R ".pio/build/$cible/assets" "$sortie/"
fi
printf 'Compilation vérifiée dans %s\n' "$sortie"
