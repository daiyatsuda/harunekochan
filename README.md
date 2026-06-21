# はるねこちゃん

人事・経営ニュース × 世界標準の経営理論 — 津田大也さん専用AI秘書サイト

## セットアップ手順

### 1. GitHub Pages の有効化

リポジトリの **Settings → Pages → Source** を `Deploy from a branch` にし、ブランチ `main`・フォルダ `/ (root)` を選択して Save。

### 2. 初回の index.html を配置

`template.html` をコピーして `index.html` を作成し、push するとサイトが公開される。

```bash
cp template.html index.html
git add .
git commit -m "chore: initial deploy"
git push
```

### 3. Notion Internal Integration の発行

1. [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations) を開く
2. **New integration** → 名前「haruneko-bot」で作成
3. 表示される `Internal Integration Secret` をコピー
4. Notion の「🐱 はるねこちゃん」ページを開く → 右上 `…` → **Connections** → haruneko-bot を追加

### 4. Actions Secrets の登録

リポジトリの **Settings → Secrets and variables → Actions → New repository secret** で 2 件追加する。

| Name | Value |
|------|-------|
| `NOTION_API_KEY` | 手順 3 でコピーした Secret |
| `NOTION_DATABASE_ID` | `384d8c66-3343-46f9-ae34-16fc2685236a` |

### 5. 動作確認（手動実行）

**Actions タブ → Update Site → Run workflow** を押す。  
ログで「✅ index.html を生成しました」が表示されれば成功。

## 構成

```
harunekochan/
├── index.html              公開サイト（Actions が自動更新）
├── template.html           index.html の雛形
├── favicon.svg             サイトアイコン（シンプル猫）
├── scripts/
│   └── generate_site.py   Notion → index.html 変換スクリプト
└── .github/workflows/
    └── update-site.yml    毎日 07:00 JST 自動実行
```

## 対応している経営理論

| タグ | 経営理論 |
|------|----------|
| 人事制度・シニア活躍・タレントマネジメント | 資源ベース理論（RBV） |
| 組織変革・リーダーシップ・管理職 | センスメイキング理論 |
| DX・採用・AI活用 | ダイナミック・ケイパビリティ |

理論の解説は入山章栄『世界標準の経営理論』を参考にしています。
