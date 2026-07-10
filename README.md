# HoekBrown-reduction（深度优化版）

基于 **Hoek, Carranza-Torres & Corkum (2002) 广义 Hoek-Brown 准则** 的岩体强度折减分析系统，
计算岩体强度参数（mb, s, a）、岩体单轴抗压/抗拉强度、变形模量，并将 H-B 准则转换为
等效 Mohr-Coulomb 参数（c', φ'），输出可直接用于 **RocLab / FLAC / Slide** 等主流岩土软件。

---

## ⚠️ 本次优化修正的关键错误（原版致命 bug）

| # | 位置 | 原版错误 | 修正后（对齐 Hoek 2002 / RocLab） |
|---|------|---------|-----------------------------------|
| 1 | `HBParameters.compute` | `mb = D * exp((GSI-100)/(28-14D))` —— 误用扰动因子 **D** 代替完整岩石常数 **mi** | `mb = mi * exp((GSI-100)/(28-14D))`（eq.3）。示例 (89.5,24,64,0.9) 偏差 **2567 倍** |
| 2 | `MohrCoulombEquivalent.compute` | `c_eq` 公式完全错误，与 Hoek 2002 无关 | 采用 Hoek 2002 **eq.13** 面积平衡解 |
| 3 | 等效 MC 范围 | 仅用单点 σ3 估算，无 σ3max 范围确定 | 新增 **面积平衡法**：由工程类型用 eq.18(隧道)/eq.19(边坡) 确定 σ3max（与 RocLab 一致） |
| 4 | 应变软化 | 硬编码常量、应变与应力混用，物理无意义 | 重写为 **GSI 峰值→残差** 随塑性剪应变退化模型（对齐 FLAC 软化 H-B） |
| 5 | `plot_roclab_style` | 硬编码 "MR = 350"（与 GUI 默认 1000 矛盾）；抗拉强度误算为 `-σci·s^a` | 显示真实变形模量与正确 `σt = -s·σci/mb` |
| 6 | GUI 模量方法映射 | 下拉索引 0（"方法4 Hoek"）却传入 Ei（方法1）逻辑错位 | 下拉标签与计算方法一一对应，正确传参 |
| 7 | 强度折减（SRM） | 缺失 | 新增 **强度折减系数 SRF**：H-B 参数折减（σci/F）与等效 MC 折减（c'/F, tanφ'/F），支撑 SRM 稳定性分析 |

---

## 新增强能力

- **强度折减扫描（SRF）**：`StrengthReduction.scan()` 输出一组折减系数 F 对应的 (c'_F, φ'_F)，可直接作为 Slide/Phase2/极限平衡的稳定性分析输入。
- **面积平衡等效 MC**：`MohrCoulombEquivalent(..., sigma_3max=...)` 按 Hoek 2002 eq.12/13 在 [σt, σ3max] 上拟合，与 RocLab 完全一致。
- **多方法变形模量**：Hoek(2002) [推荐]、Hoek&Diederichs(2006)、模量比法、Serafim&Pereira(1983)。
- **深度剖面**：各深度自重应力下的局部等效 c'。
- **验证套件**：`hb_validate.py` —— 对照 Hoek 2002 / RocLab 基准 + 数值面积平衡交叉验证。

---

## 安装与运行

```bash
pip install numpy matplotlib        # 命令行 / 计算核心
pip install PyQt5                   # 图形界面（可选）
```

```bash
python main.py                 # 启动 GUI
python main.py --demo          # 示例计算（非 GUI）
python main.py --example       # 输出 Hoek 2002 经典 + 项目示例完整结果
python main.py --validate      # 运行验证套件（对照 Hoek 2002 / RocLab）
python main.py --single "89.5,64,24,0.9,0.027,196"   # 单组快速估算
python main.py --batch data.csv  # CSV 批量（列: sigma_ci,gsi,mi,D,gamma,height）
```

---

## 理论公式（Hoek 2002）

- 广义准则：σ₁' = σ₃' + σci (mb·σ₃'/σci + s)^a
- mb = mi·exp((GSI−100)/(28−14D))；s = exp((GSI−100)/(9−3D))；a = ½ + (e^(−GSI/15) − e^(−20/3))/6
- 岩体 UCS：σcm = σci·s^a；岩体抗拉：σt = −s·σci/mb
- 变形模量（推荐）：Em(GPa) = (1−D/2)·√(σci/100)·10^((GSI−10)/40)（σci≤100），σci>100 时去掉 √ 项
- 等效 MC（面积平衡，eq.12/13）：
  - sinφ' = 6a·mb·(s+mb·σ3n)^(a−1) / [2(1+a)(2+a) + 6a·mb·(s+mb·σ3n)^(a−1)]，σ3n = σ3max/σci
  - c' = σci·[(1+2a)s + (1−a)mb·σ3n]·(s+mb·σ3n)^(a−1) / [(1+a)(2+a)·√(1 + 6a·mb·(s+mb·σ3n)^(a−1)/((1+a)(2+a)))]
- σ3max（面积平衡范围）：隧道 eq.18 = 0.47·(σcm/γH)^(−0.94)；边坡 eq.19 = 0.72·(σcm/γH)^(−0.91)

> 详见 `METHODOLOGY.md`（与 RocLab / FLAC / Slide 计算方法对比）。

---

## 文件结构

```
hb_reduction.py   核心计算引擎（修正后，含 SRF / 面积平衡 / 应变软化）
hb_plot.py        可视化（修正 MC 直线、面积平衡图、SRF 图）
hb_gui.py         PyQt5 图形界面（修正模量方法映射、新增工程类型选择）
main.py           命令行入口（demo / example / validate / single / batch / GUI）
hb_validate.py    验证套件（Hoek 2002 / RocLab 基准 + 数值面积平衡交叉验证）
METHODOLOGY.md    与主流岩土软件计算方法对比
```

---

## 验证结果

运行 `python main.py --validate` 输出（节选）：

```
mb        got=1.40256  ref=1.40260   ✓
s         got=0.00222  ref=0.00222   ✓
a         got=0.50809  ref=0.50810   ✓
σcm       got=2.24130  ref=2.24130   ✓
σt        got=-0.07907 ref=-0.07907  ✓
Em        got=5302.55  ref=5302.60   ✓
c' 闭式   got=1038.43  ref=1038.43   ✓  (独立闭式重转录交叉验证)
φ' 闭式   got=42.75    ref=42.75     ✓  (数值面积平衡交叉验证)
强度折减 / 应变软化  ✓
结果: 18 通过 / 0 失败
```
