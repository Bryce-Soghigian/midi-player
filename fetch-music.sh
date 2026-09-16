#!/bin/sh
# Download public-domain classical piano MIDI files from mfiles.co.uk.
# These are free for personal use; they are not redistributed with this repo.
set -e
cd "$(dirname "$0")"
mkdir -p music && cd music

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
BASE="https://www.mfiles.co.uk/downloads"

get() {
  [ -f "$2" ] && { echo "  have  $2"; return; }
  if curl -sS -m 25 -fL -A "$UA" -e "https://www.mfiles.co.uk/classical-midi.htm" \
       -o "$2" "$BASE/$1" && head -c 4 "$2" | grep -q MThd; then
    echo "  got   $2"
  else
    echo "  FAIL  $1" >&2; rm -f "$2"
  fi
}

get debussy-clair-de-lune.mid                  clair-de-lune.mid
get Gymnopedie1.mid                            satie-gymnopedie-1.mid
get Gnossienne1.mid                            satie-gnossienne-1.mid
get fur-elise.mid                              beethoven-fur-elise.mid
get moonlight-movement1.mid                    beethoven-moonlight-1.mid
get chopin-nocturne-op9-no2.mid                chopin-nocturne-op9-2.mid
get prelude15.mid                              chopin-raindrop-prelude.mid
get minute-waltz.mid                           chopin-minute-waltz.mid
get book1-prelude01.mid                        bach-prelude-c-bwv846.mid
get petzold-minuet-in-g-major-bwv114.mid       petzold-minuet-in-g.mid
get sonata-in-c.mid                            mozart-sonata-k545-1.mid
get alla-turca.mid                             mozart-alla-turca.mid
get arabesque1.mid                             debussy-arabesque-1.mid
get reverie-traumerei.mid                      schumann-traumerei.mid
get rachmaninoff-prelude-in-c-sharp-minor.mid  rachmaninoff-prelude-csharp.mid
get pachelbels-canon-arranged.mid              pachelbel-canon-piano.mid

cd ..
mkdir -p scores && cd scores
if [ -f chopin-raindrop-prelude-op28-no15.pdf ]; then
  echo "  have  chopin-raindrop-prelude-op28-no15.pdf"
elif curl -sS -m 60 -fL -A "$UA" -e "https://www.mfiles.co.uk/scores/prelude15.htm" \
       -o chopin-raindrop-prelude-op28-no15.pdf \
       "https://www.mfiles.co.uk/scores/prelude15.pdf" \
     && head -c 4 chopin-raindrop-prelude-op28-no15.pdf | grep -q "%PDF"; then
  echo "  got   chopin-raindrop-prelude-op28-no15.pdf"
else
  echo "  FAIL  score PDF" >&2
  rm -f chopin-raindrop-prelude-op28-no15.pdf
fi

echo "done"
