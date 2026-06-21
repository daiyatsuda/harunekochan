"""
Notionデータベースからニュースを取得してindex.htmlを生成するスクリプト。
GitHub Actionsから毎日7:00 JSTに実行される。
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
NOTION_VERSION = "2022-06-28"

JST = timezone(timedelta(hours=9))

THEORY_DESCRIPTIONS = {
    "資源ベース理論（RBV）": "企業内部の希少で模倣困難な資源・能力こそが持続的競争優位の源泉とする理論。人材・組織文化・ノウハウを戦略資産として捉える視点を与えてくれます。",
    "センスメイキング理論": "不確実な状況を人々がどう「意味づけ」するかに注目する組織論。変化の渦中にあるとき、リーダーが語るナラティブが組織行動を方向づけます。",
    "ダイナミック・ケイパビリティ": "環境変化に合わせて自社の能力を感知・捕捉・再構成する力。テクノロジーが急変する時代において、静的な強みではなく変化する能力そのものが競争優位になります。",
}

CARD_TEMPLATE = """
    <article class="article">
      <div class="article-num">{num:02d}</div>
      <div class="article-body">
        <div class="article-meta">
          <span class="theory-badge">{theory}</span>
          <div class="article-tags">{tags_html}</div>
        </div>
        <h2 class="article-headline">{headline}</h2>
        <p class="article-summary">{summary}</p>
        {theory_box}
        <div class="article-footer">
          <span class="source">{source}</span>
          {link_html}
        </div>
      </div>
    </article>"""

THEORY_BOX_TEMPLATE = """        <div class="theory-box">
          <div class="theory-box-label">経営理論の視点 ▶ {theory}</div>
          <p class="theory-box-text">{description}</p>
        </div>"""


def notion_request(path: str, payload: dict) -> dict:
    url = f"https://api.notion.com/v1/{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_news(limit: int = 10) -> list[dict]:
    payload = {
        "sorts": [{"property": "配信日", "direction": "descending"}],
        "page_size": limit,
    }
    result = notion_request(f"databases/{NOTION_DATABASE_ID}/query", payload)
    return result.get("results", [])


def extract_text(prop: dict) -> str:
    if not prop:
        return ""
    ptype = prop.get("type")
    if ptype == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    if ptype == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    if ptype == "select":
        sel = prop.get("select")
        return sel.get("name", "") if sel else ""
    if ptype == "multi_select":
        return [s.get("name", "") for s in prop.get("multi_select", [])]
    if ptype == "date":
        d = prop.get("date")
        return d.get("start", "") if d else ""
    if ptype == "url":
        return prop.get("url", "") or ""
    return ""


def page_to_item(page: dict) -> dict:
    props = page.get("properties", {})
    return {
        "headline": extract_text(props.get("ヘッドライン", {})),
        "tags": extract_text(props.get("タグ", {})) or [],
        "summary": extract_text(props.get("要約", {})),
        "source": extract_text(props.get("出典", {})),
        "theory": extract_text(props.get("経営理論", {})),
        "date": extract_text(props.get("配信日", {})),
        "link": extract_text(props.get("リンク", {})),
    }


def render_card(item: dict, num: int = 1) -> str:
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in item["tags"])
    theory = item["theory"] or "未分類"
    desc = THEORY_DESCRIPTIONS.get(theory, "")
    theory_box = THEORY_BOX_TEMPLATE.format(theory=theory, description=desc) if desc else ""
    link_html = (
        f'<a class="read-link" href="{item["link"]}" target="_blank" rel="noopener">元記事を読む</a>'
        if item["link"]
        else ""
    )
    return CARD_TEMPLATE.format(
        num=num,
        theory=theory,
        headline=item["headline"],
        tags_html=tags_html,
        summary=item["summary"],
        theory_box=theory_box,
        source=item["source"],
        link_html=link_html,
    )


def main():
    pages = fetch_news()
    items = [page_to_item(p) for p in pages]

    if items:
        cards_html = "\n".join(render_card(i, n + 1) for n, i in enumerate(items))
    else:
        cards_html = """
    <div class="empty">
      <div class="empty-icon">🐱</div>
      <p>今日のニュースはまだありません。</p>
    </div>"""

    now = datetime.now(JST)
    date_label = now.strftime("%Y年%-m月%-d日 更新")

    template = Path("template.html").read_text(encoding="utf-8")
    html = template.replace("<!-- DATE_LABEL -->", date_label)
    html = html.replace("<!-- NEWS_CARDS -->", cards_html)

    Path("index.html").write_text(html, encoding="utf-8")
    print(f"✅ index.html を生成しました（{len(items)} 件）")


if __name__ == "__main__":
    main()
