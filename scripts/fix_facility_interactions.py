#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "js" / "facilities.js"

def main():
    text = TARGET.read_text(encoding="utf-8")

    text = text.replace(
        '<article class="facility-card" id="facility-${esc(f.id)}" data-facility-id="${esc(f.id)}">',
        '<article class="facility-card" id="facility-${esc(f.id)}">'
    )

    text = text.replace(
        'data-facility-id="${esc(f.id)}">${esc(f.name)}</a>',
        'data-scroll-card-id="${esc(f.id)}">${esc(f.name)}</a>'
    )
    text = text.replace(
        'data-facility-id="${esc(f.id)}">下の施設カードを見る ↓</a>',
        'data-scroll-card-id="${esc(f.id)}">下の施設カードを見る ↓</a>'
    )

    focus_pattern = re.compile(
        r'function focusMarker\(id\) \{.*?\n\}\n\nfunction clearMarkers',
        re.S
    )

    focus_replacement = r'''function focusMarker(id) {
  const marker = markerById.get(id);

  if (!marker) {
    console.warn('Marker not found for facility:', id);
    return;
  }

  const mapEl = document.getElementById('map');

  if (mapEl) {
    mapEl.scrollIntoView({
      behavior: 'smooth',
      block: 'center'
    });
  }

  window.setTimeout(() => {
    map.invalidateSize();

    const ll = marker.getLatLng();

    map.setView(ll, 16, {
      animate: true
    });

    marker.openPopup();
  }, 350);
}

function clearMarkers'''

    text, n1 = focus_pattern.subn(focus_replacement, text, count=1)
    if n1 != 1:
        raise RuntimeError("focusMarker() の置換に失敗しました。")

    interaction_pattern = re.compile(
        r'function bindInteractions\(\) \{.*?\n\}\n\nasync function init',
        re.S
    )

    interaction_replacement = r'''function bindInteractions() {
  ['q', 'ward', 'type', 'service'].forEach((id) => {
    const el = $('#' + id);
    if (!el) return;

    el.addEventListener(
      id === 'q' ? 'input' : 'change',
      render
    );
  });

  document.addEventListener('click', (event) => {
    // Card -> map
    const mapBtn = event.target.closest('[data-map-id]');

    if (mapBtn) {
      const id = mapBtn.dataset.mapId;

      if (id) {
        event.preventDefault();
        event.stopPropagation();
        focusMarker(id);
      }

      return;
    }

    // Popup -> card
    const scrollLink =
      event.target.closest('[data-scroll-card-id]');

    if (scrollLink) {
      const id = scrollLink.dataset.scrollCardId;

      if (id) {
        event.preventDefault();
        event.stopPropagation();
        scrollToCard(id);
      }

      return;
    }

    // External links and tel links are left to normal browser behavior.
  });
}

async function init'''

    text, n2 = interaction_pattern.subn(
        interaction_replacement,
        text,
        count=1
    )
    if n2 != 1:
        raise RuntimeError("bindInteractions() の置換に失敗しました。")

    TARGET.write_text(text, encoding="utf-8")

    if 'class="facility-card" id="facility-${esc(f.id)}" data-facility-id=' in text:
        raise RuntimeError("カード全体の data-facility-id が残っています。")

    if "event.target.closest('[data-facility-id]')" in text:
        raise RuntimeError("旧クリック横取り処理が残っています。")

    print("[interaction-hotfix-v3] js/facilities.js patched successfully.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[interaction-hotfix-v3] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
