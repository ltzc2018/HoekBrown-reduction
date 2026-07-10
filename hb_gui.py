"""
Hoek-Brown岩体强度折减分析系统 - GUI界面
基于PyQt5构建的交互式桌面应用程序
"""
import sys
import math
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QGroupBox, QFormLayout,
    QTabWidget, QFileDialog, QMessageBox, QSpinBox, QDoubleSpinBox,
    QComboBox, QTextEdit, QSplitter, QFrame, QGridLayout, QSlider
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon, QColor, QPainter
import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import numpy as np

from hb_reduction import (
    HBParameters, RockMassModulus, MohrCoulombEquivalent,
    StrainSofteningResult, ReductionAnalysis, run_analysis
)
from hb_plot import plot_mohr_circles, plot_strain_softening, plot_depth_profile, plot_modulus_comparison, plot_roclab_style


# ============================================================================
# 自定义样式
# ============================================================================

DARK_BLUE = "#1a237e"
ACCENT_BLUE = "#2962ff"
LIGHT_BG = "#f5f5f5"
CARD_BG = "#ffffff"
TEXT_DARK = "#212121"
TEXT_LIGHT = "#ffffff"
SUCCESS_GREEN = "#4caf50"
WARNING_ORANGE = "#ff9800"


def apply_styles(app):
    """应用全局样式"""
    app.setStyleSheet(f"""
        QMainWindow {{
            background-color: {LIGHT_BG};
        }}
        QGroupBox {{
            font-weight: bold;
            font-size: 13px;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 12px;
            background-color: {CARD_BG};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: {DARK_BLUE};
        }}
        QPushButton {{
            background-color: {ACCENT_BLUE};
            color: {TEXT_LIGHT};
            border: none;
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 13px;
            font-weight: bold;
            min-width: 80px;
        }}
        QPushButton:hover {{
            background-color: #1565c0;
        }}
        QPushButton:pressed {{
            background-color: #0d47a1;
        }}
        QPushButton#compute_btn {{
            background-color: {SUCCESS_GREEN};
            font-size: 15px;
            padding: 12px 30px;
        }}
        QPushButton#compute_btn:hover {{
            background-color: #388e3c;
        }}
        QPushButton#reset_btn {{
            background-color: {WARNING_ORANGE};
        }}
        QPushButton#reset_btn:hover {{
            background-color: #f57c00;
        }}
        QDoubleSpinBox, QSpinBox, QLineEdit {{
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
            background-color: {CARD_BG};
        }}
        QDoubleSpinBox:focus, QSpinBox:focus, QLineEdit:focus {{
            border: 2px solid {ACCENT_BLUE};
        }}
        QTabWidget::pane {{
            border: 1px solid #ddd;
            border-radius: 8px;
            background-color: {CARD_BG};
        }}
        QTabBar::tab {{
            background-color: #e0e0e0;
            padding: 8px 16px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            font-size: 12px;
        }}
        QTabBar::tab:selected {{
            background-color: {CARD_BG};
            font-weight: bold;
            color: {DARK_BLUE};
        }}
        QTextEdit {{
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 8px;
            font-family: Consolas, monospace;
            font-size: 11px;
            background-color: #fafafa;
        }}
        QLabel {{
            font-size: 12px;
            color: {TEXT_DARK};
        }}
        QSlider::groove:horizontal {{
            border: 1px solid #999;
            height: 6px;
            background: #ccc;
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {ACCENT_BLUE};
            border: 1px solid #555;
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
    """)


# ============================================================================
# 图表画布组件
# ============================================================================

class MatplotlibCanvas(FigureCanvas):
    """Matplotlib图表在Qt中的画布"""
    def __init__(self, parent=None, width=8, height=5, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.figure)
        self.setParent(parent)
        self.figure.patch.set_facecolor(CARD_BG)
        from PyQt5.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()


# ============================================================================
# 主窗口
# ============================================================================

class HBReductionApp(QMainWindow):
    """Hoek-Brown岩体强度折减分析主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hoek-Brown 岩体强度折减分析系统 v1.0")
        self.setMinimumSize(1200, 800)
        self.analysis_result = None
        self._build_ui()

    def _build_ui(self):
        """构建用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel("  Hoek-Brown 岩体强度折减分析系统  ")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title_label.setStyleSheet(f"color: {DARK_BLUE}; padding: 8px; background-color: {CARD_BG}; border-radius: 8px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        # 分割器
        splitter = QSplitter(Qt.Horizontal)

        # --- 左侧：输入面板 ---
        left_panel = self._create_input_panel()
        splitter.addWidget(left_panel)

        # --- 右侧：结果面板 ---
        right_panel = self._create_result_panel()
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter, 1)

    def _create_input_panel(self) -> QWidget:
        """创建左侧输入面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        # 基本参数组
        basic_group = QGroupBox("基本强度参数")
        basic_layout = QFormLayout()

        self.spin_sigma_ci = QDoubleSpinBox()
        self.spin_sigma_ci.setRange(1, 500)
        self.spin_sigma_ci.setValue(89.5)
        self.spin_sigma_ci.setSuffix(" MPa")
        self.spin_sigma_ci.setDecimals(2)

        self.spin_gsi = QSpinBox()
        self.spin_gsi.setRange(0, 100)
        self.spin_gsi.setValue(64)

        self.spin_mi = QDoubleSpinBox()
        self.spin_mi.setRange(1, 25)
        self.spin_mi.setValue(24)
        self.spin_mi.setDecimals(2)

        self.spin_D = QDoubleSpinBox()
        self.spin_D.setRange(0, 1)
        self.spin_D.setValue(0.9)
        self.spin_D.setDecimals(3)
        self.spin_D.setSingleStep(0.01)

        self.spin_gamma = QDoubleSpinBox()
        self.spin_gamma.setRange(0.01, 0.1)
        self.spin_gamma.setValue(0.027)
        self.spin_gamma.setDecimals(4)
        self.spin_gamma.setSuffix(" MN/m\u00b3")

        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(1, 1000)
        self.spin_height.setValue(196)
        self.spin_height.setSuffix(" m")

        basic_layout.addRow("\u5355\u8f74\u6297\u538b\u5f3a\u5ea6 (\u03c3ci):", self.spin_sigma_ci)
        basic_layout.addRow("\u5730\u8d28\u5f3a\u5ea6\u6307\u6570 (GSI):", self.spin_gsi)
        basic_layout.addRow("\u5ca9\u4f53\u7c7b\u578b\u53c2\u6570 (mi):", self.spin_mi)
        basic_layout.addRow("\u6270\u52a8\u7cfb\u6570 (D):", self.spin_D)
        basic_layout.addRow("\u5ca9\u4f53\u91cd\u5ea6 (\u03b3):", self.spin_gamma)
        basic_layout.addRow("\u5f00\u6316\u9ad8\u5ea6 (H):", self.spin_height)

        basic_group.setLayout(basic_layout)

        # 模量参数组
        modulus_group = QGroupBox("弹性模量计算选项")
        modulus_layout = QFormLayout()

        self.combo_modulus_method = QComboBox()
        self.combo_modulus_method.addItems(["Hoek(2002) [推荐]", "Hoek&Diederichs(2006)", "模量比法", "Serafim&Pereira(1983)"])

        self.spin_Ei = QDoubleSpinBox()
        self.spin_Ei.setRange(0, 1000000)
        self.spin_Ei.setValue(5426)
        self.spin_Ei.setSuffix(" MPa")
        self.spin_Ei.setDecimals(1)

        self.spin_MR = QDoubleSpinBox()
        self.spin_MR.setRange(0, 10000)
        self.spin_MR.setValue(1000)
        self.spin_MR.setDecimals(1)

        modulus_layout.addRow("\u8ba1\u7b97\u65b9\u6cd5:", self.combo_modulus_method)
        modulus_layout.addRow("Ei \u503c:", self.spin_Ei)
        modulus_layout.addRow("MR \u503c:", self.spin_MR)

        modulus_group.setLayout(modulus_layout)

        # 分析选项组
        option_group = QGroupBox("分析选项")
        option_layout = QFormLayout()

        self.combo_application = QComboBox()
        self.combo_application.addItems(["隧道 (Tunnel)", "边坡 (Slope)"])
        self.combo_application.setCurrentIndex(0)
        self.spin_sigma3 = QDoubleSpinBox()
        self.spin_sigma3.setRange(0, 100)
        self.spin_sigma3.setValue(0)
        self.spin_sigma3.setSuffix(" MPa")
        self.spin_sigma3.setDecimals(2)

        self.spin_n_points = QSpinBox()
        self.spin_n_points.setRange(10, 200)
        self.spin_n_points.setValue(50)

        option_layout.addRow("\u6700\u5c0f\u4e3b\u5e94\u529b (\u03c33):", self.spin_sigma3)
        option_layout.addRow("工程类型:", self.combo_application)
        option_layout.addRow("\u5e94\u53d8\u70b9\u6570:", self.spin_n_points)

        option_group.setLayout(option_layout)

        # 按钮组
        btn_layout = QHBoxLayout()
        self.btn_compute = QPushButton("\u27a0  执行分析  \u27a0")
        self.btn_compute.setObjectName("compute_btn")
        self.btn_compute.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        self.btn_reset = QPushButton("\u21ba 重置")
        self.btn_reset.setObjectName("reset_btn")
        self.btn_export = QPushButton("\ud83d\udcbe 导出")
        self.btn_plot = QPushButton("\ud83d\udcca 图表")

        btn_layout.addWidget(self.btn_compute)
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_plot)
        btn_layout.addStretch()

        # 连接信号
        self.btn_compute.clicked.connect(self.run_computation)
        self.btn_reset.clicked.connect(self.reset_inputs)
        self.btn_export.clicked.connect(self.export_results)
        self.btn_plot.clicked.connect(self.show_plots)

        layout.addWidget(basic_group)
        layout.addWidget(modulus_group)
        layout.addWidget(option_group)
        layout.addLayout(btn_layout)
        layout.addStretch()

        return panel

    def _create_result_panel(self) -> QWidget:
        """创建右侧结果面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # 标签页
        self.tabs = QTabWidget()

        # 文本结果
        self.text_results = QTextEdit()
        self.text_results.setReadOnly(True)
        self.tabs.addTab(self.text_results, "\ud83d\udcdd 计算结果")

        # 图表页（包含RocLab图版 + 详细图表）
        self.plot_tab = QWidget()
        plot_layout = QVBoxLayout(self.plot_tab)
        plot_layout.setContentsMargins(5, 5, 5, 5)

        # RocLab主图区域
        self.roclab_area = QWidget()
        roclab_layout = QVBoxLayout(self.roclab_area)
        roclab_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.addWidget(self.roclab_area, 3)

        # 分隔标题
        sep_label = QLabel("详细分析图表")
        sep_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        sep_label.setStyleSheet(f"color: {DARK_BLUE}; padding: 8px 4px 4px 4px;")
        plot_layout.addWidget(sep_label)

        # 详细图表区域
        self.plot_area = QWidget()
        self.plot_area.setMinimumHeight(350)
        plot_layout_inner = QVBoxLayout(self.plot_area)
        plot_layout_inner.setContentsMargins(0, 0, 0, 0)
        plot_layout.addWidget(self.plot_area, 2)

        # 添加伸缩空间
        plot_layout.addStretch()

        self.tabs.addTab(self.plot_tab, "图表分析")

        layout.addWidget(self.tabs)

        return panel

    # ------------------------------------------------------------------
    # 事件处理
    # ------------------------------------------------------------------

    def run_computation(self):
        """执行计算"""
        try:
            params = HBParameters(
                sigma_ci=self.spin_sigma_ci.value(),
                gsi=self.spin_gsi.value(),
                mi=self.spin_mi.value(),
                D=self.spin_D.value(),
                gamma=self.spin_gamma.value(),
                height=self.spin_height.value(),
            )
            method_idx = self.combo_modulus_method.currentIndex()
            method_map = {0: "hoek2002", 1: "hd2006", 2: "mr", 3: "serafim"}
            ei_val = self.spin_Ei.value()
            mr_val = self.spin_MR.value()

            modulus_params = RockMassModulus(
                sigma_ci=params.sigma_ci,
                gsi=params.gsi,
                D=params.D,
                Ei_input=ei_val if method_map.get(method_idx) == "hd2006" else None,
                MR=mr_val if method_map.get(method_idx) == "mr" else None,
            )

            sigma_3 = self.spin_sigma3.value()
            n_points = self.spin_n_points.value()

            self.analysis_result = run_analysis(
                params, modulus_params, sigma_3, (0, 0.5, n_points),
                application=self.combo_application.currentText(),
                modulus_method=method_map.get(method_idx, "hoek2002"),
                use_area_balance=True,
            )

            # 显示文本结果
            self.text_results.setPlainText(self.analysis_result.summary())

            # 自动更新图表
            self._update_plots()

            QMessageBox.information(self, "成功", "计算完成！\n请查看结果标签页和图表。")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"计算过程中出错:\n{str(e)}")

    def reset_inputs(self):
        """重置输入"""
        self.spin_sigma_ci.setValue(89.5)
        self.spin_gsi.setValue(64)
        self.spin_mi.setValue(24)
        self.spin_D.setValue(0.9)
        self.spin_gamma.setValue(0.027)
        self.spin_height.setValue(196)
        self.spin_Ei.setValue(5426)
        self.spin_MR.setValue(1000)
        self.spin_sigma3.setValue(0)
        self.spin_n_points.setValue(50)
        self.combo_modulus_method.setCurrentIndex(0)
        self.text_results.clear()
        self._clear_plots()
        QMessageBox.information(self, "提示", "输入已重置为默认值。")

    def export_results(self):
        """导出结果到文件"""
        if not self.analysis_result:
            QMessageBox.warning(self, "警告", "请先执行计算！")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存结果", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.analysis_result.summary())
            QMessageBox.information(self, "成功", f"结果已保存到:\n{file_path}")

    def show_plots(self):
        """显示图表"""
        if not self.analysis_result:
            QMessageBox.warning(self, "警告", "请先执行计算！")
            return
        self.tabs.setCurrentIndex(1)

    def _update_plots(self):
        """更新图表显示"""
        if not self.analysis_result:
            return

        ar = self.analysis_result

        # 清除旧内容
        self._clear_plots()

        # --- RocLab主图（上方） ---
        roclab_layout = self.roclab_area.layout()
        fig_roclab = plot_roclab_style(ar)
        canvas_roclab = MatplotlibCanvas(self.roclab_area, width=14, height=8, dpi=100)
        canvas_roclab.figure = fig_roclab
        toolbar_roclab = NavigationToolbar(canvas_roclab, self.roclab_area)
        roclab_layout.addWidget(toolbar_roclab)
        roclab_layout.addWidget(canvas_roclab)

        # --- 下方详细图表（2x2网格） ---
        modulus_plot = RockMassModulus(
            sigma_ci=ar.hb.sigma_ci, gsi=ar.hb.gsi, D=ar.hb.D
        ).compute()

        figs = {
            "Mohr": plot_mohr_circles(ar.hb.sigma_ci, ar.hb.mb, ar.hb.s, ar.hb.a,
                                      ar.mc.c_eq, ar.mc.phi_eq),
            "Strain": plot_strain_softening(ar.strain_results),
            "Depth": plot_depth_profile(ar.depth_profile),
            "Modulus": plot_modulus_comparison(modulus_plot),
        }

        grid = QGridLayout()
        grid.setSpacing(10)
        self.plot_area.setLayout(grid)

        row = 0
        col = 0
        for name, fig in figs.items():
            canvas = MatplotlibCanvas(width=4.5, height=3.2, dpi=100)
            canvas.figure = fig
            nav_toolbar = NavigationToolbar(canvas, self.plot_area)
            wrapper = QWidget()
            w_layout = QVBoxLayout(wrapper)
            w_layout.setContentsMargins(0, 0, 0, 0)
            label = QLabel(f"{name}")
            label.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
            label.setStyleSheet(f"color: {DARK_BLUE}; padding: 2px 4px;")
            w_layout.addWidget(label)
            w_layout.addWidget(nav_toolbar)
            w_layout.addWidget(canvas)
            grid.addWidget(wrapper, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

    def _clear_plots(self):
        """清除所有图表区域"""
        for area in [self.roclab_area, self.plot_area]:
            old = area.layout()
            if old:
                while old.count():
                    item = old.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()


# ============================================================================
# 入口
# ============================================================================

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_styles(app)

    window = HBReductionApp()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
