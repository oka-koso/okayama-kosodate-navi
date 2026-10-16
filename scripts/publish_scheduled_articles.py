#!/usr/bin/env python3
"""Release due article HTML, metadata, static cards and sitemap together in JST."""
from __future__ import annotations

import argparse
from datetime import datetime
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://oka-koso.github.io/okayama-kosodate-navi/'


def due(article, now):
    if article.get('publish_at'):
        at = datetime.fromisoformat(article['publish_at'])
        if at.tzinfo is None:
            raise ValueError('publish_at must include a timezone')
        return at <= now
    return article['published'] <= now.astimezone(ZoneInfo('Asia/Tokyo')).date().isoformat()


class ListBounds(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.lines = source.splitlines(keepends=True)
        self.source = source
        self.depth = 0
        self.bounds = None
        self.inner_start = None
        self.feed(source)

    def char_offset(self):
        line, column = self.getpos()
        return sum(map(len, self.lines[:line-1])) + column

    def handle_starttag(self, tag, attrs):
        if tag != 'div':
            return
        if self.depth:
            self.depth += 1
        elif self.bounds is None and 'data-bibouroku-list' in dict(attrs):
            self.depth = 1
            self.inner_start = self.char_offset() + len(self.get_starttag_text())

    def handle_endtag(self, tag):
        if tag == 'div' and self.depth:
            self.depth -= 1
            if self.depth == 0:
                self.bounds = (self.inner_start, self.char_offset())


def card(article):
    e = escape
    y, m, d = map(int, article['published'].split('-'))
    img = article.get('image', 'assets/bibouroku/bibouroku-reading.png')
    return (f'<a class="bibouroku-card" href="{e(article["url"])}">'
            f'<img class="bibouroku-card__thumb" src="{e(img)}" alt="" width="640" height="426" loading="lazy" decoding="async">'
            f'<div class="bibouroku-card__meta"><span class="bibouroku-card__tag">{e(article["category"])}</span><span>{y}年{m}月{d}日</span></div>'
            f'<h2>{e(article["title"])}</h2><p>{e(article["description"])}</p><span class="bibouroku-card__more">続きを読む →</span></a>')


def release(root=ROOT, now=None):
    now = now or datetime.now(ZoneInfo('Asia/Tokyo'))
    manifest = json.loads((root / '_scheduled_articles/manifest.json').read_text())
    data_path = root / 'data/bibouroku.json'
    articles = json.loads(data_path.read_text())
    existing = {a['url'] for a in articles}
    pending = [entry for entry in manifest if due(entry['article'], now) and entry['article']['url'] not in existing]
    if not pending:
        return []

    # Validate the whole batch before writing any public files.
    contents = {}
    for entry in pending:
        article = entry['article']
        target = root / article['url']
        if target.exists():
            raise ValueError(f'Refusing to overwrite an unregistered article: {target}')
        source = root / entry['source']
        content = source.read_text()
        if '<h1>' not in content or BASE + article['url'] not in content:
            raise ValueError(f'Invalid article: {source}')
        image = root / article['image']
        if not image.is_file() or image.stat().st_size == 0:
            raise ValueError(f'Missing image: {image}')
        contents[target] = content
        articles.append(article)

    articles.sort(key=lambda a: a.get('publish_at', a.get('published', '')), reverse=True)
    visible = [a for a in articles if due(a, now)]
    contents[data_path] = json.dumps(articles, ensure_ascii=False, indent=2) + '\n'
    for page, limit in [('bibouroku.html', 0), ('index.html', 3)]:
        p = root / page
        text = p.read_text()
        bounds = ListBounds(text).bounds
        if bounds is None:
            raise ValueError(f'Missing static article list: {page}')
        first, last = bounds
        items = visible[:limit] if limit else visible
        contents[p] = text[:first] + ''.join(card(a) for a in items) + text[last:]

    sm_path = root / 'sitemap.xml'
    sitemap = sm_path.read_text()
    if '</urlset>' not in sitemap:
        raise ValueError('Invalid sitemap')
    for entry in pending:
        a = entry['article']
        if BASE + a['url'] not in sitemap:
            sitemap = sitemap.replace('</urlset>', f'  <url><loc>{BASE+a["url"]}</loc><lastmod>{a["updated"]}</lastmod></url>\n</urlset>')
        for backlink in entry.get('backlinks', []):
            p = root / backlink
            text = contents.get(p, p.read_text())
            relative = Path(a['url']).name if backlink.startswith('articles/') else a['url']
            if relative in text:
                continue
            marker = '<!-- scheduled-article-related -->'
            block = f'{marker}<div class="article-linkbox"><p>相談から提出後まで順に確認したい方へ。</p><a href="{relative}">{escape(a["title"])}</a></div>'
            if '</article>' in text:
                contents[p] = text.replace('</article>', block + '</article>', 1)
            elif '</main>' in text:
                contents[p] = text.replace('</main>', block + '</main>', 1)
            else:
                raise ValueError(f'Missing related-link insertion point: {backlink}')
    contents[sm_path] = sitemap
    for p, content in contents.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return [entry['article']['url'] for entry in pending]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    # Test dates belong in isolated test copies, never in workflow inputs.
    parser.parse_args()
    published = release()
    print('Published: ' + (', '.join(published) if published else 'no articles due'))
