"""
Hoek-Brown 2002 岩体强度折减分析核心引擎（深度优化版）
================================================================

严格实现 Hoek, Carranza-Torres & Corkum (2002) 广义 Hoek-Brown 准则，
并与主流岩土软件计算流程对齐：

  * RocLab (RocScience)      —— GSI→mb/s/a、岩体 UCS、变形模量、等效 Mohr-Coulomb
  * FLAC3D / FLAC / Phase2   —— H-B 直接强度折减 (SRF) 与应变软化
  * Slide / Slide2           —— 等效 Mohr-Coulomb 强度参数输入

相比原版的关键修正（详见 README）：
  1. mb = mi * exp((GSI-100)/(28-14D))   [原版误写为 D * exp(...)，偏差约 27 倍]
  2. 等效粘聚力 c' 采用 Hoek(2002) eq.13  [原版公式完全错误]
  3. 新增「面积平衡法」确定等效 Mohr-Coulomb 范围上限 σ3max（隧道 eq.18 / 边坡 eq.19），
     与 RocLab 一致；原版仅用单点 σ3 估算
  4. 新增强度折减系数 SRF（H-B 参数折减 / 等效 MC 参数折减），支撑 SRM 稳定性分析
  5. 重写峰后应变软化模型：随塑性剪应变 GSI 由峰值退化为残差（与 FLAC 软化 H-B 对齐）
  6. 变形模量统一为 Hoek(2002) 推荐式 + Serafim&Pereira(1983) + Hoek&Diederichs(2006) 三种方法

引用：
  Hoek E., Carranza-Torres C., Corkum B. (2002). Hoek-Brown failure criterion - 2002 edition.
  Hoek E., Diederichs M.S. (2006). Empirical estimation of rock mass modulus.
  Serafim J.L., Pereira J.P. (1983). Consideration of the geomechanical classification of Bieniawski.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Sequence

# 数值保护下限
_EPS = 1e-12

# ============================================================================
# 1. Hoek-Brown 基本强度参数
# ============================================================================

@dataclass
class HBParameters:
    """Hoek-Brown 基本强度参数（GSI 折减：完整岩石 → 岩体）"""

    sigma_ci: float                 # 完整岩石单轴抗压强度 σci (MPa)
    gsi: float                      # 地质强度指标 GSI (0~100)
    mi: float                       # 完整岩石材料常数 mi
    D: float = 0.0                  # 扰动因子 D (0=未扰动, 1=极扰动)
    gamma: float = 0.027            # 岩体重度 γ (MN/m³)
    height: float = 100.0           # 开挖埋深 / 边坡高度 H (m)

    # ---- 计算字段（compute 后填充）----
    mb: float = field(default=0.0, init=False)
    s: float = field(default=0.0, init=False)
    a: float = field(default=0.0, init=False)
    sigma_cm: float = field(default=0.0, init=False)     # 岩体单轴抗压强度 σcm (MPa)
    sigma_t: float = field(default=0.0, init=False)      # 岩体抗拉强度 σt (MPa)

    def compute(self) -> "HBParameters":
        """计算广义 Hoek-Brown 岩体常数 mb, s, a 及派生强度（Hoek 2002, eq.3~7）"""
        GSI, mi, D, sigma_ci = self.gsi, self.mi, self.D, self.sigma_ci
        # [修正] 原版误用 D 代替 mi，此处严格按 Hoek(2002) eq.3
        self.mb = mi * math.exp((GSI - 100.0) / (28.0 - 14.0 * D))        # eq.3
        self.s = math.exp((GSI - 100.0) / (9.0 - 3.0 * D))                # eq.4
        self.a = 0.5 + (1.0 / 6.0) * (math.exp(-GSI / 15.0) - math.exp(-20.0 / 3.0))  # eq.5
        # 岩体单轴抗压强度（令 σ3=0）：σcm = σci · s^a  (eq.6)
        self.sigma_cm = sigma_ci * math.pow(self.s, self.a)
        # 岩体抗拉强度（双轴拉伸条件 σ1=σ3=σt）：σt = -s·σci/mb  (eq.7)
        self.sigma_t = -self.s * sigma_ci / max(self.mb, _EPS)
        return self

    def _compute_term(self, sigma3: float) -> float:
        """计算包络线公式中的公共项: mb·σ3/σci + s"""
        term = self.mb * (sigma3 / max(self.sigma_ci, _EPS)) + self.s
        return term if term > _EPS else _EPS

    def envelope(self, sigma3: float) -> float:
        """给定小主应力 σ3 (MPa)，返回破坏时大主应力 σ1 (MPa)（有效应力形式）"""
        term = self._compute_term(sigma3)
        return sigma3 + self.sigma_ci * math.pow(term, self.a)

    def dsigma1_dsigma3(self, sigma3: float) -> float:
        """Hoek-Brown 包络线斜率 dσ1/dσ3（Balmer, eq.10），即剪胀相关量"""
        term = self._compute_term(sigma3)
        return 1.0 + self.a * self.mb * math.pow(term, self.a - 1.0)


# ============================================================================
# 2. 岩体变形模量（多种经验方法）
# ============================================================================

@dataclass
class RockMassModulus:
    """岩体变形模量 Em（单位：MPa）。提供三种主流经验方法。"""

    sigma_ci: float
    gsi: float
    D: float = 0.0
    Ei_input: Optional[float] = None     # 完整岩石变形模量 Ei (MPa)，用于方法1
    MR: Optional[float] = None           # 模量比 Ei/Em，用于方法2

    Em_hoek2002: float = field(default=0.0, init=False)        # 方法4 Hoek(2002) [推荐]
    Em_hd2006: float = field(default=0.0, init=False)          # 方法1 Hoek&Diederichs(2006) Ei比
    Em_mr: float = field(default=0.0, init=False)              # 方法2 模量比法
    Em_serafim: float = field(default=0.0, init=False)         # 方法3 Serafim&Pereira(1983)
    Em_selected: float = field(default=0.0, init=False)        # 当前选用方法结果

    def compute(self, method: str = "hoek2002") -> "RockMassModulus":
        D, GSI, sigma_ci = self.D, self.gsi, self.sigma_ci

        # 方法4 (推荐) — Hoek(2002) eq.11a/b：含 σci 与 D
        if sigma_ci <= 100.0:
            self.Em_hoek2002 = 1000.0 * (1 - D / 2.0) * math.sqrt(sigma_ci / 100.0) * math.pow(10.0, (GSI - 10.0) / 40.0)
        else:
            self.Em_hoek2002 = 1000.0 * (1 - D / 2.0) * math.pow(10.0, (GSI - 10.0) / 40.0)

        # 方法1 — Hoek & Diederichs (2006) Ei 退化比
        base_factor = 0.02 + (1 - D / 2.0) / (1 + math.exp((60 + 15 * D - GSI) / 11.0))
        if self.Ei_input is not None:
            self.Em_hd2006 = self.Ei_input * base_factor
        else:
            self.Em_hd2006 = 1000.0 * (1 - D / 2.0) * math.sqrt(sigma_ci / 100.0) * base_factor

        # 方法2 — 模量比法：Em = Ei / MR（或默认经验 MR）
        mr = self.MR if self.MR is not None else (100.0 + 30.0 * (100.0 - GSI) / 100.0)
        ei = self.Ei_input if self.Ei_input is not None else (1000.0 * math.sqrt(sigma_ci / 100.0))
        self.Em_mr = ei / max(mr, _EPS)

        # 方法3 — Serafim & Pereira (1983)（经典，不含 D 与 σci）
        self.Em_serafim = 1000.0 * math.pow(10.0, (GSI - 10.0) / 40.0)

        self.Em_selected = self._select(method)
        return self

    def _select(self, method: str) -> float:
        return {
            "hoek2002": self.Em_hoek2002,
            "hd2006": self.Em_hd2006,
            "mr": self.Em_mr,
            "serafim": self.Em_serafim,
        }.get(method, self.Em_hoek2002)

# ============================================================================
# 3. 等效 Mohr-Coulomb 参数 (c', φ')
# ============================================================================

@dataclass
class MohrCoulombEquivalent:
    """
    等效 Mohr-Coulomb 参数（Hoek 2002, eq.12~13）。

    提供两种计算模式：
      * 单点评估   —— 给定 σ3，按 eq.12/13 在 σ3n=σ3/σci 处求值（包络线“切向”等效）
      * 面积平衡   —— 给定 σ3max（应力范围上限），在 [σt, σ3max] 上面积平衡拟合，
                     与 RocLab 完全一致（推荐用于数值模型/极限平衡输入）
    c' 内部以 MPa 存储便于计算，对外提供 kPa 视图。
    """

    sigma_ci: float
    mb: float
    s: float
    a: float
    sigma_3: float = 0.0                  # 单点评估用围压 (MPa)
    sigma_3max: Optional[float] = None    # 面积平衡用范围上限 σ3max (MPa)

    c_eq: float = field(default=0.0, init=False)        # 等效粘聚力 c' (kPa)
    phi_eq: float = field(default=0.0, init=False)      # 等效内摩擦角 φ' (deg)
    psi_eq: float = field(default=0.0, init=False)      # 等效剪胀角 ψ' (deg)
    envelope_slope: float = field(default=0.0, init=False)  # 包络线斜率 dσ1/dσ3
    sigma_3n: float = field(default=0.0, init=False)    # 归一化围压

    def compute(self) -> "MohrCoulombEquivalent":
        mb, s, a, sigma_ci = self.mb, self.s, self.a, self.sigma_ci
        # 面积平衡模式使用 σ3max，否则用单点 σ3
        sigma_3n = (self.sigma_3max if self.sigma_3max is not None else self.sigma_3) / max(sigma_ci, _EPS)
        self.sigma_3n = sigma_3n

        term = mb * sigma_3n + s
        if term <= 0:
            term = _EPS

        # 包络线斜率（eq.10）
        self.envelope_slope = 1.0 + a * mb * math.pow(term, a - 1.0)

        # 等效内摩擦角（eq.12）
        numerator = 6.0 * a * mb * math.pow(term, a - 1.0)
        denominator = 2.0 * (1.0 + a) * (2.0 + a) + numerator
        if denominator > 0:
            sin_phi = max(-1.0, min(1.0, numerator / denominator))
            self.phi_eq = math.degrees(math.asin(sin_phi))
        else:
            self.phi_eq = 30.0

        # [修正] 等效粘聚力（Hoek 2002 eq.13）。
        # 注意：分母根号内为 1 + num/((1+a)(2+a))，Hoek(2002) 原文 eq.13 无额外 /2。
        # 旧版曾误写为 1 + num/(2(1+a)(2+a))，导致 c' 偏大 ~√(1+num/(2D0))/√(1+num/D0) 倍。
        c_mpa = (sigma_ci * ((1.0 + 2.0 * a) * s + (1.0 - a) * mb * sigma_3n)
                 * math.pow(term, a - 1.0)) / (
                    (1.0 + a) * (2.0 + a) * math.sqrt(1.0 + numerator / ((1.0 + a) * (2.0 + a)))
                 )
        self.c_eq = max(0.0, c_mpa) * 1000.0  # 存储为 kPa，与绘图/界面约定一致

        # 剪胀角：常用近似 ψ' = φ' - 30°（上限取 0）
        self.psi_eq = max(0.0, self.phi_eq - 30.0)
        return self

    @property
    def c_eq_mpa(self) -> float:
        return self.c_eq / 1000.0


# ============================================================================
# 4. 应力范围上限 σ3max（面积平衡范围，Hoek 2002, eq.18/19）
# ============================================================================

def sigma_3max_from_application(
    sigma_cm: float, gamma: float, H: float, application: str = "tunnel"
) -> float:
    """
    由工程类型确定面积平衡范围上限 σ3max（Hoek 2002, eq.18 隧道 / eq.19 边坡）。

    eq.18 (隧道): σ3max/σcm = 0.47 (σcm/γH)^(-0.94)
    eq.19 (边坡): σ3max/σcm = 0.72 (σcm/γH)^(-0.91)

    σcm 为岩体强度（=σci·s^a），γH 为自重应力。水平应力高时以水平应力替代 γH。
    """
    gammaH = max(gamma * H, _EPS)
    ratio = sigma_cm / gammaH
    if application.lower().startswith("slope"):
        k = 0.72 * math.pow(ratio, -0.91)
    else:  # tunnel (default)
        k = 0.47 * math.pow(ratio, -0.94)
    return sigma_cm * k


# ============================================================================
# 5. 强度折减 (Strength Reduction Factor, SRF)
# ============================================================================

@dataclass
class StrengthReduction:
    """
    强度折减系数 F（>1 表示需要折减才能保持稳定）。

    两种折减策略（与原版“仅算参数”的本质区别：真正产出用于 SRM 的折减后参数）：

      method="hb"  : 直接折减 Hoek-Brown 参数。令 σci' = σci/F（mb,s,a 不变），
                     则 σcm' = σcm/F、σt' = σt/F，符合 FLAC 软化/折减 H-B 的做法。
      method="mc"  : 折减等效 Mohr-Coulomb 参数（Slide/Phase2/极限平衡输入）：
                     c'F = c'/F，tanφ'F = tanφ'/F。
    """

    @staticmethod
    def reduce_hb(hb: HBParameters, F: float) -> HBParameters:
        """返回折减后的 H-B 参数（σci 除以 F），并重新计算 mb/s/a 与派生强度"""
        red = HBParameters(
            sigma_ci=hb.sigma_ci / max(F, _EPS),
            gsi=hb.gsi, mi=hb.mi, D=hb.D, gamma=hb.gamma, height=hb.height,
        )
        return red.compute()

    @staticmethod
    def reduce_mc(mc: MohrCoulombEquivalent, F: float) -> MohrCoulombEquivalent:
        """返回折减后的等效 Mohr-Coulomb 参数 (c'→c'/F, tanφ'→tanφ'/F)"""
        c_new_mpa = mc.c_eq_mpa / max(F, _EPS)
        phi_new = math.degrees(math.atan(math.tan(math.radians(mc.phi_eq)) / max(F, _EPS)))
        out = MohrCoulombEquivalent(
            sigma_ci=mc.sigma_ci, mb=mc.mb, s=mc.s, a=mc.a,
            sigma_3=mc.sigma_3, sigma_3max=mc.sigma_3max,
        )
        out.c_eq = c_new_mpa * 1000.0
        out.phi_eq = phi_new
        out.psi_eq = max(0.0, phi_new - 30.0)
        out.sigma_3n = mc.sigma_3n
        out.envelope_slope = mc.envelope_slope
        return out

    @staticmethod
    def scan(
        hb: HBParameters, mc: MohrCoulombEquivalent,
        factors: Sequence[float] = (1.0, 1.2, 1.5, 2.0, 3.0),
        method: str = "mc",
    ) -> List[Tuple[float, float, float]]:
        """扫描一组折减系数，返回 [(F, c'_F(kPa), φ'_F(deg)), ...]"""
        out = []
        for F in factors:
            if method == "hb":
                hb_f = StrengthReduction.reduce_hb(hb, F)
                mc_f = MohrCoulombEquivalent(hb_f.sigma_ci, hb_f.mb, hb_f.s, hb_f.a,
                                             sigma_3=mc.sigma_3, sigma_3max=mc.sigma_3max).compute()
                out.append((F, mc_f.c_eq, mc_f.phi_eq))
            else:
                mc_f = StrengthReduction.reduce_mc(mc, F)
                out.append((F, mc_f.c_eq, mc_f.phi_eq))
        return out


# ============================================================================
# 6. 峰后应变软化模型（与 FLAC/Phase2 软化 H-B 对齐）
# ============================================================================

@dataclass
class StrainSofteningResult:
    """应变软化曲线上一点"""
    plastic_strain: float             # 塑性剪应变 γp
    gsi_current: float                # 当前 GSI
    sigma_cm: float                   # 当前岩体单轴抗压强度 (MPa)
    c_eq: float                       # 当前等效粘聚力 c' (kPa)
    phi_eq: float                     # 当前等效内摩擦角 (deg)
    strength_ratio: float             # 强度比（相对峰值）


@dataclass
class StrainSofteningModel:
    """
    峰后应变软化：随塑性剪应变 γp 累积，GSI 由峰值 GSI_peak 退化为残差 GSI_res，
    并重新计算 mb/s/a、岩体强度与等效 c'/φ'。

    退化采用平滑阶跃（smoothstep）以保证数值稳定，与 FLAC 中软化 H-B 的
    property-table 思路一致。GSI_res 建议取 GSI_peak 的 0.6~0.8 倍（或按工程经验）。
    """

    sigma_ci: float
    mi: float
    gsi_peak: float
    D: float = 0.0
    gamma: float = 0.027
    gsi_residual: Optional[float] = None
    gamma_peak: float = 0.0           # 软化起始塑性应变
    gamma_residual: float = 0.02      # 完全软化塑性应变

    def _gsi_at(self, gamma_p: float) -> float:
        gsi_res = self.gsi_residual if self.gsi_residual is not None else 0.7 * self.gsi_peak
        if gamma_p <= self.gamma_peak:
            return self.gsi_peak
        if gamma_p >= self.gamma_residual:
            return gsi_res
        x = (gamma_p - self.gamma_peak) / max(self.gamma_residual - self.gamma_peak, _EPS)
        smooth = x * x * (3.0 - 2.0 * x)   # smoothstep
        return self.gsi_peak + (gsi_res - self.gsi_peak) * smooth

    def compute_curve(self, n: int = 50, gamma_max: Optional[float] = None) -> List[StrainSofteningResult]:
        gamma_max = gamma_max if gamma_max is not None else self.gamma_residual * 1.5
        # 峰值参照（γp=0）
        hb_pk = HBParameters(self.sigma_ci, self.gsi_peak, self.mi, self.D, self.gamma).compute()
        sigma_cm_peak = hb_pk.sigma_cm
        results = []
        for i in range(n):
            gamma_p = gamma_max * i / max(n - 1, 1)
            gsi = self._gsi_at(gamma_p)
            hb = HBParameters(self.sigma_ci, gsi, self.mi, self.D, self.gamma).compute()
            mc = MohrCoulombEquivalent(self.sigma_ci, hb.mb, hb.s, hb.a, sigma_3=0.0).compute()
            results.append(StrainSofteningResult(
                plastic_strain=gamma_p,
                gsi_current=gsi,
                sigma_cm=hb.sigma_cm,
                c_eq=mc.c_eq,
                phi_eq=mc.phi_eq,
                strength_ratio=hb.sigma_cm / max(sigma_cm_peak, _EPS),
            ))
        return results


# ============================================================================
# 7. 整体折减分析
# ============================================================================

@dataclass
class ReductionAnalysis:
    """整体折减分析结果容器"""
    hb: HBParameters
    modulus: RockMassModulus
    mc: MohrCoulombEquivalent                  # 显示用等效 MC（面积平衡优先）
    mc_global: Optional[MohrCoulombEquivalent] = None   # 面积平衡等效 MC（RocLab 式）
    mc_local: Optional[MohrCoulombEquivalent] = None    # 指定 σ3 处局部等效 MC
    sigma_3max: float = 0.0
    strain_results: List[StrainSofteningResult] = field(default_factory=list)
    depth_profile: List[Tuple[float, float, float]] = field(default_factory=list)
    srf_scan: List[Tuple[float, float, float]] = field(default_factory=list)

    def summary(self) -> str:
        hb, mod, mc = self.hb, self.modulus, self.mc
        L = [
            "=" * 64,
            "Hoek-Brown 岩体强度折减分析结果（优化版 / Hoek 2002）",
            "=" * 64, "",
            "--- 输入参数 ---",
            f"  完整岩石单轴抗压强度 σci : {hb.sigma_ci:.2f} MPa",
            f"  地质强度指数 GSI          : {hb.gsi:.1f}",
            f"  岩体类型参数 mi           : {hb.mi:.2f}",
            f"  扰动系数 D                : {hb.D:.3f}",
            f"  岩体重度 γ                : {hb.gamma:.4f} MN/m³",
            f"  开挖埋深/坡高 H           : {hb.height:.1f} m",
            "",
            "--- Hoek-Brown 岩体常数 (修正后) ---",
            f"  mb                          : {hb.mb:.6f}",
            f"  s                           : {hb.s:.8f}",
            f"  a                           : {hb.a:.6f}",
            f"  岩体单轴抗压强度 σcm        : {hb.sigma_cm:.4f} MPa",
            f"  岩体抗拉强度 σt             : {hb.sigma_t:.5f} MPa",
            "",
            "--- 岩体变形模量 Em (MPa) ---",
            f"  Hoek(2002) [推荐]          : {mod.Em_hoek2002:.1f}",
            f"  Hoek&Diederichs(2006)      : {mod.Em_hd2006:.1f}",
            f"  模量比法                    : {mod.Em_mr:.1f}",
            f"  Serafim&Pereira(1983)      : {mod.Em_serafim:.1f}",
            f"  当前选用                    : {mod.Em_selected:.1f}",
            "",
            "--- 等效 Mohr-Coulomb 参数 ---",
            f"  计算模式                    : {'面积平衡(σ3max)' if mc.sigma_3max is not None else '单点(σ3=' + format(mc.sigma_3, '.2f') + ')'}"
            f"{'' if mc.sigma_3max is None else '  σ3max=' + format(self.sigma_3max, '.3f') + ' MPa'}",
            f"  等效粘聚力 c'               : {mc.c_eq:.2f} kPa ({mc.c_eq_mpa:.4f} MPa)",
            f"  等效内摩擦角 φ'             : {mc.phi_eq:.2f} deg",
            f"  等效剪胀角 ψ'               : {mc.psi_eq:.2f} deg",
            f"  包络线斜率 dσ1/dσ3          : {mc.envelope_slope:.4f}",
        ]
        if self.mc_local is not None and (self.mc_global is None or self.mc_local.sigma_3max is None):
            loc = self.mc_local
            L += [
                f"  局部等效(σ3={loc.sigma_3:.2f}MPa)   : c'={loc.c_eq:.2f} kPa, φ'={loc.phi_eq:.2f}°",
            ]
        if self.mc_global is not None and self.mc.sigma_3max is None:
            g = self.mc_global
            L += [
                "",
                "--- 面积平衡等效 MC (RocLab 式, 全局输入) ---",
                f"  c' (全局)                  : {g.c_eq:.2f} kPa ({g.c_eq_mpa:.4f} MPa)",
                f"  φ' (全局)                  : {g.phi_eq:.2f} deg",
            ]
        if self.srf_scan:
            L += ["", "--- 强度折减扫描 (F, c'_F kPa, φ'_F deg) ---"]
            for F, c, phi in self.srf_scan:
                L.append(f"  F={F:.2f}  ->  c'={c:.2f} kPa, φ'={phi:.2f}°")
        if self.strain_results:
            L += ["", "--- 峰后应变软化 (前5点) ---"]
            for r in self.strain_results[:5]:
                L.append(f"  γp={r.plastic_strain:.4f} | GSI={r.gsi_current:.1f} | "
                         f"σcm={r.sigma_cm:.3f} MPa | c'={r.c_eq:.1f} kPa | "
                         f"φ'={r.phi_eq:.1f}° | 强度比={r.strength_ratio:.3f}")
            L.append("  ...")
        if self.depth_profile:
            L += ["", "--- 深度剖面 (H, 自重应力 MPa, 等效c' kPa) ---"]
            for h, sig, coh in self.depth_profile:
                L.append(f"  H={h:7.1f} m | σ=selfweight={sig:.3f} | c'={coh:.1f}")
        L.append("=" * 64)
        return "\n".join(L)


def run_analysis(
    params: HBParameters,
    modulus_params: Optional[RockMassModulus] = None,
    sigma_3: float = 0.0,
    strain_range: Tuple[float, float, int] = (0.0, 0.5, 50),
    application: str = "tunnel",
    modulus_method: str = "hoek2002",
    use_area_balance: bool = True,
    srf_factors: Sequence[float] = (1.0, 1.2, 1.5, 2.0, 3.0),
    srf_method: str = "mc",
    softening: bool = True,
) -> ReductionAnalysis:
    """
    执行完整的 Hoek-Brown 岩体强度折减分析。

    参数
    ----
    params          : HBParameters（将自动 compute）
    modulus_params  : 变形模量参数（可选，缺省按 Hoek2002 估算）
    sigma_3         : 显示用等效 MC 的单点围压 (MPa)
    application     : 'tunnel' 或 'slope'，用于确定面积平衡范围 σ3max
    use_area_balance: True 时额外计算 RocLab 式全局等效 MC（基于 σ3max）
    srf_factors     : 强度折减系数扫描序列
    softening       : 是否计算峰后应变软化曲线
    """
    hb = params.compute()
    if modulus_params is None:
        modulus_params = RockMassModulus(sigma_ci=params.sigma_ci, gsi=params.gsi, D=params.D)
    modulus = modulus_params.compute(modulus_method)

    # 面积平衡范围 σ3max
    sigma_3max = sigma_3max_from_application(hb.sigma_cm, hb.gamma, hb.height, application)

    # 显示用等效 MC（面积平衡优先，否则单点）
    mc_local = MohrCoulombEquivalent(hb.sigma_ci, hb.mb, hb.s, hb.a, sigma_3=sigma_3).compute()
    if use_area_balance:
        mc = MohrCoulombEquivalent(hb.sigma_ci, hb.mb, hb.s, hb.a, sigma_3max=sigma_3max).compute()
        mc_global = mc
    else:
        mc = mc_local
        mc_global = None

    # 峰后应变软化
    strain_results: List[StrainSofteningResult] = []
    if softening:
        ssm = StrainSofteningModel(
            sigma_ci=hb.sigma_ci, mi=hb.mi, gsi_peak=hb.gsi, D=hb.D, gamma=hb.gamma
        )
        strain_results = ssm.compute_curve(n=max(2, strain_range[2]))

    # 深度剖面（各深度自重应力下的局部等效 MC）
    depth_profile: List[Tuple[float, float, float]] = []
    for h_frac in [0.0, 0.25, 0.5, 0.75, 1.0]:
        h = hb.height * h_frac
        sig = hb.gamma * h
        mc_h = MohrCoulombEquivalent(hb.sigma_ci, hb.mb, hb.s, hb.a, sigma_3=sig).compute()
        depth_profile.append((h, sig, mc_h.c_eq))

    # 强度折减扫描
    srf_scan = StrengthReduction.scan(hb, mc, factors=srf_factors, method=srf_method)

    return ReductionAnalysis(
        hb=hb, modulus=modulus, mc=mc, mc_global=mc_global, mc_local=mc_local,
        sigma_3max=sigma_3max, strain_results=strain_results,
        depth_profile=depth_profile, srf_scan=srf_scan,
    )


# ============================================================================
# 8. 便捷接口
# ============================================================================

def quick_estimate(
    sigma_ci: float, gsi: float, mi: float, D: float = 0.0,
    gamma: float = 0.027, height: float = 100.0, application: str = "tunnel",
) -> dict:
    """一行式快速估算，返回关键结果字典（便于脚本/批处理调用）"""
    hb = HBParameters(sigma_ci, gsi, mi, D, gamma, height).compute()
    mod = RockMassModulus(sigma_ci, gsi, D).compute("hoek2002")
    s3max = sigma_3max_from_application(hb.sigma_cm, gamma, height, application)
    mc = MohrCoulombEquivalent(hb.sigma_ci, hb.mb, hb.s, hb.a, sigma_3max=s3max).compute()
    return {
        "mb": hb.mb, "s": hb.s, "a": hb.a,
        "sigma_cm": hb.sigma_cm, "sigma_t": hb.sigma_t,
        "Em_MPa": mod.Em_hoek2002,
        "sigma_3max_MPa": s3max,
        "c_kPa": mc.c_eq, "phi_deg": mc.phi_eq, "psi_deg": mc.psi_eq,
    }
