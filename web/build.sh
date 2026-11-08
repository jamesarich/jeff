#!/usr/bin/env sh
# Assemble the deployable site in web/dist from the repo's assets.
# Clips are re-encoded to MP3 because iOS Safari does not play .ogg.
set -eu

root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/web/dist"

rm -rf "$out"
mkdir -p "$out/sounds"

cp "$root/web/index.html" "$root/web/style.css" "$root/web/app.js" "$root/web/logic.js" "$out/"
cp "$root/calibration.json" "$out/calibration.json"
cp "$root/assets/jeff.jpg" "$out/jeff.jpg"

clips=""
for src in "$root"/sounds/*.ogg "$root"/sounds/*.wav "$root"/sounds/*.mp3; do
  [ -f "$src" ] || continue
  name="$(basename "${src%.*}").mp3"
  ffmpeg -loglevel error -y -i "$src" -codec:a libmp3lame -q:a 4 "$out/sounds/$name"
  clips="$clips${clips:+,}\"sounds/$name\""
done
printf '{"clips":[%s]}\n' "$clips" > "$out/sounds.json"

echo "built $out"
ls -la "$out" "$out/sounds"
