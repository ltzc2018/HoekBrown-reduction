import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from typing import List, Tuple, Optional

# 设置中文字体
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "WenQuanYi Micro Hei"]
plt.rcParams["axes.unicode_minus"] = False


def plot_mohr_circles(
    sigma_ci: float,
    mb: float,
    s: float,
    a: float,
    c_eq: float,
    phi_eq: float,
    sigma_3_range: Tuple[float, float] = (0, 20),
    n_points: int = 100,
) -> plt.Figure:
    """绘制Mohr圆和Hoek-Brown包络线"""
    fig, ax = plt.subplots(figsize=(10, 7))

    # Hoek-Brown包络线
    sigma_3_vals = np.linspace(sigma_3_range[0], sigma_3_range[1], n_points)
    sigma_1_vals = []
    for s3 in sigma_3_vals:
        term = mb * (s3 / max(sigma_ci, 1e-10)) + s
        if term <= 0:
            term = 1e-10
        s1 = s3 + sigma_ci * (term ** a)
        sigma_1_vals.append(s1)

    ax.plot(sigma_3_vals, sigma_1_vals, "b-", linewidth=2.5, label="Hoek-Brown 包络线")

    # Mohr圆
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(sigma_3_vals)))
    for i, (s3, s1) in enumerate(zip(sigma_3_vals[::20], sigma_1_vals[::20])):
        center = (s1 + s3) / 2
        radius = (s1 - s3) / 2
        if radius > 0:
            circle = plt.Circle((center, 0), radius, fill=False, color=colors[i], alpha=0.6, linewidth=1.2)
            ax.add_patch(circle)

    # Mohr-Coulomb等效直线
    sigma_3_mc = np.linspace(0, sigma_3_range[1], 50)
    sigma_1_mc = 2 * c_eq * 0.001 * np.cos(phi_eq * np.pi / 180) * np.sin(sigma_3_mc * np.pi / 180 + phi_eq * np.pi / 180) / np.cos(phi_eq * np.pi / 180) + sigma_3_mc
    # 简化MC直线
    tan_phi = np.tan(phi_eq * np.pi / 180)
    mc_line = np.array([c_eq * 0.001 / (tan_phi + 1e-10) + s3 * (1 + tan_phi) for s3 in sigma_3_mc])
    valid = mc_line >= 0
    ax.plot(sigma_3_mc[valid], mc_line[valid], "r--", linewidth=2, label=f"MC等效 (c={c_eq:.1f}kPa, phi={phi_eq:.1f}\u00b0)")

    ax.set_xlabel("\u5c0f\u4e3b\u5e94\u529b \u03c3\u2083 (MPa)", fontsize=12)
    ax.set_ylabel("\u5927\u4e3b\u5e94\u529b \u03c3\u2081 (MPa)", fontsize=12)
    ax.set_title("Mohr\u5706\u4e0eHoek-Brown\u5305\u7edc\u7ebf", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=10)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)

    return fig


def plot_strain_softening(strain_results) -> plt.Figure:
    """绘制应变软化曲线"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    strains = [r.strain for r in strain_results]
    strengths = [r.reduced_strength for r in strain_results]
    ratios = [r.strength_ratio for r in strain_results]
    stiffnesses = [r.stiffness_ratio for r in strain_results]

    ax1 = axes[0]
    ax1.plot(strains, strengths, "b-", linewidth=2)
    ax1.set_xlabel("\u5e94\u53d8 \u03b5", fontsize=12)
    ax1.set_ylabel("\u5f3a\u5ea6 (MPa)", fontsize=12)
    ax1.set_title("\u5e94\u53d8\u67d4\u5316\u66f2\u7ebf (\u5f3a\u5ea6-\u5e94\u53d8)", fontsize=13, fontweight="bold")
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    ax2.plot(strains, ratios, "r-", linewidth=2, label="\u5f3a\u5ea6\u6bd4")
    ax2.plot(strains, stiffnesses, "g-", linewidth=2, label="\u521a\u5ea6\u6bd4")
    ax2.set_xlabel("\u5e94\u53d8 \u03b5", fontsize=12)
    ax2.set_ylabel("\u6bd4\u503c", fontsize=12)
    ax2.set_title("\u5f3a\u5ea6\u6bd4\u4e0e\u521a\u5ea6\u6bd4", fontsize=13, fontweight="bold")
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=10)

    plt.tight_layout()
    return fig


def plot_depth_profile(depth_profile: List[Tuple[float, float, float]]) -> plt.Figure:
    """绘制深度剖面折减结果"""
    fig, ax = plt.subplots(figsize=(10, 6))

    depths = [p[0] for p in depth_profile]
    stresses = [p[1] for p in depth_profile]
    cohesion = [p[2] for p in depth_profile]

    ax_twin = ax.twinx()

    line1 = ax.plot(depths, stresses, "bo-", linewidth=2, markersize=8, label="\u81ea\u91cd\u5e94\u529b (MPa)")
    line2 = ax_twin.plot(depths, cohesion, "rs-", linewidth=2, markersize=8, label="\u7b49\u6548\u7c98\u805a\u529b (kPa)")

    ax.set_xlabel("\u6df1\u5ea5 H (m)", fontsize=12)
    ax.set_ylabel("\u81ea\u91cd\u5e94\u529b (MPa)", color="b", fontsize=12)
    ax_twin.set_ylabel("\u7b49\u6548\u7c98\u805a\u529b (kPa)", color="r", fontsize=12)
    ax.set_title("\u6df1\u5ea6\u5256\u9762\u6298\u51cf\u7ed3\u679c", fontsize=14, fontweight="bold")
    ax.tick_params(axis="y", labelcolor="b")
    ax_twin.tick_params(axis="y", labelcolor="r")
    ax.grid(True, alpha=0.3)

    fig.legend(line1 + line2, ["\u81ea\u91cd\u5e94\u529b", "\u7b49\u6548\u7c98\u805a\u529b"], loc="upper right", fontsize=10)
    plt.tight_layout()
    return fig


def plot_modulus_comparison(modulus) -> plt.Figure:
    """绘制弹性模量四种方法对比"""
    fig, ax = plt.subplots(figsize=(10, 6))

    methods = ["\u65b9\u6cd51\n(\u57fa\u4e8eEi)", "\u65b9\u6cd52\n(\u57fa\u4e8e\u03c3ci)", "\u65b9\u6cd53\n(\u7ecf\u9a8c)", "\u65b9\u6cd54\n(Hoek)"]
    values = [modulus.Em_method1, modulus.Em_method2, modulus.Em_method3, modulus.Em_method4]
    colors = ["#4CAF50", "#2196F3", "#FF9800", "#9C27B0"]

    bars = ax.bar(methods, values, color=colors, edgecolor="black", linewidth=1.5)
    ax.set_ylabel("\u5f39\u6027\u6a21\u91cf E (MPa)", fontsize=12)
    ax.set_title("\u5ca9\u4f53\u5f39\u6027\u6a21\u91cf\u56db\u79cd\u8ba1\u7b97\u65b9\u6cd5\u5bf9\u6bd4", fontsize=14, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.3)

    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2.0, height + 50, f"{val:.1f}", ha="center", va="bottom", fontsize=11, fontweight="bold")

    return fig


def plot_roclab_style(analysis) -> plt.Figure:
    """绘制RocLab风格的强度分析图版"""
    fig = plt.figure(figsize=(14, 10), dpi=100)
    gs = fig.add_gridspec(2, 3, width_ratios=[2, 2, 3], height_ratios=[1, 1])
    
    ax1 = fig.add_subplot(gs[:, 0])
    ax2 = fig.add_subplot(gs[:, 1])
    ax_info = fig.add_subplot(gs[:, 2])
    ax_info.axis('off')
    
    hb = analysis.hb
    mc = analysis.mc
    modulus = analysis.modulus
    
    sigma_3_range = (0, 20)
    n_points = 100
    sigma_3_vals = np.linspace(sigma_3_range[0], sigma_3_range[1], n_points)
    sigma_1_vals = []
    for s3 in sigma_3_vals:
        term = hb.mb * (s3 / max(hb.sigma_ci, 1e-10)) + hb.s
        if term <= 0:
            term = 1e-10
        s1 = s3 + hb.sigma_ci * (term ** hb.a)
        sigma_1_vals.append(s1)
    
    ax1.plot(sigma_3_vals, sigma_1_vals, 'r-', linewidth=2.5)
    ax1.set_xlabel('Minor principal stress (MPa)', fontsize=10, fontweight='bold')
    ax1.set_ylabel('Major principal stress (MPa)', fontsize=10, fontweight='bold')
    ax1.grid(True, linestyle='--', alpha=0.3)
    ax1.set_xlim(left=0)
    ax1.set_ylim(bottom=0)
    ax1.tick_params(axis='both', labelsize=9)
    
    sigma_vals = np.linspace(0, sigma_3_range[1], n_points)
    c_mpa = mc.c_eq / 1000
    phi_rad = mc.phi_eq * np.pi / 180
    tau_vals = c_mpa * np.cos(phi_rad) + sigma_vals * np.sin(phi_rad)
    
    ax2.plot(sigma_vals, tau_vals, 'r-', linewidth=2.5)
    ax2.set_xlabel('Normal stress (MPa)', fontsize=10, fontweight='bold')
    ax2.set_ylabel('Shear stress (MPa)', fontsize=10, fontweight='bold')
    ax2.grid(True, linestyle='--', alpha=0.3)
    ax2.set_xlim(left=0)
    ax2.set_ylim(bottom=0)
    ax2.tick_params(axis='both', labelsize=9)
    
    info_text = f"""
Hoek-Brown Classification
─────────────────────────────────
intact uniaxial comp. strength (sigci) = {hb.sigma_ci:.2f} MPa
GSI = {hb.gsi:.0f}    mi = {hb.mi:.0f}    Disturbance factor (D) = {hb.D:.2f}
intact modulus (Ei) = {modulus.Em_method1:.0f} MPa
modulus ratio (MR) = 350

Hoek-Brown Criterion
─────────────────────────────────
mb = {hb.mb:.3f}    s = {hb.s:.6f}    a = {hb.a:.3f}

Mohr-Coulomb Fit
─────────────────────────────────
cohesion = {c_mpa:.3f} MPa    friction angle = {mc.phi_eq:.2f} deg

Rock Mass Parameters
─────────────────────────────────
tensile strength = {(hb.sigma_ci * (hb.s ** hb.a) * (-1)):.3f} MPa
uniaxial compressive strength = {hb.sigma_c_prime:.2f} MPa
global strength = {3 * hb.sigma_c_prime:.2f} MPa
deformation modulus = {modulus.Em_method4:.2f} MPa
"""
    
    ax_info.text(0.02, 0.98, info_text, transform=ax_info.transAxes,
                 fontfamily='Courier New', fontsize=10,
                 verticalalignment='top', horizontalalignment='left',
                 linespacing=1.4)
    
    fig.suptitle('Analysis of Rock Strength using HB Reduction System',
                 fontsize=14, fontweight='bold', y=0.98)
    
    plt.tight_layout()
    return fig


def plot_all_charts(analysis) -> dict:
    """生成所有图表，返回字典"""
    figures = {}
    figures["mohr"] = plot_mohr_circles(
        analysis.hb.sigma_ci, analysis.hb.mb, analysis.hb.s, analysis.hb.a,
        analysis.mc.c_eq, analysis.mc.phi_eq
    )
    figures["strain"] = plot_strain_softening(analysis.strain_results)
    figures["depth"] = plot_depth_profile(analysis.depth_profile)
    figures["modulus"] = plot_modulus_comparison(analysis.modulus)
    figures["roclab"] = plot_roclab_style(analysis)
    return figures
