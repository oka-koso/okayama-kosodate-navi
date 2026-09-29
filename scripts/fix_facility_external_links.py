#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "js" / "facilities.js"

HOTFIX = r'''
// External-link hotfix:
// facility card/popup ancestors may still have delegated click handlers.
// Capture these links before other delegated handlers and open the real URL.
document.addEventListener('click', (event) => {
  const link = event.target.closest(
    'a.facility-site-link, a.facility-city-link'
  );

  if (!link) return;

  const href = link.getAttribute('href');

  if (!href) return;

  event.preventDefault();
  event.stopPropagation();
  event.stopImmediatePropagation();

  const newWindow = window.open(
    href,
    '_blank',
    'noopener,noreferrer'
  );

  // If popup opening is blocked, fall back to same-tab navigation.
  if (!newWindow) {
    window.location.href = href;
  }
}, true);
'''

def main():
    text = TARGET.read_text(encoding="utf-8")

    marker = "// External-link hotfix:"

    if marker in text:
        print("[external-link-hotfix-v1] already installed.")
        return

    text = text.rstrip() + "\n\n" + HOTFIX.strip() + "\n"

    TARGET.write_text(text, encoding="utf-8")

    # Basic verification.
    check = TARGET.read_text(encoding="utf-8")

    if "a.facility-site-link, a.facility-city-link" not in check:
        raise RuntimeError("hotfix was not written.")

    print("[external-link-hotfix-v1] installed successfully.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[external-link-hotfix-v1] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
