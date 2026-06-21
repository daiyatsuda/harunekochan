"""
Notionデータベースからニュースを取得してindex.htmlを生成するスクリプト。
GitHub Actionsから毎日7:00 JSTに実行される。
"""

import os
import json
import re
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import Counter, defaultdict

NOTION_API_KEY = os.environ["NOTION_API_KEY"]
NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
NOTION_VERSION = "2022-06-28"
JST = timezone(timedelta(hours=9))
SITE_URL = "https://daiyatsuda.github.io/harunekochan/"

THEORY_DESCRIPTIONS = {
    # ── 競争戦略系 ──
    "SCP理論": "産業構造（Structure）が企業行動（Conduct）を決め、パフォーマンス（Performance）を左右するという枠組み。ポーターの「5つの力」の基盤となり、業界の魅力度を分析する出発点です。",
    "ゲーム理論": "競合・顧客・サプライヤーなど複数のプレーヤーが相互に意思決定し合う状況を分析する理論。価格競争・協調・交渉など、戦略的相互依存を読み解くための強力なツールです。",
    "取引費用理論": "市場取引には探索・交渉・監視などのコストがかかるという考え方。内製か外注か、どの範囲まで組織内に取り込むかという「組織の境界」を決める際の基本論理です。",
    "エージェンシー理論": "依頼人（プリンシパル）と代理人（エージェント）の間に生まれる利害対立と情報非対称を扱う理論。報酬設計・ガバナンス・インセンティブ設計の核心をなします。",
    "コア・コンピタンス理論": "競合が簡単に模倣できない、顧客価値の源泉となる中核能力を指す概念。自社の強みを起点に事業多角化を考える際の指針となります。",
    "資源ベース理論（RBV）": "企業内部の希少で模倣困難な資源・能力こそが持続的競争優位の源泉とする理論。人材・組織文化・ノウハウを戦略資産として捉える視点を与えてくれます。",
    "ダイナミック・ケイパビリティ": "環境変化に合わせて自社の能力を感知・捕捉・再構成する力。テクノロジーが急変する時代において、静的な強みではなく変化する能力そのものが競争優位になります。",
    "リアル・オプション理論": "不確実な状況下での投資判断を「オプション（選択権）」として捉える考え方。段階的投資・撤退・延期の柔軟性に経済的価値を見出し、意思決定の質を高めます。",
    # ── 組織・知識系 ──
    "知識創造理論": "暗黙知と形式知の相互変換（SECIモデル）を通じて組織的知識が創られるプロセスを説く理論。野中郁次郎らが提唱し、イノベーションと学習の源泉を説明します。",
    "組織学習論": "個人の学びが組織全体の知識・ルーティンへと昇華していく仕組みを扱う理論。シングルループ学習（修正）とダブルループ学習（前提の問い直し）の区別が鍵となります。",
    "両利きの経営": "既存事業の「深化（exploitation）」と新規事業の「探索（exploration）」を同時に追求する組織能力の理論。成熟企業がイノベーションを実現するための組織論的解答です。",
    "センスメイキング理論": "不確実な状況を人々がどう「意味づけ」するかに注目する組織論。変化の渦中にあるとき、リーダーが語るナラティブが組織行動を方向づけます。",
    "上位集団理論": "組織のパフォーマンスはトップマネジメントチームの特性（経験・価値観・認知）を反映するという理論。リーダーシップ研究や後継者計画に深く関わります。",
    "組織アイデンティティ理論": "「我々は何者か」という組織の自己認識が、戦略・文化・意思決定に大きな影響を与えるとする理論。組織変革時のメンバーの抵抗感や一体感を理解する鍵です。",
    # ── 制度・社会系 ──
    "制度理論": "企業は経済合理性だけでなく、社会的規範・規制・慣行に適応することで正統性を獲得するとする理論。業界標準への同調や制度的圧力を読み解く視点を提供します。",
    "組織エコロジー": "生物進化に倣い、組織の誕生・成長・死滅を個体群レベルで捉える理論。特定業界で「どんな組織が生き残り、なぜ消えるか」を長期的に分析します。",
    "社会ネットワーク理論（弱い紐帯）": "強い絆よりも「弱いつながり」のほうが、異質な情報・機会・革新をもたらすというグラノヴェッターの知見。人脈・採用・知識探索の設計に応用できます。",
    "社会ネットワーク理論（構造的空隙）": "他者同士がつながっていない「空白」を橋渡しするポジションが、情報・影響力・交渉力の優位をもたらすというバートの理論。組織内外のブローカー的役割を説明します。",
    "正統性理論": "組織が社会・ステークホルダーから「存在する理由がある」と認められることの重要性を説く理論。ESGやブランド戦略、ステークホルダー対応に直結します。",
    # ── 心理・行動系 ──
    "認知理論（経営）": "経営者の認知・信念・注意配分が戦略選択に影響するとする行動論的アプローチ。バイアスや認知の枠組みを意識することで、より良い意思決定が可能になります。",
    "プロスペクト理論": "人は利益より損失を大きく感じる（損失回避）という行動経済学の知見。リスク判断・交渉・報酬設計など、合理性からの逸脱を予測・活用するための理論です。",
    # ── イノベーション・起業系 ──
    "イノベーションのジレンマ": "優良企業が持続的イノベーションに集中するあまり、破壊的イノベーターに市場を奪われるパラドックスを説くクリステンセンの理論。既存事業の優等生ほど危ない理由です。",
    "アントレプレナーシップ理論": "新たな機会を発見・創造し、資源を結合して価値を生み出す企業家的行動を扱う理論。大企業の社内起業（イントラプレナーシップ）や新規事業開発にも応用されます。",
    "スピンオフ理論": "既存組織から独立した新事業・新企業が生まれるプロセスとその成功要因を扱う理論。親組織の知識・資源・人材がどう次世代イノベーションを生むかを分析します。",
    "未分類": "現時点では既存の経営理論に明確に分類しにくいニュースです。今後の理論的文脈の変化とともに再分類される可能性があります。",
}


def notion_request(path: str, payload: dict) -> dict:
    url = f"https://api.notion.com/v1/{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_all_news(limit: int = 60) -> list[dict]:
    payload = {
        "sorts": [{"property": "配信日", "direction": "descending"}],
        "page_size": limit,
    }
    result = notion_request(f"databases/{NOTION_DATABASE_ID}/query", payload)
    return result.get("results", [])


def extract_text(prop: dict) -> str | list:
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


def parse_summary_sections(text: str) -> dict:
    """要約テキストから【事実】【考察】【示唆】マーカーを解析してセクションに分割する。"""
    sections = {"facts": "", "analysis": "", "insights": "", "plain": ""}
    markers = {
        "【事実】": "facts",
        "【考察】": "analysis",
        "【示唆】": "insights",
    }
    has_marker = any(m in text for m in markers)
    if not has_marker:
        sections["plain"] = text
        return sections

    current_key = "plain"
    for line in text.replace("\r", "").split("\n"):
        matched = False
        for marker, key in markers.items():
            if line.startswith(marker):
                current_key = key
                rest = line[len(marker):].strip()
                if rest:
                    sections[current_key] = (sections[current_key] + " " + rest).strip()
                matched = True
                break
        if not matched and line.strip():
            sections[current_key] = (sections[current_key] + " " + line.strip()).strip()

    return sections


def render_theory_box(theory: str) -> str:
    desc = THEORY_DESCRIPTIONS.get(theory, "")
    if not desc:
        return ""
    return (
        f'<div class="theory-box">'
        f'<div class="theory-box-label">📚 経営理論の視点 ▶ {theory}</div>'
        f'<p class="theory-box-text">{desc}</p>'
        f'</div>'
    )


def render_fb_share(link: str = "") -> str:
    share_url = link if link else SITE_URL
    encoded = urllib.parse.quote(share_url, safe="") if link else urllib.parse.quote(SITE_URL, safe="")
    return (
        f'<a class="fb-share" href="https://www.facebook.com/sharer/sharer.php?u={encoded}" '
        f'target="_blank" rel="noopener">'
        f'<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M18 2h-3a5 5 0 00-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 011-1h3z"/></svg>'
        f'シェア</a>'
    )


def render_card(item: dict, num: int, is_today: bool = True) -> str:
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in item["tags"])
    theory = item["theory"] or "未分類"
    new_badge = '<span class="badge-new">NEW</span>' if is_today else ""

    # Parse structured sections
    sections = parse_summary_sections(item["summary"])
    content_html = ""
    if sections["facts"]:
        content_html += (
            f'<div class="art-section fact">'
            f'<span class="art-label">📰 事実</span>'
            f'<p>{sections["facts"]}</p>'
            f'</div>'
        )
    if sections["analysis"]:
        content_html += (
            f'<div class="art-section analysis">'
            f'<span class="art-label">🔍 考察</span>'
            f'<p>{sections["analysis"]}</p>'
            f'</div>'
        )
    if sections["insights"]:
        content_html += (
            f'<div class="art-section insight">'
            f'<span class="art-label">💡 示唆</span>'
            f'<p>{sections["insights"]}</p>'
            f'</div>'
        )
    if not content_html and sections["plain"]:
        content_html = f'<p class="card-summary">{sections["plain"]}</p>'

    theory_box = render_theory_box(theory) if is_today else ""

    source_text = item["source"]
    if item["link"]:
        source_html = f'<a class="card-source" href="{item["link"]}" target="_blank" rel="noopener">📎 {source_text}</a>'
    else:
        source_html = f'<span class="card-source">{source_text}</span>'

    link_btn = (
        f'<a class="read-btn" href="{item["link"]}" target="_blank" rel="noopener">元記事 →</a>'
        if item["link"] else ""
    )

    fb = render_fb_share(item.get("link", ""))

    return f"""<div class="card">
  <div class="card-num">{num:02d}</div>
  <div class="card-meta">
    <span class="badge-theory">📚 {theory}</span>
    {new_badge}
    {tags_html}
  </div>
  <h2 class="card-headline">{item["headline"]}</h2>
  {content_html}
  {theory_box}
  <div class="card-foot">
    {source_html}
    <div class="card-foot-right">
      {link_btn}
      {fb}
    </div>
  </div>
</div>"""


def render_archive_card(item: dict, num: int) -> str:
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in item["tags"])
    theory = item["theory"] or "未分類"
    sections = parse_summary_sections(item["summary"])
    summary_text = sections["plain"] or sections["facts"] or item["summary"]

    if item["link"]:
        source_html = f'<a class="card-source" href="{item["link"]}" target="_blank" rel="noopener">📎 {item["source"]}</a>'
        link_btn = f'<a class="read-btn" href="{item["link"]}" target="_blank" rel="noopener">元記事 →</a>'
    else:
        source_html = f'<span class="card-source">{item["source"]}</span>'
        link_btn = ""

    fb = render_fb_share(item.get("link", ""))

    return f"""<div class="arc-card">
  <div class="card-meta">
    <span class="badge-theory">📚 {theory}</span>
    {tags_html}
  </div>
  <h3 class="card-headline">{item["headline"]}</h3>
  <p class="card-summary">{summary_text}</p>
  <div class="card-foot">
    {source_html}
    <div class="card-foot-right">
      {link_btn}
      {fb}
    </div>
  </div>
</div>"""


def format_date_ja(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        d = datetime.fromisoformat(date_str)
        return d.strftime("%-m月%-d日")
    except Exception:
        return date_str


def generate_insights_html(items: list[dict], today_str: str) -> str:
    if not items:
        return '<p style="color:var(--text-light);font-size:.9rem;">まだデータが蓄積されていません。</p>'

    # Theory frequency
    theory_counter: Counter = Counter()
    for item in items:
        t = item["theory"] or "未分類"
        if t != "未分類":
            theory_counter[t] += 1

    max_cnt = max(theory_counter.values()) if theory_counter else 1
    top_theories = theory_counter.most_common(6)

    # Theory rank bars
    rank_html = ""
    for theory, cnt in top_theories:
        pct = int(cnt / max_cnt * 100)
        rank_html += (
            f'<div class="rank-item">'
            f'<span class="rank-label">{theory}</span>'
            f'<div class="rank-bar-bg"><div class="rank-bar" style="width:{pct}%"></div></div>'
            f'<span class="rank-cnt">{cnt}件</span>'
            f'</div>'
        )

    # Featured theory (top 1)
    featured_theory = top_theories[0][0] if top_theories else ""
    featured_desc = THEORY_DESCRIPTIONS.get(featured_theory, "")
    featured_html = ""
    if featured_theory and featured_desc:
        featured_html = (
            f'<div class="theory-feature">'
            f'<div class="theory-feature-name">🏆 最頻出理論：{featured_theory}</div>'
            f'<div class="theory-feature-text">{featured_desc}</div>'
            f'</div>'
        )

    # Tag frequency
    tag_counter: Counter = Counter()
    for item in items:
        tag_counter.update(item["tags"])
    top_tags = tag_counter.most_common(5)
    tag_rank_html = ""
    max_tag = max(tag_counter.values()) if tag_counter else 1
    for tag, cnt in top_tags:
        pct = int(cnt / max_tag * 100)
        tag_rank_html += (
            f'<div class="rank-item">'
            f'<span class="rank-label">{tag}</span>'
            f'<div class="rank-bar-bg"><div class="rank-bar" style="width:{pct}%;background:var(--rose)"></div></div>'
            f'<span class="rank-cnt">{cnt}件</span>'
            f'</div>'
        )

    # Recent week's articles with rich content (has sections)
    rich_items = [i for i in items if "【考察】" in i["summary"] or "【示唆】" in i["summary"]][:5]
    featured_articles_html = ""
    if rich_items:
        featured_articles_html = '<div class="insight-articles-title">💎 深掘り記事ピックアップ</div>'
        for item in rich_items:
            sections = parse_summary_sections(item["summary"])
            insight_text = sections["insights"] or sections["analysis"] or ""
            theory = item["theory"] or "未分類"
            link_attr = f'href="{item["link"]}" target="_blank" rel="noopener"' if item["link"] else "href='#'"
            featured_articles_html += f"""<div class="arc-card" style="margin-bottom:16px;">
  <div class="card-meta">
    <span class="badge-theory">📚 {theory}</span>
  </div>
  <h3 class="card-headline"><a {link_attr} style="text-decoration:none;color:inherit;">{item["headline"]}</a></h3>
  {f'<div class="art-section insight"><span class="art-label">💡 示唆</span><p>{insight_text}</p></div>' if insight_text else f'<p class="card-summary">{sections["plain"]}</p>'}
  <div class="card-foot">
    <span class="card-source">{item["source"]} / {format_date_ja(item["date"])}</span>
  </div>
</div>"""

    # Week summary note
    recent_count = len([i for i in items if i["date"] >= (datetime.now(JST) - timedelta(days=7)).strftime("%Y-%m-%d")])

    return f"""<div class="insights-grid">
  <div class="insight-box">
    <div class="insight-box-title">📊 よく出る経営理論 TOP6</div>
    <div class="theory-rank">
      {rank_html}
    </div>
    {featured_html}
  </div>
  <div class="insight-box">
    <div class="insight-box-title">🏷 注目トピック TOP5</div>
    <div class="theory-rank">
      {tag_rank_html}
    </div>
    <div style="margin-top:20px;padding:14px;background:var(--bg);border-radius:10px;">
      <div style="font-size:.72rem;font-weight:700;color:var(--text-light);margin-bottom:6px;">📈 直近7日間</div>
      <div style="font-family:'Shippori Mincho',serif;font-size:1.6rem;font-weight:800;color:var(--text);">{recent_count}<small style="font-size:.85rem;font-weight:400;font-family:'Zen Kaku Gothic New',sans-serif;">件</small></div>
      <div style="font-size:.72rem;color:var(--text-light);">のニュースを収集・解説</div>
    </div>
  </div>
</div>
{featured_articles_html}"""


# urllib.parse is needed for URL encoding
import urllib.parse


def main():
    pages = fetch_all_news()
    items = [page_to_item(p) for p in pages]

    now = datetime.now(JST)
    today_str = now.strftime("%Y-%m-%d")
    date_label = now.strftime("%-m月%-d日")

    today_items   = [i for i in items if i["date"] == today_str]
    archive_items = [i for i in items if i["date"] != today_str]

    # Today cards
    if today_items:
        today_cards_html = "\n".join(render_card(i, n + 1, True) for n, i in enumerate(today_items))
    else:
        today_cards_html = """<div class="empty">
  <svg width="80" height="60" viewBox="0 0 80 60" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M16 20 Q18 8 26 12 Q25 17 19 22Z" fill="#C8BFB6" stroke="#8A7F78" stroke-width="1.5" stroke-linejoin="round"/>
    <path d="M44 20 Q42 8 34 12 Q35 17 41 22Z" fill="#C8BFB6" stroke="#8A7F78" stroke-width="1.5" stroke-linejoin="round"/>
    <circle cx="30" cy="28" r="18" fill="#C8BFB6" stroke="#8A7F78" stroke-width="2"/>
    <path d="M22 26 Q26 24 30 26" stroke="#8A7F78" stroke-width="2" stroke-linecap="round" fill="none"/>
    <path d="M30 26 Q34 24 38 26" stroke="#8A7F78" stroke-width="2" stroke-linecap="round" fill="none"/>
    <ellipse cx="30" cy="30" rx="2.5" ry="2" fill="#8A7F78"/>
    <text x="44" y="14" font-size="10" fill="#A89F96">z</text>
    <text x="52" y="8" font-size="7" fill="#A89F96">z</text>
  </svg>
  <p style="margin-top:12px;">今日のニュースはまだ届いていません。<br>毎朝6時に自動収集します。</p>
</div>"""

    # Archive grouped by date
    archive_by_date: defaultdict = defaultdict(list)
    for item in archive_items:
        archive_by_date[item["date"]].append(item)

    archive_html = ""
    card_num = 1
    for date_str in sorted(archive_by_date.keys(), reverse=True):
        date_items = archive_by_date[date_str]
        date_ja = format_date_ja(date_str)
        archive_html += f'<div class="archive-group"><div class="archive-group-head">{date_ja}のニュース</div>\n'
        for item in date_items:
            archive_html += render_archive_card(item, card_num) + "\n"
            card_num += 1
        archive_html += "</div>\n"

    if not archive_html:
        archive_html = '<p style="color:var(--text-light);font-size:.85rem;">アーカイブはまだありません。</p>'

    # Tag cloud
    all_tags: list[str] = []
    for item in items:
        all_tags.extend(item["tags"])
    tag_counts = Counter(all_tags)

    topic_tags_html = ""
    for tag, count in tag_counts.most_common():
        topic_tags_html += f'<span class="topic-pill">{tag}<span class="topic-cnt">{count}</span></span>\n'

    # Sidebar archive list
    archive_list_html = ""
    recent = archive_items[:10]
    if recent:
        cur_date = None
        for item in recent:
            if item["date"] != cur_date:
                cur_date = item["date"]
                archive_list_html += f'<div class="arc-date-lbl">{format_date_ja(cur_date)}</div>\n'
            if item["link"]:
                archive_list_html += (
                    f'<a class="arc-list-item" href="{item["link"]}" target="_blank" rel="noopener">'
                    f'<div class="arc-dot"></div>'
                    f'<div class="arc-text">{item["headline"]}</div>'
                    f'</a>\n'
                )
            else:
                archive_list_html += (
                    f'<div class="arc-list-item">'
                    f'<div class="arc-dot"></div>'
                    f'<div class="arc-text">{item["headline"]}</div>'
                    f'</div>\n'
                )
    else:
        archive_list_html = '<p style="color:var(--text-light);font-size:.8rem;">まだありません。</p>'

    # Insights page
    insights_html = generate_insights_html(items, today_str)

    # Build index.html
    template = Path("template.html").read_text(encoding="utf-8")
    html = template
    html = html.replace("<!-- DATE_LABEL -->",       date_label)
    html = html.replace("<!-- TODAY_COUNT -->",       str(len(today_items)))
    html = html.replace("<!-- TOTAL_COUNT -->",       str(len(items)))
    html = html.replace("<!-- TODAY_CARDS -->",       today_cards_html)
    html = html.replace("<!-- ARCHIVE_HTML -->",      archive_html)
    html = html.replace("<!-- TOPIC_TAGS_HTML -->",   topic_tags_html)
    html = html.replace("<!-- ARCHIVE_LIST_HTML -->", archive_list_html)
    html = html.replace("<!-- INSIGHTS_HTML -->",     insights_html)

    Path("index.html").write_text(html, encoding="utf-8")
    print(f"✅ index.html を生成しました（今日 {len(today_items)} 件 / アーカイブ {len(archive_items)} 件 / 合計 {len(items)} 件）")


if __name__ == "__main__":
    main()
