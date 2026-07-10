"""
Hoek-Brown岩体强度折减分析系统 - 主程序入口
============================================
用法:
    python main.py          # 启动GUI界面
    python main.py --test   # 运行示例计算
"""
import sys
import os

# 确保模块路径正确
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_demo():
    """运行示例计算（非GUI模式）"""
    from hb_reduction import HBParameters, RockMassModulus, run_analysis

    print("=" * 70)
    print("  Hoek-Brown 岩体强度折减分析系统 - 示例计算")
    print("=" * 70)
    print()

    # 使用Excel中的第一组数据作为示例
    params = HBParameters(sigma_ci=89.5, gsi=64, mi=24, D=0.9, gamma=0.027, height=196)
    modulus_params = RockMassModulus(sigma_ci=89.5, gsi=64, D=0.9, Ei_input=5426, MR=1000)

    result = run_analysis(params, modulus_params, sigma_3=0.0, strain_range=(0, 0.5, 50))

    print(result.summary())
    print()
    print("=" * 70)
    print("  验证：与Excel文件第一行数据对比")
    print("=" * 70)
    print()
    print("  Excel A2 (sigma_ci) = 89.5 MPa      -> Python:", params.sigma_ci)
    print("  Excel C2 (GSI) = 64                 -> Python:", params.gsi)
    print("  Excel D2 (mi) = 24                  -> Python:", params.mi)
    print("  Excel E2 (D) = 0.9                  -> Python:", params.D)
    print()
    print("  所有模块已就绪，运行 'python main.py' 启动图形界面。")


def run_gui():
    """启动图形界面"""
    from hb_gui import HBReductionApp
    from PyQt5.QtWidgets import QApplication
    from hb_gui import apply_styles

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_styles(app)

    window = HBReductionApp()
    window.show()

    print("  [提示] GUI窗口已打开。如需命令行模式，请运行: python main.py --test")
    sys.exit(app.exec_())


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_demo()
    else:
        run_gui()
