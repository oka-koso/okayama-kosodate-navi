(() => {
  'use strict';
  function setup(panel, mapEl) {
    if (!panel || !mapEl) return;
    panel.classList.add('okn-map-panel');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'okn-map-fullscreen-toggle';
    button.textContent = '⛶ 全画面表示';
    button.setAttribute('aria-pressed', 'false');
    button.setAttribute('aria-label', '地図を全画面表示');
    panel.appendChild(button);
    let active = false;
    let previousFocus = null;
    let savedScroll = 0;
    const resize = () => {
      window.dispatchEvent(new Event('resize'));
      requestAnimationFrame(() => window.dispatchEvent(new Event('resize')));
      setTimeout(() => window.dispatchEvent(new Event('resize')), 180);
    };
    function setActive(next) {
      if (active === next) return;
      active = next;
      if (next) {
        previousFocus = document.activeElement;
        savedScroll = window.scrollY;
        document.body.classList.add('okn-map-fullscreen-open');
        panel.classList.add('okn-map-is-fullscreen');
        button.textContent = '× 全画面を閉じる';
        button.setAttribute('aria-label', '地図の全画面表示を閉じる');
      } else {
        panel.classList.remove('okn-map-is-fullscreen');
        document.body.classList.remove('okn-map-fullscreen-open');
        button.textContent = '⛶ 全画面表示';
        button.setAttribute('aria-label', '地図を全画面表示');
        window.scrollTo(0, savedScroll);
      }
      button.setAttribute('aria-pressed', String(next));
      resize();
      if (next) button.focus({preventScroll:true});
      else if (previousFocus && previousFocus !== button && typeof previousFocus.focus === 'function') {
        previousFocus.focus({preventScroll:true});
      }
    }
    button.addEventListener('click', () => setActive(!active));
    document.addEventListener('keydown', event => {
      if (active && event.key === 'Escape') { event.preventDefault(); setActive(false); }
    });
    // Fullscreen uses a fixed overlay instead of requestFullscreen(), for iOS Safari support.
  }
  document.addEventListener('DOMContentLoaded', () => {
    setup(document.querySelector('.home-map-shell'), document.getElementById('home-map'));
    setup(document.getElementById('okn-facility-map-panel'), document.getElementById('map'));
  });
})();
