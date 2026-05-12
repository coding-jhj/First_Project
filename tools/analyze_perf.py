"""
VG_PERF 로그 분석 스크립트
사용법: python tools/analyze_perf.py <log_file> [--out <output_dir>]
"""
import re
import sys
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams

# ── 한글 폰트 설정 ────────────────────────────────────────────────────────────
import matplotlib.font_manager as fm

def _setup_korean_font():
    candidates = [
        "Malgun Gothic",      # Windows
        "AppleGothic",        # macOS
        "NanumGothic",        # Linux
        "NanumBarunGothic",
        "DejaVu Sans",        # fallback
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            rcParams["font.family"] = name
            break
    rcParams["axes.unicode_minus"] = False

_setup_korean_font()

# ── 색상 팔레트 ───────────────────────────────────────────────────────────────
C_PRE  = "#4E79A7"
C_INFER = "#F28E2B"
C_POST = "#59A14F"
C_OH   = "#B07AA1"
C_E2E  = "#E15759"
C_TOT  = "#76B7B2"
BG     = "#F5F5F5"

# ── 파싱 ─────────────────────────────────────────────────────────────────────
PERF_RE = re.compile(
    r"D VG_PERF\s*:\s*"
    r"request_id\|(?P<rid>[^\|]+)\|"
    r"route\|(?P<route>[^\|]+)\|"
    r"model\|(?P<model>[^\|]+)\|"
    r"provider\|(?P<provider>[^\|]+)\|"
    r"preprocess\|(?P<preprocess>\d+)\|"
    r"infer\|(?P<infer>\d+)\|"
    r"postprocess\|(?P<postprocess>\d+)\|"
    r"mvp\|(?P<mvp>[^\|]+)\|"
    r"total\|(?P<total>\d+)\|"
    r"e2e\|(?P<e2e>-?\d+)\|"
    r"objs\|(?P<objs>\d+)"
)

def parse_log(path: str) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = PERF_RE.search(line)
            if not m:
                continue
            d = m.groupdict()
            row = {
                "request_id": d["rid"],
                "model": d["model"],
                "provider": d["provider"],
                "preprocess": int(d["preprocess"]),
                "infer": int(d["infer"]),
                "postprocess": int(d["postprocess"]),
                "mvp": d["mvp"],
                "total": int(d["total"]),
                "e2e": int(d["e2e"]),
                "objs": int(d["objs"]),
            }
            rows.append(row)
    df = pd.DataFrame(rows)
    df = df[df["e2e"] > 0].reset_index(drop=True)
    df["overhead"] = df["e2e"] - df["total"]
    df["frame"] = range(1, len(df) + 1)
    return df

# ── 통계 ─────────────────────────────────────────────────────────────────────
STAGES = ["preprocess", "infer", "postprocess", "overhead", "total", "e2e"]

def compute_stats(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for col in STAGES:
        s = df[col]
        records.append({
            "구간": col,
            "count": len(s),
            "mean": round(s.mean(), 1),
            "std": round(s.std(), 1),
            "min": int(s.min()),
            "p50": int(s.quantile(0.50)),
            "p95": int(s.quantile(0.95)),
            "p99": int(s.quantile(0.99)),
            "max": int(s.max()),
        })
    return pd.DataFrame(records).set_index("구간")

# ── 차트 공통 설정 ────────────────────────────────────────────────────────────
FIG_W, FIG_H, DPI = 19.2, 10.8, 100   # → 1920×1080 px

def _fig():
    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI, facecolor=BG)
    return fig

# ── 01 파이프라인 단계별 스택 바 ───────────────────────────────────────────────
def chart_breakdown(df: pd.DataFrame, out: Path):
    means = {s: df[s].mean() for s in ["preprocess", "infer", "postprocess", "overhead"]}
    e2e_mean = df["e2e"].mean()

    fig = _fig()
    ax = fig.add_subplot(111, facecolor=BG)

    bar_w = 0.45
    x = 0
    bottoms = [0, means["preprocess"],
               means["preprocess"] + means["infer"],
               means["preprocess"] + means["infer"] + means["postprocess"]]
    colors = [C_PRE, C_INFER, C_POST, C_OH]
    labels = ["전처리 (Preprocess)", "YOLO 추론 (Infer)", "NMS + EMA (Post)", "오버헤드 (Overhead)"]
    keys   = ["preprocess", "infer", "postprocess", "overhead"]

    for key, color, label, bot in zip(keys, colors, labels, bottoms):
        val = means[key]
        ax.bar(x, val, bar_w, bottom=bot, color=color, label=f"{label}  {val:.1f} ms",
               edgecolor="white", linewidth=1.5, zorder=3)
        ax.text(x, bot + val / 2, f"{val:.1f} ms",
                ha="center", va="center", fontsize=18, fontweight="bold", color="white", zorder=4)

    ax.annotate(f"E2E 평균\n{e2e_mean:.1f} ms",
                xy=(x + bar_w / 2 + 0.02, e2e_mean),
                xytext=(x + bar_w / 2 + 0.38, e2e_mean),
                fontsize=20, color=C_E2E, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=C_E2E, lw=2),
                va="center")

    ax.set_xlim(-0.5, 1.2)
    ax.set_ylim(0, e2e_mean * 1.35)
    ax.set_xticks([])
    ax.set_ylabel("소요 시간 (ms)", fontsize=16)
    ax.set_title(
        f"CameraX 프레임 수신 → EMA 완료  파이프라인 단계별 소요시간\n"
        f"모델: {df['model'].iloc[0]}  |  추론 엔진: {df['provider'].iloc[0]}  |  샘플: {len(df)}프레임",
        fontsize=18, pad=20)
    ax.legend(loc="upper right", fontsize=14, framealpha=0.9)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fpath = out / "01_pipeline_breakdown.png"
    fig.savefig(fpath, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  저장: {fpath}")

# ── 02 E2E 히스토그램 ──────────────────────────────────────────────────────────
def chart_histogram(df: pd.DataFrame, out: Path):
    e2e = df["e2e"]
    p50 = e2e.quantile(0.50)
    p95 = e2e.quantile(0.95)

    fig = _fig()
    ax = fig.add_subplot(111, facecolor=BG)

    bins = range(int(e2e.min()) - 1, int(e2e.max()) + 3)
    ax.hist(e2e, bins=bins, color=C_E2E, edgecolor="white", linewidth=0.8,
            alpha=0.85, zorder=3, label="E2E 지연 (ms)")

    ax.axvline(p50, color="#2C2C2C", linestyle="--", lw=2.5, zorder=4)
    ax.axvline(p95, color="#FF6B35", linestyle="--", lw=2.5, zorder=4)
    ax.text(p50 + 0.3, ax.get_ylim()[1] * 0.85, f"P50\n{p50:.0f} ms",
            fontsize=15, color="#2C2C2C", fontweight="bold")
    ax.text(p95 + 0.3, ax.get_ylim()[1] * 0.70, f"P95\n{p95:.0f} ms",
            fontsize=15, color="#FF6B35", fontweight="bold")

    ax.set_xlabel("E2E 지연시간 (ms)", fontsize=16)
    ax.set_ylabel("프레임 수", fontsize=16)
    ax.set_title(
        f"E2E 지연시간 분포  (CameraX 도착 → EMA 완료)\n"
        f"mean={e2e.mean():.1f} ms  std={e2e.std():.1f} ms  "
        f"min={e2e.min()}  max={e2e.max()}  n={len(e2e)}",
        fontsize=18, pad=20)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fpath = out / "02_e2e_histogram.png"
    fig.savefig(fpath, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  저장: {fpath}")

# ── 03 프레임별 타임라인 ────────────────────────────────────────────────────────
def chart_timeline(df: pd.DataFrame, out: Path):
    fig = _fig()
    ax = fig.add_subplot(111, facecolor=BG)

    ax.plot(df["frame"], df["e2e"], color=C_E2E, lw=1.8, label="E2E", zorder=4)
    ax.plot(df["frame"], df["total"], color=C_TOT, lw=1.4,
            linestyle="--", label="Total (내부 합계)", zorder=3)
    ax.fill_between(df["frame"], df["total"], df["e2e"],
                    color=C_OH, alpha=0.25, label="오버헤드 영역", zorder=2)

    mvp_frames = df[df["mvp"] == "run"]
    ax.scatter(mvp_frames["frame"], mvp_frames["e2e"],
               marker="*", s=180, color="#F4D03F", edgecolors="#8B7200",
               linewidths=0.8, zorder=5, label="MVP run (EMA 실행)")

    e2e_mean = df["e2e"].mean()
    ax.axhline(e2e_mean, color=C_E2E, linestyle=":", lw=1.5, alpha=0.8)
    ax.text(df["frame"].max() * 1.005, e2e_mean, f" 평균 {e2e_mean:.1f}ms",
            va="center", fontsize=13, color=C_E2E)

    ax.set_xlabel("프레임 인덱스", fontsize=16)
    ax.set_ylabel("소요 시간 (ms)", fontsize=16)
    ax.set_title(
        f"프레임별 E2E / Total 지연시간 타임라인\n"
        f"★ = MVP pipeline(EMA) 실행 프레임",
        fontsize=18, pad=20)
    ax.legend(fontsize=14, loc="upper right", framealpha=0.9)
    ax.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fpath = out / "03_timeline.png"
    fig.savefig(fpath, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  저장: {fpath}")

# ── 04 통계 요약 테이블 ────────────────────────────────────────────────────────
def chart_stats_table(stats: pd.DataFrame, df: pd.DataFrame, out: Path):
    fig = _fig()
    ax = fig.add_subplot(111)
    ax.axis("off")

    col_labels = ["count", "mean (ms)", "std", "min", "P50", "P95", "P99", "max"]
    row_labels  = list(stats.index)
    cell_data = []
    for row in row_labels:
        r = stats.loc[row]
        cell_data.append([
            str(int(r["count"])),
            f"{r['mean']:.1f}",
            f"{r['std']:.1f}",
            str(r["min"]),
            str(r["p50"]),
            str(r["p95"]),
            str(r["p99"]),
            str(r["max"]),
        ])

    row_colors_map = {
        "preprocess": C_PRE,
        "infer":      C_INFER,
        "postprocess": C_POST,
        "overhead":   C_OH,
        "total":      C_TOT,
        "e2e":        C_E2E,
    }
    row_colors = [[row_colors_map.get(r, "#CCCCCC")] + ["#F9F9F9"] * (len(col_labels) - 1)
                  for r in row_labels]

    tbl = ax.table(
        cellText=cell_data,
        rowLabels=row_labels,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(15)
    tbl.scale(1.6, 2.8)

    # 행 색상 적용
    for (row_idx, col_idx), cell in tbl.get_celld().items():
        if row_idx == 0:
            cell.set_facecolor("#2C3E50")
            cell.set_text_props(color="white", fontweight="bold")
        elif col_idx == -1:
            cell.set_facecolor(row_colors_map.get(row_labels[row_idx - 1], "#DDD"))
            cell.set_text_props(color="white", fontweight="bold")
        else:
            cell.set_facecolor("#F9F9F9" if row_idx % 2 == 0 else "#EFEFEF")

    ax.set_title(
        f"VoiceGuide 파이프라인 지연시간 통계\n"
        f"모델: {df['model'].iloc[0]}  |  엔진: {df['provider'].iloc[0]}  |  샘플: {len(df)}프레임",
        fontsize=20, pad=30, fontweight="bold")

    fig.tight_layout()
    fpath = out / "04_stats_table.png"
    fig.savefig(fpath, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  저장: {fpath}")

# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="VG_PERF 로그 분석 → PPT 차트 생성")
    parser.add_argument("log_file", help="adb logcat으로 수집한 .txt 파일 경로")
    parser.add_argument("--out", default="perf_report", help="출력 폴더 (기본: perf_report)")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"\n[1/5] 로그 파싱: {args.log_file}")
    df = parse_log(args.log_file)
    if df.empty:
        print("❌ VG_PERF 라인을 찾을 수 없습니다.")
        sys.exit(1)
    print(f"  → {len(df)}개 프레임 파싱 완료")

    print("\n[2/5] 통계 계산")
    stats = compute_stats(df)
    csv_path = out / "summary_stats.csv"
    stats.to_csv(csv_path, encoding="utf-8-sig")
    print(f"  저장: {csv_path}")
    print(stats.to_string())

    print("\n[3/5] 차트 생성")
    chart_breakdown(df, out)
    chart_histogram(df, out)
    chart_timeline(df, out)
    chart_stats_table(stats, df, out)

    print(f"\n[완료] 출력 폴더: {out.resolve()}")
    print(f"   FPS 추정: {1000 / df['e2e'].mean():.1f} fps (e2e 평균 기준)")

if __name__ == "__main__":
    main()
