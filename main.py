"""
Hoek-Brown 岩体强度折减分析系统 — 命令行入口
============================================

用法:
    python main.py                 # 启动 GUI 界面
    python main.py --demo         # 运行示例计算（非 GUI）
    python main.py --validate     # 运行验证套件（对照 Hoek 2002 / RocLab）
    python main.py --example      # 输出 Hoek 2002 经典与项目示例完整结果
    python main.py --batch csv.txt # 从 CSV 批量计算（列: sigma_ci,gsi,mi,D,gamma,height）
    python main.py --single "89.5,64,24,0.9,0.027,196"  # 单组参数快速估算

依赖: numpy, matplotlib (GUI 还需 PyQt5)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---- 单组参数快速估算 ----
def _parse_single(arg: str):
    parts = [float(x) for x in arg.split(",")]
    while len(parts) < 6:
        parts.append([89.5, 64.0, 24.0, 0.9, 0.027, 196.0][len(parts)])
    return parts[:6]


def run_single(arg: str):
    sci, gsi, mi, D, gamma, H = _parse_single(arg)
    from hb_reduction import quick_estimate
    r = quick_estimate(sci, gsi, mi, D, gamma, H)
    print("=" * 60)
    print(f"  单组快速估算: σci={sci}, GSI={gsi}, mi={mi}, D={D}")
    print("=" * 60)
    for k, v in r.items():
        print(f"  {k:16s}: {v:.5f}")
    return r


def run_demo():
    """示例计算（非 GUI 模式），复现项目自带数据组"""
    from hb_reduction import HBParameters, RockMassModulus, run_analysis
    print("=" * 70)
    print("  Hoek-Brown 岩体强度折减分析系统（优化版）— 示例计算")
    print("=" * 70)
    params = HBParameters(sigma_ci=89.5, gsi=64, mi=24, D=0.9, gamma=0.027, height=196)
    modulus_params = RockMassModulus(sigma_ci=89.5, gsi=64, D=0.9, Ei_input=5426, MR=1000)
    result = run_analysis(params, modulus_params, sigma_3=0.0, application="tunnel")
    print(result.summary())
    print("\n提示: 运行 'python main.py' 启动图形界面；'--validate' 运行验证。")


def run_example():
    """输出 Hoek 2002 经典 + 项目示例的完整结果，便于核对"""
    from hb_reduction import HBParameters, RockMassModulus, MohrCoulombEquivalent
    from hb_reduction import sigma_3max_from_application

    cases = [
        ("Hoek 2002 经典", 50.0, 45.0, 10.0, 0.0, 0.027, 196.0),
        ("项目自带示例", 89.5, 64.0, 24.0, 0.9, 0.027, 196.0),
    ]
    for name, sci, gsi, mi, D, gamma, H in cases:
        print("=" * 64)
        print(f"  {name}: σci={sci}, GSI={gsi}, mi={mi}, D={D}")
        print("=" * 64)
        hb = HBParameters(sci, gsi, mi, D, gamma, H).compute()
        mod = RockMassModulus(sci, gsi, D).compute("hoek2002")
        s3max = sigma_3max_from_application(hb.sigma_cm, gamma, H, "tunnel")
        mc = MohrCoulombEquivalent(sci, hb.mb, hb.s, hb.a, sigma_3max=s3max).compute()
        print(f"  mb = {hb.mb:.6f}")
        print(f"  s  = {hb.s:.8f}")
        print(f"  a  = {hb.a:.6f}")
        print(f"  岩体 UCS σcm      = {hb.sigma_cm:.4f} MPa")
        print(f"  岩体抗拉 σt       = {hb.sigma_t:.5f} MPa")
        print(f"  变形模量 Em(2002) = {mod.Em_hoek2002:.1f} MPa")
        print(f"  σ3max (隧道)      = {s3max:.4f} MPa")
        print(f"  等效 c'           = {mc.c_eq:.2f} kPa ({mc.c_eq_mpa:.4f} MPa)")
        print(f"  等效 φ'           = {mc.phi_eq:.2f} deg")
        print()


def run_batch(csv_path: str):
    """从 CSV 批量计算。首行可含表头；列顺序: sigma_ci,gsi,mi,D,gamma,height"""
    import csv
    from hb_reduction import HBParameters, RockMassModulus, run_analysis
    print(f"批量计算: {csv_path}")
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    header = rows[0]
    data = rows[1:] if header and not _is_number(header[0]) else rows
    print(f"{'σci':>8} {'GSI':>5} {'mi':>5} {'D':>5} {'c(kPa)':>10} {'φ(°)':>8} {'Em(MPa)':>10}")
    print("-" * 55)
    for row in data:
        if not row:
            continue
        vals = [float(x) for x in row[:6]]
        sci, gsi, mi, D = vals[0], vals[1], vals[2], vals[3]
        gamma = vals[4] if len(vals) > 4 else 0.027
        H = vals[5] if len(vals) > 5 else 100.0
        hb = HBParameters(sci, gsi, mi, D, gamma, H).compute()
        mod = RockMassModulus(sci, gsi, D).compute("hoek2002")
        res = run_analysis(hb, mod, application="tunnel")
        print(f"{sci:8.1f} {gsi:5.0f} {mi:5.1f} {D:5.2f} {res.mc.c_eq:10.1f} {res.mc.phi_eq:8.1f} {mod.Em_hoek2002:10.0f}")


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


def run_gui():
    try:
        from hb_gui import HBReductionApp
        from PyQt5.QtWidgets import QApplication
        from hb_gui import apply_styles
    except ImportError as e:
        print(f"[错误] 无法加载 GUI（缺少 PyQt5）: {e}")
        print("        可改用: python main.py --demo / --validate / --example / --batch")
        sys.exit(1)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_styles(app)
    window = HBReductionApp()
    window.show()
    print("  [提示] GUI 窗口已打开。命令行模式: python main.py --demo")
    sys.exit(app.exec_())


def main():
    args = sys.argv[1:]
    if "--validate" in args:
        from hb_validate import main as validate_main
        sys.exit(validate_main())
    if "--demo" in args:
        run_demo()
        return
    if "--example" in args:
        run_example()
        return
    if "--single" in args:
        i = args.index("--single")
        if i + 1 < len(args):
            run_single(args[i + 1])
        else:
            print("用法: --single \"89.5,64,24,0.9,0.027,196\"")
        return
    if "--batch" in args:
        i = args.index("--batch")
        if i + 1 < len(args):
            run_batch(args[i + 1])
        else:
            print("用法: --batch data.csv")
        return
    # 默认启动 GUI
    run_gui()


if __name__ == "__main__":
    main()
