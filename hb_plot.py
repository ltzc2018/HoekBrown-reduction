"""
hb_plot.py —— Hoek-Brown 强度折减分析可视化

布局约定（与 GUI 标签页对齐，每页严格 ≤2 个图形）:
  1. 包络线     : σ1-σ3 主应力图 + τ-σn 剪应力图
  2. 面积平衡+Mohr : 面积平衡图 + Mohr 圆图
  3. 软化+深度  : 单面板应变软化 + 深度剖面
  4. 模量+SRF   : 模量对比柱图 + 强度折减扫描

修正:
  * Mohr-Coulomb 直线: τ = c' + σn·tanφ'（σn-τ）/ 主应力空间标准换算
  * 抗拉强度: σt = -s·σci/mb
  * 统一主题、constrained_layout、窗口自适应
"""
from __future__ import annotations

import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from typing import List, Tuple, Optional

# ----------------------------------------------------------------------------
# 全局主题（学术风格：深蓝强调 + 暖红破坏线 + 浅灰底）
# ----------------------------------------------------------------------------
_CJK_FONT_CANDIDATES = [
    "PingFang SC", "Microsoft YaHei", "SimHei", "Heiti SC", "STHeiti",
    "Songti SC", "Arial Unicode MS", "Hiragino Sans GB",
    "WenQuanYi Micro Hei", "Noto Sans CJK SC",
]


def _pick_cjk_font() -> str:
    from matplotlib import font_manager
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in _CJK_FONT_CANDIDATES:
        if name in available:
            return name
    return "DejaVu Sans"


_CJK_FONT = _pick_cjk_font()
plt.rcParams["font.sans-serif"] = [_CJK_FONT, "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["axes.facecolor"] = "#f8fafc"
plt.rcParams["savefig.facecolor"] = "white"
plt.rcParams["axes.edgecolor"] = "#94a3b8"
plt.rcParams["axes.labelcolor"] = "#1e293b"
plt.rcParams["axes.titlecolor"] = "#0f172a"
plt.rcParams["xtick.color"] = "#475569"
plt.rcParams["ytick.color"] = "#475569"
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["axes.titlesize"] = 12
plt.rcParams["axes.labelsize"] = 10
plt.rcParams["legend.fontsize"] = 9
plt.rcParams["legend.frameon"] = True
plt.rcParams["legend.framealpha"] = 0.92
plt.rcParams["legend.edgecolor"] = "#e2e8f0"
plt.rcParams["grid.color"] = "#e2e8f0"
plt.rcParams["grid.linestyle"] = "--"
plt.rcParams["grid.linewidth"] = 0.65
plt.rcParams["grid.alpha"] = 0.7


class HBTheme:
    """统一配色（GUI 与图表共用语义）"""
    ENVELOPE = "#dc2626"          # H-B 包络线
    ENVELOPE_FILL = "#fef2f2"
    MC_LINE = "#1d4ed8"           # 等效 Mohr-Coulomb
    GRID = "#e2e8f0"
    ACCENT = "#7c3aed"            # 紫强调
    SECONDARY = "#0d9488"         # 青绿
    TERNARY = "#ea580c"           # 橙
    SPINE = "#94a3b8"
    TEXT = "#1e293b"
    TITLE = "#0f172a"
    PAIR_A = "#2563eb"
    PAIR_B = "#16a34a"
    BAR_PALETTE = ["#2563eb", "#16a34a", "#ea580c", "#7c3aed", "#dc2626", "#0d9488"]


def _style_axes(ax, title=None, xlabel=None, ylabel=None):
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(HBTheme.SPINE)
        ax.spines[spine].set_linewidth(1.0)
    ax.tick_params(axis="both", which="major", labelsize=9, length=3.5, width=0.8)
    ax.grid(True, ls="--", lw=0.65, alpha=0.7, color=HBTheme.GRID)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, fontsize=12, fontweight="bold", color=HBTheme.TITLE, pad=8)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10, color=HBTheme.TEXT)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10, color=HBTheme.TEXT)
    return ax


def _legend(ax, **kw):
    leg = ax.legend(**kw)
    if leg:
        frame = leg.get_frame()
        frame.set_facecolor("white")
        frame.set_edgecolor("#e2e8f0")
        frame.set_linewidth(0.8)
        frame.set_boxstyle("round,pad=0.35,rounding_size=0.25")
    return leg


def _hb_envelope(ci, mb, s, a, s3_arr):
    term = mb * (s3_arr / max(ci, 1e-12)) + s
    term = np.maximum(term, 1e-12)
    return s3_arr + ci * np.power(term, a)


def _mc_principal_line(s3v, c_eq_kpa: float, phi_eq_deg: float):
    """主应力空间 MC: σ1 = k·σ3 + b"""
    phi = math.radians(phi_eq_deg)
    c_mpa = c_eq_kpa / 1000.0
    k = (1 + math.sin(phi)) / max(1 - math.sin(phi), 1e-12)
    b = 2 * c_mpa * math.cos(phi) / max(1 - math.sin(phi), 1e-12)
    return k * s3v + b, c_mpa


# ============================================================================
# 1. 包络线页（2 图）
# ============================================================================

def plot_principal_envelope(
    sigma_ci: float, mb: float, s: float, a: float,
    c_eq_kpa: float, phi_eq_deg: float,
    sigma_3_range: Tuple[float, float] = (0, 20), n_points: int = 120,
) -> plt.Figure:
    """图1: 主应力空间 H-B 包络 + 等效 MC 直线"""
    fig, ax = plt.subplots(figsize=(7.5, 5.2), dpi=100, constrained_layout=True)
    s3v = np.linspace(sigma_3_range[0], sigma_3_range[1], n_points)
    s1v = _hb_envelope(sigma_ci, mb, s, a, s3v)
    mc_line, c_mpa = _mc_principal_line(s3v, c_eq_kpa, phi_eq_deg)

    ax.fill_between(s3v, 0, s1v, color=HBTheme.ENVELOPE_FILL, alpha=0.75, zorder=1)
    ax.plot(s3v, s1v, color=HBTheme.ENVELOPE, lw=2.4, label="Hoek-Brown 包络线", zorder=4)
    ax.plot(s3v, mc_line, color=HBTheme.MC_LINE, ls="--", lw=2.0,
            label=f"MC 等效 (c'={c_mpa:.3f} MPa, φ'={phi_eq_deg:.1f}°)", zorder=5)
    _style_axes(ax, title="主应力空间  σ₁ vs σ₃",
                xlabel="小主应力 σ₃ (MPa)", ylabel="大主应力 σ₁ (MPa)")
    _legend(ax, loc="lower right")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    return fig


def plot_shear_envelope(
    c_eq_kpa: float, phi_eq_deg: float,
    sigma_n_max: float = 20.0, n_points: int = 120,
) -> plt.Figure:
    """图2: 剪应力空间 等效 MC 直线 τ = c'cosφ + σn·sinφ（RocLab 展示式）"""
    fig, ax = plt.subplots(figsize=(7.5, 5.2), dpi=100, constrained_layout=True)
    c_mpa = c_eq_kpa / 1000.0
    phi = math.radians(phi_eq_deg)
    sn = np.linspace(0, sigma_n_max, n_points)
    # RocLab 风格剪应力展示（与原 plot_roclab_style 一致）
    tau = c_mpa * math.cos(phi) + sn * math.sin(phi)
    ax.fill_between(sn, 0, tau, color=HBTheme.ENVELOPE_FILL, alpha=0.7, zorder=1)
    ax.plot(sn, tau, color=HBTheme.ENVELOPE, lw=2.4,
            label=f"等效 MC (c'={c_mpa:.3f} MPa, φ'={phi_eq_deg:.1f}°)", zorder=4)
    ax.plot(0, c_mpa * math.cos(phi), marker="o", color=HBTheme.MC_LINE, markersize=7, zorder=5)
    ax.annotate(f"截距 ≈ c'cosφ", xy=(0, c_mpa * math.cos(phi)),
                xytext=(sigma_n_max * 0.18, c_mpa * math.cos(phi) + max(tau) * 0.08),
                fontsize=9, color=HBTheme.MC_LINE,
                arrowprops=dict(arrowstyle="-|>", color=HBTheme.MC_LINE, lw=1.0))
    _style_axes(ax, title="剪应力空间  τ vs σn",
                xlabel="法向应力 σn (MPa)", ylabel="剪应力 τ (MPa)")
    _legend(ax, loc="lower right")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    return fig


# ============================================================================
# 2. 面积平衡 + Mohr（各 1 图）
# ============================================================================

def plot_mohr_circles(
    sigma_ci: float, mb: float, s: float, a: float,
    c_eq_kpa: float, phi_eq_deg: float,
    sigma_3_range: Tuple[float, float] = (0, 20), n_points: int = 100,
) -> plt.Figure:
    """Mohr 圆 + H-B 包络 + 等效 MC（主应力空间）"""
    fig, ax = plt.subplots(figsize=(7.5, 5.5), dpi=100, constrained_layout=True)
    s3v = np.linspace(sigma_3_range[0], sigma_3_range[1], n_points)
    s1v = _hb_envelope(sigma_ci, mb, s, a, s3v)
    ax.fill_between(s3v, 0, s1v, color=HBTheme.ENVELOPE_FILL, alpha=0.75, zorder=1)
    ax.plot(s3v, s1v, color=HBTheme.ENVELOPE, lw=2.4, label="Hoek-Brown 包络线", zorder=4)

    colors = plt.cm.viridis(np.linspace(0.15, 0.85, max(1, len(s3v) // 20)))
    for i, (s3, s1) in enumerate(zip(s3v[::20], s1v[::20])):
        c, r = (s1 + s3) / 2.0, (s1 - s3) / 2.0
        if r > 0:
            ax.add_patch(plt.Circle((c, 0), r, fill=False, color=colors[i],
                                    alpha=0.6, lw=1.2, zorder=3))

    mc_line, c_mpa = _mc_principal_line(s3v, c_eq_kpa, phi_eq_deg)
    ax.plot(s3v, mc_line, color=HBTheme.MC_LINE, ls="--", lw=2.0,
            label=f"MC 等效 (c'={c_mpa:.3f} MPa, φ'={phi_eq_deg:.1f}°)", zorder=5)
    _style_axes(ax, title="Mohr 圆与 Hoek-Brown 包络线",
                xlabel="小主应力 σ₃ (MPa)", ylabel="大主应力 σ₁ (MPa)")
    _legend(ax, loc="lower right")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    return fig


def plot_area_balance(analysis) -> plt.Figure:
    """面积平衡: σn-τ 空间 H-B 包络 + 等效 MC 直线"""
    fig, ax = plt.subplots(figsize=(7.5, 5.5), dpi=100, constrained_layout=True)
    hb = analysis.hb
    mc = analysis.mc
    s3t = -hb.s * hb.sigma_ci / max(hb.mb, 1e-12)
    s3v = np.linspace(s3t + 1e-3, analysis.sigma_3max, 300)
    term = np.maximum(hb.mb * (s3v / hb.sigma_ci) + hb.s, 1e-9)
    s1 = s3v + hb.sigma_ci * np.power(term, hb.a)
    K = 1.0 + hb.a * hb.mb * np.power(term, hb.a - 1.0)
    ds = (s1 - s3v) / 2.0
    sn = (s1 + s3v) / 2.0 - ds * (K - 1.0) / (K + 1.0)
    tau = ds * 2.0 * np.sqrt(K) / (K + 1.0)
    ax.fill_between(sn, 0, tau, color=HBTheme.ENVELOPE_FILL, alpha=0.7, zorder=1)
    ax.plot(sn, tau, color=HBTheme.ENVELOPE, lw=2.4, label="Hoek-Brown 包络线", zorder=4)
    c_mpa = mc.c_eq / 1000.0
    phi = math.radians(mc.phi_eq)
    sn_line = np.linspace(0, max(sn) if len(sn) else 1.0, 50)
    ax.plot(sn_line, c_mpa + sn_line * math.tan(phi), color=HBTheme.MC_LINE,
            ls="--", lw=2.0, label=f"MC 等效 (c'={c_mpa:.3f} MPa, φ'={mc.phi_eq:.1f}°)", zorder=5)
    ax.plot(0, c_mpa, marker="o", color=HBTheme.MC_LINE, markersize=7, zorder=6)
    ax.annotate(f"c' = {c_mpa:.3f} MPa", xy=(0, c_mpa),
                xytext=(max(sn) * 0.15 if len(sn) else 1, c_mpa + (max(tau) if len(tau) else 1) * 0.12),
                fontsize=9, color=HBTheme.MC_LINE, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color=HBTheme.MC_LINE, lw=1.1))
    _style_axes(ax, title="面积平衡等效 Mohr-Coulomb (σn-τ)",
                xlabel="法向应力 σn (MPa)", ylabel="剪应力 τ (MPa)")
    _legend(ax, loc="lower right")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    return fig


# ============================================================================
# 3. 软化 + 深度（各 1 图；软化为单面板）
# ============================================================================

def plot_strain_softening(strain_results) -> plt.Figure:
    """峰后应变软化（单图双轴：σcm + 强度比 / c'）— 保证与深度剖面合计 ≤2 图"""
    fig, ax = plt.subplots(figsize=(7.5, 5.2), dpi=100, constrained_layout=True)
    if not strain_results:
        ax.set_title("无应变软化数据")
        return fig
    gp = [r.plastic_strain for r in strain_results]
    sc = [r.sigma_cm for r in strain_results]
    sr = [r.strength_ratio for r in strain_results]
    c = [r.c_eq for r in strain_results]

    ax.fill_between(gp, sc, min(sc), color=HBTheme.PAIR_A, alpha=0.12, zorder=1)
    ax.plot(gp, sc, color=HBTheme.PAIR_A, lw=2.2, marker="o", markersize=3.5,
            label="岩体强度 σcm (MPa)", zorder=3)
    ax.set_xlabel("塑性剪应变 γp")
    ax.set_ylabel("岩体强度 σcm (MPa)", color=HBTheme.PAIR_A)
    ax.tick_params(axis="y", colors=HBTheme.PAIR_A, labelcolor=HBTheme.PAIR_A)

    ax2 = ax.twinx()
    ax2.plot(gp, sr, color=HBTheme.ENVELOPE, lw=2.0, marker="s", markersize=3.5,
             label="强度比", zorder=3)
    ax2.plot(gp, [v / max(c[0], 1e-9) for v in c], color=HBTheme.SECONDARY, lw=1.6,
             ls=":", marker=None, label="c' 相对峰值", zorder=2)
    ax2.set_ylabel("强度比 / c' 比", color=HBTheme.ENVELOPE)
    ax2.tick_params(axis="y", colors=HBTheme.ENVELOPE, labelcolor=HBTheme.ENVELOPE)
    for sp in ("top",):
        ax2.spines[sp].set_visible(False)
    ax2.spines["right"].set_color(HBTheme.ENVELOPE)

    _style_axes(ax, title="峰后应变软化 (σcm · 强度比 · c')")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    _legend(ax, handles=lines1 + lines2, labels=labels1 + labels2, loc="upper right")
    return fig


def plot_depth_profile(depth_profile: List[Tuple[float, float, float]]) -> plt.Figure:
    """深度剖面: 自重应力 + 局部等效粘聚力"""
    fig, ax = plt.subplots(figsize=(7.5, 5.2), dpi=100, constrained_layout=True)
    depths = [p[0] for p in depth_profile]
    stresses = [p[1] for p in depth_profile]
    cohesion = [p[2] for p in depth_profile]
    ax_twin = ax.twinx()
    ax.fill_between(depths, stresses, color=HBTheme.PAIR_A, alpha=0.12, zorder=1)
    l1 = ax.plot(depths, stresses, color=HBTheme.PAIR_A, lw=2.2, marker="o",
                 markersize=6, label="自重应力 (MPa)", zorder=3)
    l2 = ax_twin.plot(depths, cohesion, color=HBTheme.ENVELOPE, lw=2.2, marker="s",
                      markersize=6, label="等效粘聚力 c' (kPa)", zorder=3)
    ax.set_xlabel("深度 H (m)")
    ax.set_ylabel("自重应力 (MPa)", color=HBTheme.PAIR_A)
    ax_twin.set_ylabel("等效粘聚力 c' (kPa)", color=HBTheme.ENVELOPE)
    _style_axes(ax, title="深度剖面折减结果")
    ax.tick_params(axis="y", colors=HBTheme.PAIR_A, labelcolor=HBTheme.PAIR_A)
    ax_twin.tick_params(axis="y", colors=HBTheme.ENVELOPE, labelcolor=HBTheme.ENVELOPE)
    for sp in ("top",):
        ax_twin.spines[sp].set_visible(False)
    fig.legend(l1 + l2, ["自重应力", "等效粘聚力 c'"], loc="upper right",
               fontsize=9, bbox_to_anchor=(0.98, 0.96))
    return fig


# ============================================================================
# 4. 模量 + SRF
# ============================================================================

def plot_modulus_comparison(modulus) -> plt.Figure:
    """四种变形模量方法对比"""
    fig, ax = plt.subplots(figsize=(7.5, 5.2), dpi=100, constrained_layout=True)
    methods = ["Hoek(2002)\n[推荐]", "Hoek&Diederichs\n(2006)", "模量比法", "Serafim&Pereira\n(1983)"]
    values = [modulus.Em_hoek2002, modulus.Em_hd2006, modulus.Em_mr, modulus.Em_serafim]
    colors = HBTheme.BAR_PALETTE
    bars = ax.bar(methods, values, color=colors, edgecolor="white", lw=1.4,
                  width=0.62, zorder=3)
    _style_axes(ax, title="岩体变形模量四种计算方法对比",
                xlabel=None, ylabel="变形模量 Em (MPa)")
    ax.set_ylim(0, max(values) * 1.18 if max(values) > 0 else 1)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + max(values) * 0.02,
                f"{val:.0f}", ha="center", va="bottom", fontsize=10,
                fontweight="bold", color=HBTheme.TEXT)
    ax.annotate("推荐", xy=(0, values[0]),
                xytext=(0, values[0] * 1.10),
                ha="center", fontsize=9, fontweight="bold",
                color=HBTheme.TITLE,
                arrowprops=dict(arrowstyle="-|>", color=HBTheme.TITLE, lw=1.2))
    return fig


def plot_srf_scan(srf_scan: List[Tuple[float, float, float]]) -> plt.Figure:
    """强度折减扫描: F vs c', φ'"""
    fig, ax = plt.subplots(figsize=(7.5, 5.2), dpi=100, constrained_layout=True)
    if not srf_scan:
        ax.set_title("无强度折减数据")
        return fig
    F = [r[0] for r in srf_scan]
    c = [r[1] for r in srf_scan]
    ph = [r[2] for r in srf_scan]
    ax.fill_between(F, c, color=HBTheme.PAIR_A, alpha=0.12, zorder=1)
    ax.plot(F, c, color=HBTheme.PAIR_A, lw=2.2, marker="o", markersize=6,
            label="等效粘聚力 c' (kPa)", zorder=3)
    _style_axes(ax, title="强度折减系数扫描 (SRF)",
                xlabel="强度折减系数 F", ylabel="等效粘聚力 c' (kPa)")
    ax.tick_params(axis="y", colors=HBTheme.PAIR_A, labelcolor=HBTheme.PAIR_A)
    ax2 = ax.twinx()
    ax2.plot(F, ph, color=HBTheme.ENVELOPE, lw=2.2, marker="s", markersize=6,
             label="等效内摩擦角 φ' (°)", zorder=3)
    ax2.set_ylabel("等效内摩擦角 φ' (°)", color=HBTheme.ENVELOPE)
    ax2.tick_params(axis="y", colors=HBTheme.ENVELOPE, labelcolor=HBTheme.ENVELOPE)
    for sp in ("top",):
        ax2.spines[sp].set_visible(False)
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    fig.legend(lines1 + lines2, labels1 + labels2, loc="upper right",
               fontsize=9, bbox_to_anchor=(0.98, 0.96))
    return fig


# ============================================================================
# 兼容: RocLab 风格双图（不含信息卡，恰好 2 图）
# ============================================================================

def _info_card(ax, title, rows):
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    box = FancyBboxPatch((0.02, 0.02), 0.96, 0.96,
                         boxstyle="round,pad=0.02,rounding_size=0.03",
                         linewidth=1.0, edgecolor="#e2e8f0",
                         facecolor="#f8fafc", transform=ax.transAxes, zorder=1)
    ax.add_patch(box)
    ax.text(0.5, 0.96, title, transform=ax.transAxes, ha="center", va="top",
            fontsize=11, fontweight="bold", color=HBTheme.TITLE, zorder=3)
    ax.plot([0.08, 0.92], [0.905, 0.905], transform=ax.transAxes,
            color=HBTheme.TITLE, lw=1.0, zorder=3)
    y = 0.86
    step = 0.072
    for item in rows:
        label, value, *opt = item
        color = opt[0] if opt else HBTheme.TEXT
        ax.text(0.08, y, label, transform=ax.transAxes, ha="left", va="top",
                fontsize=8.5, color="#64748b", fontfamily="monospace", zorder=3)
        ax.text(0.92, y, value, transform=ax.transAxes, ha="right", va="top",
                fontsize=9, color=color, fontweight="bold",
                fontfamily="monospace", zorder=3)
        y -= step


def plot_roclab_style(analysis) -> plt.Figure:
    """兼容旧接口: 仅 2 个绘图轴（主应力 + 剪应力），参数由 GUI 指标卡展示。"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.2), dpi=100, constrained_layout=True)
    hb, mc = analysis.hb, analysis.mc
    s3r = (0.0, 20.0)
    s3v = np.linspace(s3r[0], s3r[1], 120)
    s1v = _hb_envelope(hb.sigma_ci, hb.mb, hb.s, hb.a, s3v)
    mc_line, c_mpa = _mc_principal_line(s3v, mc.c_eq, mc.phi_eq)

    ax1.fill_between(s3v, 0, s1v, color=HBTheme.ENVELOPE_FILL, alpha=0.7, zorder=1)
    ax1.plot(s3v, s1v, color=HBTheme.ENVELOPE, lw=2.4, zorder=4, label="H-B")
    ax1.plot(s3v, mc_line, color=HBTheme.MC_LINE, ls="--", lw=1.8, zorder=5, label="MC")
    _style_axes(ax1, title="主应力空间 σ₁ vs σ₃",
                xlabel="σ₃ (MPa)", ylabel="σ₁ (MPa)")
    _legend(ax1, loc="lower right")
    ax1.set_xlim(left=0)
    ax1.set_ylim(bottom=0)

    phi = math.radians(mc.phi_eq)
    sv = np.linspace(0, s3r[1], 120)
    tauv = c_mpa * math.cos(phi) + sv * math.sin(phi)
    ax2.fill_between(sv, 0, tauv, color=HBTheme.ENVELOPE_FILL, alpha=0.7, zorder=1)
    ax2.plot(sv, tauv, color=HBTheme.ENVELOPE, lw=2.4, zorder=4)
    ax2.plot(0, c_mpa * math.cos(phi), marker="o", color=HBTheme.MC_LINE, markersize=6, zorder=5)
    _style_axes(ax2, title="剪应力空间 τ vs σn",
                xlabel="σn (MPa)", ylabel="τ (MPa)")
    ax2.set_xlim(left=0)
    ax2.set_ylim(bottom=0)
    fig.suptitle("Hoek-Brown 强度包络线", fontsize=13, fontweight="bold", color=HBTheme.TITLE)
    return fig
