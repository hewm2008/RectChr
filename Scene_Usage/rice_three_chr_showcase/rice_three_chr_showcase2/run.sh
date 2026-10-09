#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
perl generate_showcase_data.pl
../../../../../bin/RectChr -InConf in.conf -OutPut rice_three_chr_showcase.svg
