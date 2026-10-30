#!/bin/sh
# Hakee äänivalinnan näytteet (web/voices/<ääni>.wav): sama lause kaikilla äänillä, jotta äänet voi verrata
# valikossa (web/app.js: VOICE_SAMPLE). Näytteet ovat sovelluspaketissa, joten ne toimivat jo ensimmäisellä
# käynnistyksellä ilman verkkoyhteyttä; muut ääntämiset haetaan palvelusta kuten ennenkin.
# LÄHDE: Divvunin ja Giellateknon puhesynteesi (UiT), api-giellalt.uit.no. Divvun on hyväksynyt API:n käytön
# (2026-10-29); näytteiden mukaan ottamista on kysytty 2026-10-30. Ks. CREDITS.md.
cd "$(dirname "$0")" || exit 1

TEXT="Bures boahtin Sápmái"  # sama kuin web/app.js: VOICE_SAMPLE
mkdir -p web/voices || exit 1
for voice in biret mahtte sunna; do
    curl -sSf -X POST -H "Content-Type: application/json" -d "{\"text\": \"$TEXT\"}" \
        -o "web/voices/$voice.wav" "https://api-giellalt.uit.no/tts/se/$voice" || { echo "$voice: haku epäonnistui"; exit 1; }
    echo "web/voices/$voice.wav: $(wc -c < "web/voices/$voice.wav") tavua"
done
