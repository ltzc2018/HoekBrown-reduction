"""
hb_plot.py —— Hoek-Brown 强度折减分析可视化（优化版）

修正原版问题:
  * Mohr-Coulomb 等效直线公式错误 → 重写为标准 τ = c' + σn·tanφ'
  * plot_roclab_style 中硬编码 "MR = 350" → 改为显示真实变形模量与参数
  * 抗拉强度误算为 -σci·s^a → 改为正确 σt = -s·σci/mb
  * 新增: 强度折减扫描图、面积平衡(σn-τ)拟合图、应变软化曲线
"""
from __future__ import annotations

import math
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from typing import List, Tuple, Optional

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "WenQuanYi Micro Hei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _hb_envelope(ci, mb, s, a, s3_arr):
    out = []
    for s3 in s3_arr:
        term = mb * (s3 / max(ci, 1e-12)) + s
        if term <= 0:
            term = 1e-12
        out.append(s3 + ci * math.pow(term, a))
    return np.array(out)


def plot_mohr_circles(
    sigma_ci: float, mb: float, s: float, a: float,
    c_eq_kpa: float, phi_eq_deg: float,
    sigma_3_range: Tuple[float, float] = (0, 20), n_points: int = 100,
) -> plt.Figure:
    """Hoek-Brown 包络线 + Mohr 圆 + 等效 Mohr-Coulomb 直线"""
    fig, ax = plt.subplots(figsize=(10, 7))
    s3v = np.linspace(sigma_3_range[0], sigma_3_range[1], n_points)
    s1v = _hb_envelope(sigma_ci, mb, s, a, s3v)
    ax.plot(s3v, s1v, "b-", lw=2.5, label="Hoek-Brown 包络线")

    colors = plt.cm.viridis(np.linspace(0.1, 0.9, max(1, len(s3v) // 20)))
    for i, (s3, s1) in enumerate(zip(s3v[::20], s1v[::20])):
        c, r = (s1 + s3) / 2.0, (s1 - s3) / 2.0
        if r > 0:
            ax.add_patch(plt.Circle((c, 0), r, fill=False, color=colors[i], alpha=0.6, lw=1.2))

    # 等效 MC 直线 (σ1-σ3 空间): σ1 = σ3·(1+sinφ)/(1-sinφ) + 2c·cosφ/(1-sinφ)
    phi = math.radians(phi_eq_deg)
    c_mpa = c_eq_kpa / 1000.0
    k = (1 + math.sin(phi)) / (1 - math.sin(phi))
    b = 2 * c_mpa * math.cos(phi) / (1 - math.sin(phi))
    mc_line = k * s3v + b
    ax.plot(s3v, mc_line, "r--", lw=2, label=f"MC 等效 (c={c_mpa:.3f} MPa, φ={phi_eq_deg:.1f}°)")

    ax.set_xlabel("小主应力 σ₃ (MPa)")
    ax.set_ylabel("大主应力 σ₁ (MPa)")
    ax.set_title("Mohr 圆与 Hoek-Brown 包络线")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=10)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    return fig


def plot_strain_softening(strain_results) -> plt.Figure:
    """峰后应变软化曲线: 强度 / 强度比 vs 塑性剪应变"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    if not strain_results:
        axes[0].set_title("无应变软化数据")
        return fig
    gp = [r.plastic_strain for r in strain_results]
    sc = [r.sigma_cm for r in strain_results]
    sr = [r.strength_ratio for r in strain_results]
    c = [r.c_eq for r in strain_results]
    ph = [r.phi_eq for r in strain_results]

    axes[0].plot(gp, sc, "b-", lw=2, label="岩体强度 σcm")
    ax2 = axes[0].twinx()
    ax2.plot(gp, sr, "r-", lw=2, label="强度比")
    axes[0].set_xlabel("塑性剪应变 γp")
    axes[0].set_ylabel("岩体强度 σcm (MPa)", color="b")
    ax2.set_ylabel("强度比 (相对峰值)", color="r")
    axes[0].set_title("峰后应变软化 (强度-应变)")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(gp, c, "g-", lw=2, label="等效粘聚力 c' (kPa)")
    axes[1].set_xlabel("塑性剪应变 γp")
    axes[1].set_ylabel("等效 c' (kPa)", color="g")
    ax3 = axes[1].twinx()
    ax3.plot(gp, ph, "m-", lw=2, label="等效内摩擦角 φ' (°)")
    ax3.set_ylabel("等效 φ' (°)", color="m")
    axes[1].set_title("峰后应变软化 (等效 MC 参数)")
    axes[1].grid(True, alpha=0.3)
    plt.tight_layout()
    return fig


def plot_depth_profile(depth_profile: List[Tuple[float, float, float]]) -> plt.Figure:
    """深度剖面: 自重应力 + 局部等效粘聚力"""
    fig, ax = plt.subplots(figsize=(10, 6))
    depths = [p[0] for p in depth_profile]
    stresses = [p[1] for p in depth_profile]
    cohesion = [p[2] for p in depth_profile]
    ax_twin = ax.twinx()
    l1 = ax.plot(depths, stresses, "bo-", lw=2, markersize=8, label="自重应力 (MPa)")
    l2 = ax_twin.plot(depths, cohesion, "rs-", lw=2, markersize=8, label="等效粘聚力 c' (kPa)")
    ax.set_xlabel("深度 H (m)")
    ax.set_ylabel("自重应力 (MPa)", color="b")
    ax_twin.set_ylabel("等效粘聚力 c' (kPa)", color="r")
    ax.set_title("深度剖面折减结果")
    ax.tick_params(axis="y", labelcolor="b")
    ax_twin.tick_params(axis="y", labelcolor="r")
    ax.grid(True, alpha=0.3)
    fig.legend(l1 + l2, ["自重应力", "等效粘聚力 c'"], loc="upper right", fontsize=10)
    plt.tight_layout()
    return fig


def plot_modulus_comparison(modulus) -> plt.Figure:
    """四种变形模量方法对比"""
    fig, ax = plt.subplots(figsize=(10, 6))
    methods = ["Hoek(2002)\n[推荐]", "Hoek&Diederichs\n(2006)", "模量比法", "Serafim&Pereira\n(1983)"]
    values = [modulus.Em_hoek2002, modulus.Em_hd2006, modulus.Em_mr, modulus.Em_serafim]
    colors = ["#4CAF50", "#2196F3", "#FF9800", "#9C27B0"]
    bars = ax.bar(methods, values, color=colors, edgecolor="black", lw=1.5)
    ax.set_ylabel("变形模量 Em (MPa)")
    ax.set_title("岩体变形模量四种计算方法对比")
    ax.grid(True, axis="y", alpha=0.3)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 50,
                f"{val:.0f}", ha="center", va="bottom", fontsize=11, fontweight="bold")
    return fig


def plot_srf_scan(srf_scan: List[Tuple[float, float, float]]) -> plt.Figure:
    """强度折减扫描: 折减系数 F vs c', φ'"""
    fig, ax = plt.subplots(figsize=(10, 6))
    if not srf_scan:
        ax.set_title("无强度折减数据")
        return fig
    F = [r[0] for r in srf_scan]
    c = [r[1] for r in srf_scan]
    ph = [r[2] for r in srf_scan]
    ax.plot(F, c, "bo-", lw=2, label="等效粘聚力 c' (kPa)")
    ax.set_xlabel("强度折减系数 F")
    ax.set_ylabel("等效粘聚力 c' (kPa)", color="b")
    ax.grid(True, alpha=0.3)
    ax2 = ax.twinx()
    ax2.plot(F, ph, "rs-", lw=2, label="等效内摩擦角 φ' (°)")
    ax2.set_ylabel("等效内摩擦角 φ' (°)", color="r")
    ax.set_title("强度折减系数扫描 (SRF)")
    fig.legend(loc="upper right", fontsize=10)
    plt.tight_layout()
    return fig


def plot_area_balance(analysis) -> plt.Figure:
    """面积平衡视角: σn-τ 空间 H-B 包络线 + 等效 MC 直线"""
    fig, ax = plt.subplots(figsize=(10, 7))
    hb = analysis.hb
    mc = analysis.mc
    s3t = -hb.s * hb.sigma_ci / max(hb.mb, 1e-12)
    s3max = analysis.sigma_3max
    s3v = np.linspace(s3t + 1e-3, s3max, 300)
    sn, tau = [], []
    for s3 in s3v:
        term = max(hb.mb * (s3 / hb.sigma_ci) + hb.s, 1e-9)
        s1 = s3 + hb.sigma_ci * math.pow(term, hb.a)
        K = 1.0 + hb.a * hb.mb * math.pow(term, hb.a - 1.0)
        ds = (s1 - s3) / 2.0
        sn.append((s1 + s3) / 2.0 - ds * (K - 1.0) / (K + 1.0))
        tau.append(ds * 2.0 * math.sqrt(K) / (K + 1.0))
    sn, tau = np.array(sn), np.array(tau)
    ax.plot(sn, tau, "b-", lw=2.5, label="Hoek-Brown 包络线")
    c_mpa = mc.c_eq / 1000.0
    phi = math.radians(mc.phi_eq)
    sn_line = np.linspace(min(sn), max(sn), 50)
    ax.plot(sn_line, c_mpa + sn_line * math.tan(phi), "r--", lw=2,
            label=f"MC 等效 (c={c_mpa:.3f} MPa, φ={mc.phi_eq:.1f}°)")
    ax.set_xlabel("法向应力 σn (MPa)")
    ax.set_ylabel("剪应力 τ (MPa)")
    ax.set_title("面积平衡等效 Mohr-Coulomb (σn-τ 空间)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=10)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    return fig


def plot_roclab_style(analysis) -> plt.Figure:
    """RocLab 风格分析图版（修正 MR 硬编码与抗拉强度误算）"""
    fig = plt.figure(figsize=(14, 10), dpi=100)
    gs = fig.add_gridspec(2, 3, width_ratios=[2, 2, 3], height_ratios=[1, 1])
    ax1 = fig.add_subplot(gs[:, 0])
    ax2 = fig.add_subplot(gs[:, 1])
    ax_info = fig.add_subplot(gs[:, 2])
    ax_info.axis("off")

    hb, mc, modulus = analysis.hb, analysis.mc, analysis.modulus
    s3r = (0, 20)
    s3v = np.linspace(s3r[0], s3r[1], 100)
    s1v = _hb_envelope(hb.sigma_ci, hb.mb, hb.s, hb.a, s3v)
    ax1.plot(s3v, s1v, "r-", lw=2.5)
    ax1.set_xlabel("Minor principal stress (MPa)")
    ax1.set_ylabel("Major principal stress (MPa)")
    ax1.grid(True, ls="--", alpha=0.3)
    ax1.set_xlim(left=0)
    ax1.set_ylim(bottom=0)

    sv = np.linspace(0, s3r[1], 100)
    c_mpa = mc.c_eq / 1000.0
    phi = math.radians(mc.phi_eq)
    tauv = c_mpa * math.cos(phi) + sv * math.sin(phi)
    ax2.plot(sv, tauv, "r-", lw=2.5)
    ax2.set_xlabel("Normal stress (MPa)")
    ax2.set_ylabel("Shear stress (MPa)")
    ax2.grid(True, ls="--", alpha=0.3)
    ax2.set_xlim(left=0)
    ax2.set_ylim(bottom=0)

    info = f"""
Hoek-Brown Classification
─────────────────────────────────
intact UCS (σci)      = {hb.sigma_ci:.2f} MPa
GSI = {hb.gsi:.0f}    mi = {hb.mi:.0f}    Disturbance (D) = {hb.D:.2f}
─────────────────────────────────
Hoek-Brown Criterion
mb = {hb.mb:.3f}    s = {hb.s:.6f}    a = {hb.a:.3f}
─────────────────────────────────
Rock Mass Parameters
tensile strength  = {hb.sigma_t:.3f} MPa
UCS (σcm)         = {hb.sigma_cm:.3f} MPa
deformation mod.  = {modulus.Em_hoek2002:.0f} MPa (Hoek 2002)
─────────────────────────────────
Mohr-Coulomb Fit
cohesion    = {c_mpa:.3f} MPa
friction φ' = {mc.phi_eq:.2f} deg
dilatancy ψ'= {mc.psi_eq:.2f} deg
σ3max (area) = {analysis.sigma_3max:.3f} MPa
"""
    ax_info.text(0.02, 0.98, info, transform=ax_info.transAxes,
                 fontfamily="Courier New", fontsize=10, va="top", linespacing=1.4)
    fig.suptitle("Analysis of Rock Strength using HB Reduction System (Optimized)",
                 fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout()
    return fig


def plot_all_charts(analysis) -> dict:
    """生成所有图表，返回字典"""
    figures = {
        "mohr": plot_mohr_circles(
            analysis.hb.sigma_ci, analysis.hb.mb, analysis.hb.s, analysis.hb.a,
            analysis.mc.c_eq, analysis.mc.phi_eq),
        "strain": plot_strain_softening(analysis.strain_results),
        "depth": plot_depth_profile(analysis.depth_profile),
        "modulus": plot_modulus_comparison(analysis.modulus),
        "srf": plot_srf_scan(analysis.srf_scan),
        "area": plot_area_balance(analysis),
        "roclab": plot_roclab_style(analysis),
    }
    return figures
