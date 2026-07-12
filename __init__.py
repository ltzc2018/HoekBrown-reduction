"""
Hoek-Brown 岩体强度折减分析系统

基于 Hoek, Carranza-Torres & Corkum (2002) 广义 Hoek-Brown 准则，
提供岩体强度参数计算、等效 Mohr-Coulomb 拟合、强度折减与应变软化分析。

核心模块:
    hb_reduction — Hoek-Brown 强度折减核心引擎
    hb_gui       — PyQt5 图形界面
    hb_plot      — Matplotlib 可视化
    hb_validate  — 与 xlsx 论文结果对标验证
    main         — 命令行入口
"""

from .hb_reduction import (
    HBParameters, RockMassModulus, MohrCoulombEquivalent,
    StrainSofteningModel, StrengthReduction, ReductionAnalysis,
    sigma_3max_from_application, run_analysis, quick_estimate,
)

__version__ = "1.0.0"
__all__ = [
    "HBParameters", "RockMassModulus", "MohrCoulombEquivalent",
    "StrainSofteningModel", "StrengthReduction", "ReductionAnalysis",
    "sigma_3max_from_application", "run_analysis", "quick_estimate",
]
