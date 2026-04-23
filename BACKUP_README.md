# バックアップ運用ガイド

## 概要
`backup/` 配下に、変更前の重要ファイルのスナップショットを退避します。新しい実装で不具合が出たらここから簡単に元に戻せるようにするためです。

## 命名規則
`backup/<YYYYMMDD>_<変更の概要>/`

## 退避対象
その変更で書き換えるファイルのみを格納します。今回は `analyze_sectors.py` 本体は触らず、wrapper スクリプト (`run_with_baseline.py`) 追加と workflow yml の変更のみのため、退避対象は workflow yml のみです。

---

## 既存バックアップ一覧

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
```bash
git checkout claude/review-project-structure-0PEOW
cp backup/20260422_pre_weekday_baseline/market_analysis.yml ./.github/workflows/
git rm run_with_baseline.py
git add .github/workflows/market_analysis.yml
git commit -m "Revert weekday-baseline wrapper"
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
