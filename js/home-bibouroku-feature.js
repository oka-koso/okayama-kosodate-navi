(() => {
  "use strict";

  const DATA_URL = "data/bibouroku.json";

  const normalizeArticles = (data) => {
    const list = Array.isArray(data) ? data :
      Array.isArray(data?.articles) ? data.articles :
      Array.isArray(data?.items) ? data.items : [];
    return list
      .filter(a => a && (a.url || a.href) && (a.title || a.name))
      .map(a => ({
        ...a,
        url: a.url || a.href,
        title: a.title || a.name,
        date: a.date || a.published_at || a.published || ""
      }))
      .sort((a,b) => String(b.date).localeCompare(String(a.date)));
  };

  const pathKey = (u) => {
    try {
      const x = new URL(u, location.href);
      return x.pathname.replace(/\/+/g,"/").replace(/\/$/,"");
    } catch (_) {
      return String(u || "").replace(/^\.\//,"").replace(/\/$/,"");
    }
  };

  const findHeading = (text) =>
    [...document.querySelectorAll("h1,h2,h3,h4")]
      .find(el => (el.textContent || "").replace(/\s+/g,"").includes(text.replace(/\s+/g,"")));

  const findSection = (heading) => {
    if (!heading) return null;
    return heading.closest("section") ||
           heading.closest(".section") ||
           heading.closest("[class*='section']") ||
           heading.parentElement;
  };

  function addLatestBar(latest) {
    if (document.querySelector(".home-bibouroku-latest")) return;

    const wrap = document.createElement("div");
    wrap.className = "home-bibouroku-latest";
    wrap.innerHTML = `
      <a class="home-bibouroku-latest__link" href="${latest.url}">
        <span class="home-bibouroku-latest__new">NEW</span>
        <span class="home-bibouroku-latest__label">子育て備忘録</span>
        <span class="home-bibouroku-latest__title"></span>
        <span class="home-bibouroku-latest__arrow" aria-hidden="true">→</span>
      </a>`;
    wrap.querySelector(".home-bibouroku-latest__title").textContent = latest.title;

    const hero = document.querySelector(
      ".hero, .hero-section, .home-hero, #hero, [class*='hero']"
    );
    if (hero) {
      hero.insertAdjacentElement("afterend", wrap);
      return;
    }

    const main = document.querySelector("main");
    if (main) main.insertAdjacentElement("afterbegin", wrap);
    else document.body.insertAdjacentElement("afterbegin", wrap);
  }

  function getHomeArticleCards() {
    const bibHeading = findHeading("子育て備忘録");
    const section = findSection(bibHeading);
    if (!section) return { section:null, cards:[] };

    const cards = [...section.querySelectorAll("a[href]")]
      .filter(a => {
        const href = a.getAttribute("href") || "";
        return href.includes("articles/") &&
          (a.classList.contains("bibouroku-card") ||
           a.querySelector(".bibouroku-card__meta") ||
           a.textContent.trim().length > 0);
      });

    return { section, cards: [...new Set(cards)] };
  }

  function orderCardsAndMarkNew(articles) {
    const { section, cards } = getHomeArticleCards();
    if (!section || !cards.length) return;

    const rank = new Map(articles.map((a,i) => [pathKey(a.url), i]));
    const sorted = [...cards].sort((a,b) => {
      const ra = rank.get(pathKey(a.getAttribute("href"))) ?? 9999;
      const rb = rank.get(pathKey(b.getAttribute("href"))) ?? 9999;
      return ra - rb;
    });

    const parent = sorted[0]?.parentElement;
    if (parent && sorted.every(x => x.parentElement === parent)) {
      sorted.forEach(card => parent.appendChild(card));
    }

    const latestKey = pathKey(articles[0].url);
    cards.forEach(card => {
      card.querySelectorAll(".bibouroku-new-ribbon").forEach(x => x.remove());
      if (pathKey(card.getAttribute("href")) === latestKey) {
        const badge = document.createElement("span");
        badge.className = "bibouroku-new-ribbon";
        badge.textContent = "NEW";
        card.appendChild(badge);
      }
    });
  }

  function moveBibourokuAfterFlow() {
    const bib = findSection(findHeading("子育て備忘録"));
    const flow = findSection(findHeading("保育園探し・申込みの流れ"));
    if (!bib || !flow || bib === flow) return;
    if (flow.nextElementSibling !== bib) {
      flow.insertAdjacentElement("afterend", bib);
    }
  }

  async function run() {
    try {
      const res = await fetch(DATA_URL, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const articles = normalizeArticles(await res.json());
      if (!articles.length) return;

      addLatestBar(articles[0]);

      // bibouroku.js may render its cards asynchronously; retry briefly.
      let tries = 0;
      const apply = () => {
        moveBibourokuAfterFlow();
        orderCardsAndMarkNew(articles);
        if (++tries < 10 && !getHomeArticleCards().cards.length) {
          setTimeout(apply, 180);
        }
      };
      apply();
    } catch (e) {
      console.warn("Home Bibouroku feature:", e);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run, { once:true });
  } else {
    run();
  }
})();