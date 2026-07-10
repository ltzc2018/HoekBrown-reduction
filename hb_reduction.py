import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class HBParameters:
    """Hoek-Brown基本强度参数"""
    sigma_ci: float
    gsi: float
    mi: float
    D: float
    gamma: float
    height: float
    mb: float = 0.0
    s: float = 0.0
    a: float = 0.0
    sigma_c_prime: float = 0.0

    def compute(self) -> "HBParameters":
        D, GSI, mi, sigma_ci = self.D, self.gsi, self.mi, self.sigma_ci
        self.mb = D * math.exp((GSI - 100) / (28 - 14 * D))
        self.s = math.exp((GSI - 100) / (9 - 3 * D))
        self.a = 0.5 + (1.0 / 6.0) * (math.exp(-GSI / 15) - math.exp(-20.0 / 3))
        self.sigma_c_prime = sigma_ci * math.pow(self.s, self.a)
        return self


@dataclass
class RockMassModulus:
    """岩体弹性模量（多种计算方法）"""
    sigma_ci: float
    gsi: float
    D: float
    Ei_input: Optional[float] = None
    MR: Optional[float] = None
    Em_method1: float = 0.0
    Em_method2: float = 0.0
    Em_method3: float = 0.0
    Em_method4: float = 0.0

    def compute(self) -> "RockMassModulus":
        D, GSI, sigma_ci = self.D, self.gsi, self.sigma_ci
        base_factor = 0.02 + (1 - D / 2) / (1 + math.exp((60 + 15 * D - GSI) / 11))
        if self.Ei_input is not None:
            self.Em_method1 = self.Ei_input * base_factor
        else:
            self.Em_method1 = 1000 * (1 - D / 2) * math.sqrt(sigma_ci / 100) * base_factor
        if self.MR is not None:
            self.Em_method2 = self.MR * sigma_ci * base_factor
        else:
            self.Em_method2 = sigma_ci * base_factor
        self.Em_method3 = 100000 * (1 - D / 2) / (1 + math.exp((75 + 25 * D - GSI) / 11))
        self.Em_method4 = 1000 * (1 - D / 2) * math.sqrt(sigma_ci / 100) * math.pow(10, (GSI - 10) / 40)
        return self


@dataclass
class MohrCoulombEquivalent:
    """Mohr-Coulomb等效参数(c, phi)"""
    sigma_ci: float
    mb: float
    s: float
    a: float
    sigma_3: float = 0.0
    c_eq: float = 0.0
    phi_eq: float = 0.0
    psi_eq: float = 0.0
    E_eq: float = 0.0

    def compute(self) -> "MohrCoulombEquivalent":
        mb, s, a, sigma_ci = self.mb, self.s, self.a, self.sigma_ci
        sigma_3 = self.sigma_3
        term = mb * (sigma_3 / max(sigma_ci, 1e-10)) + s
        if term <= 0:
            term = 1e-10
        denom = 1 + (2 * a) / max(1e-10, (1 - a)) * (1 + (1 - a) * mb / (2 * a) * (sigma_3 / sigma_ci) * term ** (a - 1))
        self.c_eq = (sigma_ci * (term ** a)) / denom * 1000
        numerator = 6 * a * mb * term ** (a - 1)
        denominator = 2 * (1 + a) * (2 + a) + numerator
        if denominator > 0:
            sin_phi = max(-1, min(1, numerator / denominator))
            self.phi_eq = math.degrees(math.asin(sin_phi))
        else:
            self.phi_eq = 30.0
        self.psi_eq = max(0, self.phi_eq - 30)
        self.E_eq = sigma_ci * a * mb * term ** (a - 1) / (2 * (1 + a) * (2 + a))
        return self


@dataclass
class StrainSofteningResult:
    """应变软化模型结果"""
    strain: float
    reduced_strength: float
    strength_ratio: float
    stiffness_ratio: float

    @staticmethod
    def compute(strain_values, sigma_ci, mb, s, a):
        results = []
        for eps in strain_values:
            residual = 30.05 * math.pow(0.454 * eps / 30.05, 0.511) if eps > 0 else 0
            reduced = eps + residual
            term = mb * (reduced / max(sigma_ci, 1e-10)) + s
            if term <= 0:
                term = 1e-10
            current_strength = sigma_ci * math.pow(term, a)
            ratio = current_strength / sigma_ci if sigma_ci > 0 else 0
            stiffness = current_strength / (eps + 1e-10)
            results.append(StrainSofteningResult(eps, current_strength, ratio, stiffness))
        return results


@dataclass
class ReductionAnalysis:
    """整体折减分析结果"""
    hb: HBParameters
    modulus: RockMassModulus
    mc: MohrCoulombEquivalent
    strain_results: List[StrainSofteningResult] = field(default_factory=list)
    depth_profile: List[Tuple[float, float, float]] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            "=" * 60,
            "Hoek-Brown 岩体强度折减分析结果",
            "=" * 60, "",
            "--- 输入参数 ---",
            f"  完整岩石单轴抗压强度 sigma_ci : {self.hb.sigma_ci:.2f} MPa",
            f"  地质强度指数 GSI               : {self.hb.gsi:.1f}",
            f"  岩体类型参数 mi                : {self.hb.mi:.2f}",
            f"  扰动系数 D                     : {self.hb.D:.3f}",
            f"  岩体重度 gamma                 : {self.hb.gamma:.4f} MN/m3",
            f"  开挖高度 H                     : {self.hb.height:.1f} m",
            "",
            "--- Hoek-Brown 参数 ---",
            f"  mb                             : {self.hb.mb:.6f}",
            f"  s                              : {self.hb.s:.8f}",
            f"  a                              : {self.hb.a:.6f}",
            f"  sigma_c_prime (折减后强度)     : {self.hb.sigma_c_prime:.4f} MPa",
            "",
            "--- 岩体弹性模量 ---",
            f"  方法1 (基于Ei)                 : {self.modulus.Em_method1:.2f} MPa",
            f"  方法2 (基于sigma_ci)           : {self.modulus.Em_method2:.2f} MPa",
            f"  方法3 (经验公式)               : {self.modulus.Em_method3:.2f} MPa",
            f"  方法4 (Hoek经验)               : {self.modulus.Em_method4:.2f} MPa",
            "",
            "--- Mohr-Coulomb 等效参数 ---",
            f"  等效粘聚力 c                   : {self.mc.c_eq:.2f} kPa",
            f"  等效内摩擦角 phi               : {self.mc.phi_eq:.2f} deg",
            f"  等效剪胀角 psi                 : {self.mc.psi_eq:.2f} deg",
            f"  割线模量 Es                    : {self.mc.E_eq:.4f} MPa",
            "",
        ]
        if self.strain_results:
            lines.append("--- 应变软化曲线 (前5个) ---")
            for r in self.strain_results[:5]:
                lines.append(f"  eps={r.strain:.4f} | sigma={r.reduced_strength:.4f} MPa | "
                            f"比={r.strength_ratio:.4f} | 刚度={r.stiffness_ratio:.4f}")
            lines.append("  ...")
        lines.append("=" * 60)
        return "\n".join(lines)


def run_analysis(params: HBParameters,
                 modulus_params: Optional[RockMassModulus] = None,
                 sigma_3: float = 0.0,
                 strain_range: Tuple[float, float, int] = (0, 0.5, 50)) -> ReductionAnalysis:
    """执行完整的Hoek-Brown岩体强度折减分析"""
    hb = params.compute()
    if modulus_params is None:
        modulus_params = RockMassModulus(sigma_ci=params.sigma_ci, gsi=params.gsi, D=params.D)
    modulus = modulus_params.compute()
    mc = MohrCoulombEquivalent(sigma_ci=params.sigma_ci, mb=hb.mb, s=hb.s, a=hb.a, sigma_3=sigma_3).compute()
    start, end, n = strain_range
    strain_values = [start + i * (end - start) / (n - 1) for i in range(n)]
    strain_results = StrainSofteningResult.compute(strain_values, params.sigma_ci, hb.mb, hb.s, hb.a)
    depth_profile = []
    for h_frac in [0.0, 0.25, 0.5, 0.75, 1.0]:
        h = params.height * h_frac
        sigma_3_at_depth = params.gamma * h
        mc_h = MohrCoulombEquivalent(sigma_ci=params.sigma_ci, mb=hb.mb, s=hb.s, a=hb.a, sigma_3=sigma_3_at_depth).compute()
        depth_profile.append((h, sigma_3_at_depth, mc_h.c_eq))
    return ReductionAnalysis(hb=hb, modulus=modulus, mc=mc, strain_results=strain_results, depth_profile=depth_profile)
