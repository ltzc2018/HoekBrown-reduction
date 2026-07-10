# 与相关岩土软件计算方法的对比

本项目优化的目标是让计算结果与业界主流软件 **RocLab (RocScience)、FLAC/FLAC3D、Phase2/RS2、Slide/Slide2** 的处理方式对齐。
下面按"计算环节 → 本项目实现 → 软件对应做法"逐一说明。

---

## 1. Hoek-Brown 岩体常数 mb, s, a

| 环节 | 公式 | 软件做法 |
|------|------|---------|
| mb | mi·exp((GSI−100)/(28−14D)) | **RocLab / RocScience** 完全采用此式（GSI + D 折减 mi） |
| s | exp((GSI−100)/(9−3D)) | 同 RocLab |
| a | ½ + (e^(−GSI/15) − e^(−20/3))/6 | 同 RocLab（2002 版，全 GSI 范围连续） |

> ⚠️ **原版 bug**：误写为 `mb = D·exp(...)`，把扰动因子 D 当成了完整岩石常数 mi，导致 mb 偏差最高达 **2567 倍**。本项目已修正，并经开源实现 `rocstrenv/HoekBrown.py` 交叉确认（其 mb/s/a 与本项目逐式一致）。

---

## 2. 岩体强度与变形参数

| 参数 | 公式 | 软件对应 |
|------|------|---------|
| 岩体 UCS σcm | σci·s^a | RocLab "UCS" 字段 |
| 岩体抗拉 σt | −s·σci/mb | RocLab "Tensile strength" 字段 |
| 变形模量 Em | (1−D/2)·√(σci/100)·10^((GSI−10)/40) [GPa] | **Hoek (2002)** 推荐式；RocLab 亦提供此式 |

本项目额外提供 Hoek&Diederichs(2006)（Ei 退化比）、模量比法、Serafim&Pereira(1983) 三种方法，便于与不同工程经验对标。

---

## 3. 等效 Mohr-Coulomb 转换（核心差异点）

多数数值软件（FLAC、Phase2、Slide）基于 Mohr-Coulomb 准则，因此必须把弯曲的 H-B 包络线"拉直"成 c'、φ'。

**本项目采用 Hoek 2002 eq.12/13 的面积平衡解**（与 RocLab 完全一致）：

- 先由工程类型确定应力范围上限 **σ3max**：
  - 隧道（地下开挖）eq.18：σ3max/σcm = 0.47·(σcm/γH)^(−0.94)
  - 边坡 eq.19：σ3max/σcm = 0.72·(σcm/γH)^(−0.91)
- 在 [σt, σ3max] 上用 eq.12/13 拟合直线，得到单一 (c', φ')。

**与各类软件的对应关系：**

| 软件 | 做法 | 本项目对齐方式 |
|------|------|---------------|
| **RocLab** | 用户给定/自动 σ3max，输出 eq.12/13 的 (c', φ') | `MohrCoulombEquivalent(sigma_3max=...)` 直接复现 |
| **FLAC / FLAC3D** | 可直接用 H-B 本构（FISH 定义 mb/s/a），或用等效 c'/φ' | 本项目同时输出二者；SRF 可直接作用于 H-B 或 MC |
| **Slide / Slide2** | 极限平衡，需要 c'、φ' 输入 | 输出 (c'_kPa, φ'_deg) 直接填表 |
| **Phase2 / RS2** | 强度折减法（SRM），需 c'、φ' 与折减系数 | 见第 4 节 SRF |

> ⚠️ **原版 bug**：`c_eq` 公式与 Hoek 2002 无关，结果完全错误。本项目重写为 eq.13，并经**独立闭式重转录 + 数值面积平衡（Balmer 转换 + 最小二乘）双交叉验证**，φ' 与面积平衡斜率误差 < 0.01°，c' 与独立重转录完全一致。

> 注：H-B 包络线在 σn-τ 空间是弯曲的，直线拟合在范围内最大偏差约 18%（线性化弯曲包络的正常水平），这与 RocLab 的等效 MC 行为一致。

---

## 4. 强度折减（Strength Reduction, SRF / SRM）

"强度折减"（本项目名称"HB折减"的核心）对应数值软件中的 **强度折减法（Strength Reduction Method, SRM）**，用于求安全系数 FOS。

本项目 `StrengthReduction` 提供两种折减策略（与软件实践一致）：

### 4.1 等效 MC 折减（Slide / Phase2 / 极限平衡输入）
- c'_F = c' / F
- tanφ'_F = tanφ' / F
- 最小使体系失稳的 F = FOS。本项目 `StrengthReduction.scan()` 输出 F = 1.0, 1.2, 1.5, 2.0, 3.0 对应的 (c'_F, φ'_F)，可直接批量填入 Slide/Phase2 试算。

### 4.2 H-B 参数折减（FLAC 直接 H-B 模型）
- σci_F = σci / F（mb, s, a 不变）→ 自动使 σcm_F = σcm / F、σt_F = σt / F
- 与 FLAC 中对 H-B 模型施加强度折减因子的做法一致。

---

## 5. 峰后应变软化（FLAC / Phase2 软化 H-B）

真实岩体峰后强度会随变形下降。本项目 `StrainSofteningModel` 实现：

- 随**塑性剪应变 γp** 累积，GSI 由峰值 **GSI_peak** 经平滑阶跃退化为残差 **GSI_res**（默认 0.7·GSI_peak，可设）；
- 每步重算 mb、s、a 与等效 c'、φ'，得到后峰强度跌落曲线。
- 该思路与 FLAC 中"H-B 软化表（property-table，按塑性应变插值 GSI/mb/s/a）"一致，可作为数值模型参数标定的依据。

> ⚠️ **原版 bug**：用硬编码常量 `30.05·(0.454·ε/30.05)^0.511` 并将应变（无量纲）与应力（MPa）直接相加，物理无意义。已重写为上述退化模型。

---

## 6. 验证基准（本项目如何确认"算得对"）

1. **mb/s/a/σcm/σt/Em** —— 对照 Hoek 2002 经典算例 (σci=50, mi=10, GSI=45, D=0) 与开源 `rocstrenv`，误差 < 1e-4。
2. **φ'（eq.12）** —— 与数值面积平衡（Balmer 转换 + 最小二乘）斜率交叉验证，误差 < 0.01°。
3. **c'（eq.13）** —— 与独立重转录的闭式公式逐字符比对，完全一致；φ' 斜率与面积平衡一致。
4. **SRF** —— 验证 σcm_F = σcm/F、tanφ'_F = tanφ'/F 严格成立。
5. **应变软化** —— 验证峰后强度单调递减。

运行 `python main.py --validate` 可得 18/18 通过。
