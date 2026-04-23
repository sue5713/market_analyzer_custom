# バックアップ運用ガイド

## 概要
`backup/` 配下に、変更前の重要ファイルのスナップショットを退避します。新しい実装で不具合が出たらここから簡単に元に戻せるようにするためです。

## 命名規則
`backup/<YYYYMMDD>_<変更の概要>/`

## 退避対象
その変更で書き換えるファイルのみを格納します。

---

## 既存バックアップ一覧

### `backup/20260424_pre_hours_filter/` (2026-04-24)
**変更内容**: US 市場の「終値」判定を NY 時間 15:45 の 15分足に固定 + close-to-close 合成バー方式
- Before: yfinance が返した最終バー(after-hours が混ざるケースあり)をそのまま終値として使用
- After:
  - NY 時間 9:30 〜 15:45 のバーのみにフィルタ
  - JST で見ると、**夏時間(EDT)** は 04:45 開始の 15分足 / **冬時間(EST)** は 05:45 開始の 15分足 が最終バー
  - DST/EST の切替は pytz が自動判定
  - **close-to-close 合成バー**: baseline 日の最終バー Close を OHLC 全部に入れた合成バーを先頭に差し込み、baseline 日の実バーを除外。下流の analyze_sectors は Open→Close の計算式を変えずに終値-終値基準で RF/MDD を算出

**実装方針**: `analyze_sectors.py` は引き続き未変更。新規 `market_hours_filter.py` モジュールを追加し、`run_with_baseline.py` で `analyze_sectors.filter_data_by_date` を monkey-patch して組み込み(subprocess をやめて同一プロセス内で main を呼び出す構成へ変更)。

**退避ファイル**:
- `run_with_baseline.py` — 改修前 (subprocess 版)

---

### `backup/20260422_pre_weekday_baseline/` (2026-04-22)
**変更内容**: 分析基点を「直近14日固定」から「曜日ごと切替」へ
- Before: 毎日、直近14日間を対象に RF/MDD を算出
- After:
  - **月〜木**: 前週末(前週金曜)の終値を基点
  - **金**: 前月末の終値を基点

**実装方針**: `analyze_sectors.py` は一切変更せず、新規 `run_with_baseline.py` (wrapper) で曜日判定 -> 適切な `--start/--end` を決めて `analyze_sectors.py` を呼び出す構成に変更。

**退避ファル**:
- `market_analysis.yml` — 改修前の GitHub Actions 定義

---

## 復元手順

### A. バックアップファイルから戻す (簡単)
例: 20260424 の改修を巻き戻したい場合
```bash
git checkout claude/review-project-structure-0PEOW
cp backup/20260424_pre_hours_filter/run_with_baseline.py ./
git rm market_hours_filter.py
git add run_with_baseline.py
git commit -m "Revert US regular-hours filter"
git push
```

### B. Git で変更コミットごと revert (バイト完全一致)
```bash
git log --oneline
git revert <commit-hash>
git push
```

---

## ルール
- `backup/` 配下のファイルは **編集禁止**
- 大きな変更の前には **必ず新しい `backup/<timestamp>_<label>/`** を切り対象ファイルをコピー
- `backup/` は GitHub Actions 実行時に読み込まれません
