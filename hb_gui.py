"""
Hoek-Brown 岩体强度折减分析系统 - GUI 界面
基于 PyQt6 的交互式桌面应用

图表页（每页严格 ≤2 图）:
  包络线 | 面积平衡+Mohr | 软化+深度 | 模量+SRF | 文献与公式
"""
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox,
    QTabWidget, QFileDialog, QMessageBox, QSpinBox, QDoubleSpinBox,
    QComboBox, QPlainTextEdit, QTextBrowser, QSplitter, QFrame, QGridLayout,
    QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from hb_reduction import (
    HBParameters, RockMassModulus, run_analysis
)
from hb_plot import (
    plot_principal_envelope, plot_shear_envelope,
    plot_mohr_circles, plot_area_balance,
    plot_strain_softening, plot_depth_profile,
    plot_modulus_comparison, plot_srf_scan,
)


# ============================================================================
# 主题配色（与 hb_plot.HBTheme 语义对齐：slate 灰底 + 深蓝强调）
# ============================================================================

APP_BG        = "#f1f5f9"
PANEL_BG      = "#f8fafc"
CARD_BG       = "#ffffff"
BORDER        = "#e2e8f0"
BORDER_STRONG = "#94a3b8"
DARK_BLUE     = "#0f172a"
ACCENT        = "#1d4ed8"
ACCENT_HOVER  = "#1e40af"
TEXT_DARK     = "#1e293b"
TEXT_MUTED    = "#64748b"
SUCCESS_BTN   = "#15803d"
SUCCESS_HOVER = "#166534"
WARN          = "#c2410c"
INPUT_BG      = "#ffffff"
PURPLE        = "#7c3aed"


def apply_styles(app):
    """应用全局商业级样式表"""
    app.setStyleSheet(f"""
        QMainWindow {{
            background-color: {APP_BG};
        }}
        /* ---------- 区块（分组框） ---------- */
        QGroupBox {{
            font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
            font-weight: 600;
            font-size: 13px;
            color: {DARK_BLUE};
            border: 1px solid {BORDER};
            border-radius: 10px;
            margin-top: 14px;
            padding: 16px 12px 12px 12px;
            background-color: {CARD_BG};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 6px;
            color: {ACCENT};
            background-color: {CARD_BG};
        }}
        /* ---------- 标签 ---------- */
        QLabel {{
            font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
            font-size: 12.5px;
            color: {TEXT_DARK};
        }}
        /* ---------- 输入控件（白底 + 深色边框，与浅灰面板明显区分） ---------- */
        QDoubleSpinBox, QSpinBox, QLineEdit {{
            background-color: {INPUT_BG};
            border: 1px solid {BORDER_STRONG};
            border-radius: 6px;
            padding: 6px 8px;
            font-size: 13px;
            color: {TEXT_DARK};
            selection-background-color: {ACCENT};
            selection-color: white;
        }}
        QDoubleSpinBox:hover, QSpinBox:hover, QLineEdit:hover {{
            border: 1px solid {ACCENT};
        }}
        QDoubleSpinBox:focus, QSpinBox:focus, QLineEdit:focus {{
            border: 2px solid {ACCENT};
            background-color: #f0f6ff;
        }}
        QDoubleSpinBox::up-button, QSpinBox::up-button {{ width: 16px; }}
        QDoubleSpinBox::down-button, QSpinBox::down-button {{ width: 16px; }}
        /* ---------- 下拉框 ---------- */
        QComboBox {{
            background-color: {INPUT_BG};
            border: 1px solid {BORDER_STRONG};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 13px;
            color: {TEXT_DARK};
        }}
        QComboBox:hover {{ border: 1px solid {ACCENT}; }}
        QComboBox:focus {{ border: 2px solid {ACCENT}; }}
        QComboBox::drop-down {{ border: none; width: 22px; }}
        QComboBox QAbstractItemView {{
            background-color: {INPUT_BG};
            border: 1px solid {BORDER};
            selection-background-color: {ACCENT};
            selection-color: white;
        }}
        /* ---------- 按钮 ---------- */
        QPushButton {{
            background-color: {ACCENT};
            color: white;
            border: none;
            border-radius: 7px;
            padding: 9px 18px;
            font-size: 13px;
            font-weight: 600;
            font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
        }}
        QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}
        QPushButton:pressed {{ background-color: #08306b; }}
        QPushButton:disabled {{ background-color: #b7c2d4; color: #eef1f6; }}
        QPushButton#compute_btn {{
            background-color: {SUCCESS_BTN};
            font-size: 15px;
            padding: 11px 26px;
        }}
        QPushButton#compute_btn:hover {{ background-color: {SUCCESS_HOVER}; }}
        QPushButton#compute_btn:pressed {{ background-color: #1c5e2e; }}
        QPushButton#secondary_btn {{
            background-color: {CARD_BG};
            color: {ACCENT};
            border: 1px solid {ACCENT};
        }}
        QPushButton#secondary_btn:hover {{ background-color: #eaf2ff; }}
        /* ---------- 标签页 ---------- */
        QTabWidget::pane {{
            border: 1px solid {BORDER};
            border-radius: 10px;
            background-color: {CARD_BG};
            top: 6px;
        }}
        QTabBar::tab {{
            background-color: #e3e8f0;
            color: {TEXT_MUTED};
            padding: 9px 18px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", sans-serif;
            margin-right: 3px;
        }}
        QTabBar::tab:selected {{
            background-color: {CARD_BG};
            color: {ACCENT};
            border: 1px solid {BORDER};
            border-bottom: 2px solid {CARD_BG};
        }}
        QTabBar::tab:hover {{ background-color: #d7deea; }}
        /* ---------- 文本结果 ---------- */
        QTextEdit, QPlainTextEdit {{
            background-color: {INPUT_BG};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 10px;
            font-family: "Consolas", "SF Mono", "Menlo", monospace;
            font-size: 12px;
            color: {TEXT_DARK};
            line-height: 1.5;
        }}
        /* ---------- 滚动区域 ---------- */
        QScrollArea {{
            border: none;
            background-color: transparent;
        }}
        QScrollBar:vertical {{ width: 10px; background: #e3e8f0; }}
        QScrollBar::handle:vertical {{ background: #b7c2d4; border-radius: 5px; }}
        QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
        /* ---------- 状态栏 ---------- */
        QStatusBar {{
            background-color: {DARK_BLUE};
            color: #cdd9ec;
            font-size: 12px;
            padding: 4px 10px;
        }}
    """)


# ============================================================================
# 图表画布组件
# ============================================================================

class MetricCard(QFrame):
    """顶部关键指标卡片（商业级大数字展示）"""

    def __init__(self, title, value="—", unit="", accent=ACCENT, parent=None):
        super().__init__(parent)
        self.setObjectName("metric_card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(78)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._accent = accent
        self._title = title
        self._unit = unit

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: 600;"
        )
        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(
            f"color: {accent}; font-size: 22px; font-weight: 700; "
            f"font-family: Consolas, 'SF Mono', Menlo, monospace;"
        )
        self.value_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.unit_lbl = QLabel(unit)
        self.unit_lbl.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px;"
        )

        lay.addWidget(self.title_lbl)
        lay.addWidget(self.value_lbl)
        lay.addWidget(self.unit_lbl)

        self.setStyleSheet(f"""
            MetricCard, QFrame#metric_card {{
                background-color: {CARD_BG};
                border: 1px solid {BORDER};
                border-left: 4px solid {accent};
                border-radius: 10px;
            }}
        """)

    def set_value(self, value, unit=None):
        if unit is not None:
            self._unit = unit
            self.unit_lbl.setText(unit)
        self.value_lbl.setText(str(value))


def make_field(layout, label_text, widget, unit_text=None, tip=None, row=None):
    """在网格布局中放置一个带标签的字段，返回 widget。"""
    lbl = QLabel(label_text)
    lbl.setWordWrap(True)
    if tip:
        lbl.setToolTip(tip)
        widget.setToolTip(tip)
    if row is None:
        row = layout.rowCount()
    layout.addWidget(lbl, row, 0)
    if unit_text:
        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(widget, 1)
        u = QLabel(unit_text)
        u.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        h.addWidget(u)
        layout.addLayout(h, row, 1)
    else:
        layout.addWidget(widget, row, 1)
    return widget


def make_combo(items, current=None):
    cb = QComboBox()
    cb.addItems(items)
    if current is not None and current in items:
        cb.setCurrentText(current)
    return cb


class MatplotlibCanvas(FigureCanvas):
    """Matplotlib 图表在 Qt 中的画布。

    支持两种模式:
      * 传入外部 figure（推荐）:复用 hb_plot 中 constrained_layout 的 figure,
        窗口缩放时自动重新排版,实现"图形铺满布局窗口"。
      * 不传 figure 时自建空 figure（占位用）。

    尺寸策略:Expanding + 自定义 sizeHint,使画布在 splitter / 网格中
    能自由放大或缩小到任意窗口尺寸,不受 figsize 写死限制。
    """
    def __init__(self, parent=None, figure=None, width=8, height=5, dpi=100):
        if figure is None:
            self.figure = Figure(figsize=(width, height), dpi=dpi, constrained_layout=True)
        else:
            self.figure = figure
        super().__init__(self.figure)
        self.setParent(parent)
        self.figure.patch.set_facecolor("white")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.updateGeometry()
        # resize 节流:窗口快速拖动时减少重绘次数,避免卡顿
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(80)
        self._resize_timer.timeout.connect(self._delayed_refresh)

    def sizeHint(self) -> QSize:
        return QSize(640, 420)

    def minimumSizeHint(self) -> QSize:
        return QSize(120, 100)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start()

    def _delayed_refresh(self):
        # 图表使用 constrained_layout,Qt resize 后仅需触发重绘即可自动重排版铺满。
        # 不调用 tight_layout()(与 constrained_layout 互斥,会报 warning)。
        self.draw_idle()

    def attach_figure(self, figure):
        """替换当前 figure 为新 figure（用于更新图表时避免重建画布对象）"""
        self.figure = figure
        self.figure.patch.set_facecolor("white")
        self.draw_idle()


# ============================================================================
# 主窗口
# ============================================================================

class HBReductionApp(QMainWindow):
    """Hoek-Brown岩体强度折减分析主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hoek-Brown 岩体强度折减分析系统 v1.1")
        self.setMinimumSize(1120, 740)
        self._plot_figures = []  # 跟踪当前 figure，便于精确关闭
        self.analysis_result = None
        self._build_ui()
        # 启动时给一个较大窗口并居中,默认铺满屏幕 75%
        screen = QApplication.primaryScreen().availableGeometry()
        w = int(screen.width() * 0.78)
        h = int(screen.height() * 0.82)
        self.resize(w, h)
        self.move((screen.width() - w) // 2, (screen.height() - h) // 2)

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
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {DARK_BLUE}; padding: 8px; background-color: {CARD_BG}; border-radius: 8px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- 左侧:输入面板(可滚动,固定最大宽度避免被拉得过宽) ---
        left_panel = self._create_input_panel()
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(left_panel)
        left_scroll.setMaximumWidth(420)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        splitter.addWidget(left_scroll)

        # --- 右侧:结果面板 ---
        right_panel = self._create_result_panel()
        splitter.addWidget(right_panel)


        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([360, self.width() - 380])
        main_layout.addWidget(splitter, 1)

        sb = self.statusBar()
        sb.setStyleSheet(f"background-color: {DARK_BLUE}; color: #cdd9ec; font-size: 12px; padding: 4px 10px;")
        sb.showMessage("就绪 \u2014 输入参数后点击『执行分析』")


    def _create_input_panel(self) -> QWidget:
        """创建左侧输入面板（商业级：分组清晰、白底输入框、单位标注）"""
        panel = QWidget()
        root = QVBoxLayout(panel)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        title = QLabel("工程参数输入")
        title.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {DARK_BLUE}; "
            f"font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;"
        )
        root.addWidget(title)
        sub = QLabel("Hoek-Brown 岩体强度折减分析")
        sub.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        root.addWidget(sub)

        # 基本强度参数
        basic_group = QGroupBox("基本强度参数")
        basic_layout = QGridLayout()
        basic_layout.setColumnStretch(1, 1)
        basic_layout.setHorizontalSpacing(10)
        basic_layout.setVerticalSpacing(8)

        self.spin_sigma_ci = QDoubleSpinBox()
        self.spin_sigma_ci.setRange(1, 500)
        self.spin_sigma_ci.setValue(89.5)
        self.spin_sigma_ci.setDecimals(2)
        self.spin_sigma_ci.setSuffix(" MPa")
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

        make_field(basic_layout, "单轴抗压强度 \u03c3ci (MPa):", self.spin_sigma_ci)
        make_field(basic_layout, "地质强度指标 GSI:", self.spin_gsi)
        make_field(basic_layout, "岩体类型参数 mi:", self.spin_mi)
        make_field(basic_layout, "扰动系数 D:", self.spin_D)
        make_field(basic_layout, "岩体容重 \u03b3 (MN/m\u00b3):", self.spin_gamma)
        make_field(basic_layout, "开挖高度 H (m):", self.spin_height)
        basic_group.setLayout(basic_layout)

        # 弹性模量
        modulus_group = QGroupBox("弹性模量计算选项")
        modulus_layout = QGridLayout()
        modulus_layout.setColumnStretch(1, 1)
        self.combo_modulus_method = make_combo(
            ["Hoek(2002) [推荐]", "Hoek&Diederichs(2006)", "模量比法", "Serafim&Pereira(1983)"]
        )
        self.spin_Ei = QDoubleSpinBox()
        self.spin_Ei.setRange(0, 1000000)
        self.spin_Ei.setValue(5426)
        self.spin_Ei.setDecimals(1)
        self.spin_Ei.setSuffix(" MPa")
        self.spin_MR = QDoubleSpinBox()
        self.spin_MR.setRange(0, 10000)
        self.spin_MR.setValue(1000)
        self.spin_MR.setDecimals(1)
        make_field(modulus_layout, "计算方法:", self.combo_modulus_method)
        make_field(modulus_layout, "完整岩石模量 Ei (MPa):", self.spin_Ei)
        make_field(modulus_layout, "模量比 MR:", self.spin_MR)
        modulus_group.setLayout(modulus_layout)

        # 分析选项
        option_group = QGroupBox("分析选项")
        option_layout = QGridLayout()
        option_layout.setColumnStretch(1, 1)
        self.combo_application = make_combo(["隧道 (Tunnel)", "边坡 (Slope)"], current="隧道 (Tunnel)")
        self.spin_sigma3 = QDoubleSpinBox()
        self.spin_sigma3.setRange(0, 100)
        self.spin_sigma3.setValue(0)
        self.spin_sigma3.setDecimals(2)
        self.spin_sigma3.setSuffix(" MPa")
        self.spin_n_points = QSpinBox()
        self.spin_n_points.setRange(10, 200)
        self.spin_n_points.setValue(50)
        make_field(option_layout, "最小主应力 \u03c33 (MPa):", self.spin_sigma3)
        make_field(option_layout, "工程类型:", self.combo_application)
        make_field(option_layout, "应变点数:", self.spin_n_points)
        option_group.setLayout(option_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.btn_compute = QPushButton("\u27a0 执行分析 \u27a0")
        self.btn_compute.setObjectName("compute_btn")
        self.btn_reset = QPushButton("重置")
        self.btn_reset.setObjectName("secondary_btn")
        self.btn_export = QPushButton("导出")
        self.btn_export.setObjectName("secondary_btn")
        self.btn_plot = QPushButton("图表")
        self.btn_plot.setObjectName("secondary_btn")
        btn_layout.addWidget(self.btn_compute)
        btn_layout.addWidget(self.btn_reset)
        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_plot)
        btn_layout.addStretch()

        self.btn_compute.clicked.connect(self.run_computation)
        self.btn_reset.clicked.connect(self.reset_inputs)
        self.btn_export.clicked.connect(self.export_results)
        self.btn_plot.clicked.connect(self.show_plots)

        root.addWidget(basic_group)
        root.addWidget(modulus_group)
        root.addWidget(option_group)
        root.addSpacing(4)
        root.addLayout(btn_layout)
        root.addStretch()
        return panel

    def _create_result_panel(self) -> QWidget:
        """创建右侧结果面板（关键指标卡片 + 图表/报告标签页）"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # 顶部关键指标卡片
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)
        self.metric_scm = MetricCard("岩体抗压强度 \u03c3cm", "\u2014", "MPa", ACCENT)
        self.metric_c = MetricCard("等效黏聚力 c'", "\u2014", "MPa", SUCCESS_BTN)
        self.metric_phi = MetricCard("等效内摩擦角 \u03c6'", "\u2014", "\u00b0", "#c77700")
        self.metric_em = MetricCard("变形模量 Em", "\u2014", "GPa", ACCENT)
        self.metric_s3 = MetricCard("面积平衡 \u03c3\u2083max", "\u2014", "MPa", "#7b1fa2")
        for c in (self.metric_scm, self.metric_c, self.metric_phi, self.metric_em, self.metric_s3):
            cards_layout.addWidget(c)
        layout.addLayout(cards_layout)

        # 主标签：图表 | 报告 | 文献
        self.tabs = QTabWidget()

        # 图表子标签（每页 ≤2 图）
        self.plot_tabs = QTabWidget()
        self.tab_envelope = self._make_plot_page()
        self.tab_mohr_area = self._make_plot_page()
        self.tab_soft_depth = self._make_plot_page()
        self.tab_mod_srf = self._make_plot_page()
        self.plot_tabs.addTab(self.tab_envelope, "包络线")
        self.plot_tabs.addTab(self.tab_mohr_area, "面积平衡 · Mohr")
        self.plot_tabs.addTab(self.tab_soft_depth, "软化 · 深度")
        self.plot_tabs.addTab(self.tab_mod_srf, "模量 · SRF")

        self.plot_tab = QWidget()
        plot_layout = QVBoxLayout(self.plot_tab)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(0)
        plot_layout.addWidget(self.plot_tabs)

        self.text_results = QPlainTextEdit()
        self.text_results.setReadOnly(True)

        self.literature_view = QTextBrowser()
        self.literature_view.setOpenExternalLinks(True)
        self.literature_view.setHtml(self._literature_html())

        self.tabs.addTab(self.plot_tab, "图表分析")
        self.tabs.addTab(self.text_results, "结果报告")
        self.tabs.addTab(self.literature_view, "文献与公式")

        layout.addWidget(self.tabs, 1)
        return panel

    def _make_plot_page(self) -> QWidget:
        """带水平分割的双图画布页（最多 2 个 figure 并排/上下）"""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(6)
        return page

    @staticmethod
    def _literature_html() -> str:
        """文献与公式说明页（eq.3–13 与引用）"""
        return """
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body { font-family: "PingFang SC","Microsoft YaHei",sans-serif;
         color:#1e293b; line-height:1.55; padding:12px 18px; background:#fff; }
  h2 { color:#0f172a; border-bottom:2px solid #1d4ed8; padding-bottom:6px; font-size:18px; }
  h3 { color:#1d4ed8; margin-top:1.4em; font-size:14px; }
  .eq { font-family: "Times New Roman", serif; background:#f8fafc;
        border-left:3px solid #1d4ed8; padding:8px 12px; margin:8px 0;
        font-size:13.5px; color:#0f172a; }
  .eq-id { color:#64748b; font-size:12px; margin-right:8px; font-family:sans-serif; }
  .ref { font-size:12.5px; margin:6px 0 6px 12px; color:#334155; }
  .note { font-size:12px; color:#64748b; background:#f1f5f9; padding:8px 12px;
          border-radius:6px; margin-top:12px; }
  table { border-collapse:collapse; width:100%; font-size:12.5px; margin:8px 0; }
  th, td { border:1px solid #e2e8f0; padding:6px 10px; text-align:left; }
  th { background:#f1f5f9; color:#0f172a; }
  code { background:#f1f5f9; padding:1px 5px; border-radius:3px; font-size:12px; }
</style></head><body>
<h2>文献与公式（Hoek 2002）</h2>
<p>本系统严格实现广义 Hoek-Brown 准则，并与 RocLab / FLAC / Slide 计算流程对齐。</p>

<h3>1. 广义 Hoek-Brown 准则</h3>
<div class="eq"><span class="eq-id">准则</span>
σ₁′ = σ₃′ + σ<sub>ci</sub> (m<sub>b</sub>·σ₃′/σ<sub>ci</sub> + s)<sup>a</sup>
</div>

<h3>2. 岩体常数 mb, s, a（eq.3–5）</h3>
<div class="eq"><span class="eq-id">eq.3</span>
m<sub>b</sub> = m<sub>i</sub> · exp[(GSI − 100)/(28 − 14D)]
</div>
<div class="eq"><span class="eq-id">eq.4</span>
s = exp[(GSI − 100)/(9 − 3D)]
</div>
<div class="eq"><span class="eq-id">eq.5</span>
a = ½ + (e<sup>−GSI/15</sup> − e<sup>−20/3</sup>)/6
</div>

<h3>3. 岩体强度（eq.6–7）</h3>
<div class="eq"><span class="eq-id">eq.6</span>
σ<sub>cm</sub> = σ<sub>ci</sub> · s<sup>a</sup>
&nbsp;&nbsp;&nbsp;（岩体单轴抗压强度）
</div>
<div class="eq"><span class="eq-id">eq.7</span>
σ<sub>t</sub> = − s · σ<sub>ci</sub> / m<sub>b</sub>
&nbsp;&nbsp;&nbsp;（岩体抗拉强度）
</div>

<h3>4. 变形模量 Em（eq.11）</h3>
<div class="eq"><span class="eq-id">eq.11a</span>
σ<sub>ci</sub> ≤ 100 MPa：&nbsp;
E<sub>m</sub> (GPa) = (1 − D/2) · √(σ<sub>ci</sub>/100) · 10<sup>(GSI−10)/40</sup>
</div>
<div class="eq"><span class="eq-id">eq.11b</span>
σ<sub>ci</sub> &gt; 100 MPa：&nbsp;
E<sub>m</sub> (GPa) = (1 − D/2) · 10<sup>(GSI−10)/40</sup>
</div>
<p style="font-size:12.5px;color:#64748b;">另实现 Hoek &amp; Diederichs (2006)、模量比法、Serafim &amp; Pereira (1983)。</p>

<h3>5. 等效 Mohr-Coulomb（eq.12–13，面积平衡）</h3>
<div class="eq"><span class="eq-id">eq.12</span>
sin φ′ = 6a m<sub>b</sub> (s + m<sub>b</sub> σ<sub>3n</sub>)<sup>a−1</sup>
&nbsp;/&nbsp; [2(1+a)(2+a) + 6a m<sub>b</sub> (s + m<sub>b</sub> σ<sub>3n</sub>)<sup>a−1</sup>]
<br><span style="font-size:12px;color:#64748b;">其中 σ<sub>3n</sub> = σ<sub>3max</sub> / σ<sub>ci</sub></span>
</div>
<div class="eq"><span class="eq-id">eq.13</span>
c′ = σ<sub>ci</sub> · [(1+2a)s + (1−a)m<sub>b</sub> σ<sub>3n</sub>] · (s+m<sub>b</sub>σ<sub>3n</sub>)<sup>a−1</sup>
&nbsp;/&nbsp; {(1+a)(2+a) · √[1 + 6a m<sub>b</sub> (s+m<sub>b</sub>σ<sub>3n</sub>)<sup>a−1</sup> / ((1+a)(2+a))]}
</div>

<h3>6. 面积平衡范围 σ<sub>3max</sub>（eq.18–19）</h3>
<div class="eq"><span class="eq-id">eq.18 隧道</span>
σ<sub>3max</sub>/σ<sub>cm</sub> = 0.47 (σ<sub>cm</sub>/γH)<sup>−0.94</sup>
</div>
<div class="eq"><span class="eq-id">eq.19 边坡</span>
σ<sub>3max</sub>/σ<sub>cm</sub> = 0.72 (σ<sub>cm</sub>/γH)<sup>−0.91</sup>
</div>

<h3>7. 强度折减（SRF / SRM）</h3>
<table>
  <tr><th>策略</th><th>公式</th><th>用途</th></tr>
  <tr><td>MC 折减</td><td>c′<sub>F</sub>=c′/F，&nbsp;tanφ′<sub>F</sub>=tanφ′/F</td>
      <td>Slide / Phase2 极限平衡</td></tr>
  <tr><td>H-B 折减</td><td>σ<sub>ci,F</sub>=σ<sub>ci</sub>/F（m<sub>b</sub>,s,a 不变）</td>
      <td>FLAC 直接 H-B 本构</td></tr>
</table>

<h3>主要参考文献</h3>
<div class="ref">1. Hoek, E., Carranza-Torres, C., Corkum, B. (2002).
  <i>Hoek-Brown failure criterion — 2002 edition.</i>
  Proc. NARMS-TAC, Toronto, 267–273.</div>
<div class="ref">2. Hoek, E., Diederichs, M.S. (2006).
  <i>Empirical estimation of rock mass modulus.</i>
  Int. J. Rock Mech. Min. Sci., 43(2), 203–215.</div>
<div class="ref">3. Serafim, J.L., Pereira, J.P. (1983).
  <i>Consideration of the geomechanical classification of Bieniawski.</i>
  Proc. Int. Symp. Engineering Geology and Underground Construction, Lisbon.</div>
<div class="ref">4. RocScience RocLab / FLAC / Slide — 工程软件实现惯例（本项目计算对齐）。</div>

<div class="note">
  验证：运行 <code>python main.py --validate</code> 对照论文经典算例与闭式公式交叉验证。<br>
  方法细节见项目内 <code>METHODOLOGY.md</code>。
</div>
</body></html>
"""

    def run_computation(self):
        """执行计算并更新结果（文本 + 指标卡片 + 图表）"""
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
            application = self._parse_application(self.combo_application.currentText())

            self.analysis_result = run_analysis(
                params, modulus_params, sigma_3, (0, 0.5, n_points),
                application=application,
                modulus_method=method_map.get(method_idx, "hoek2002"),
                use_area_balance=True,
            )

            ar = self.analysis_result
            self.metric_scm.set_value(f"{ar.hb.sigma_cm:.1f}")
            self.metric_c.set_value(f"{ar.mc.c_eq / 1000:.3f}")
            self.metric_phi.set_value(f"{ar.mc.phi_eq:.1f}")
            self.metric_em.set_value(
                f"{ar.modulus.Em_selected / 1000:.2f}" if ar.modulus.Em_selected else "\u2014"
            )
            self.metric_s3.set_value(f"{ar.sigma_3max:.2f}")

            self.text_results.setPlainText(ar.summary())
            self._update_plots()

            # c_eq 单位为 kPa；状态栏同时给出 MPa 便于对照
            self.statusBar().showMessage(
                f"计算完成 | \u03c3cm={ar.hb.sigma_cm:.1f} MPa, "
                f"c'={ar.mc.c_eq:.1f} kPa ({ar.mc.c_eq/1000:.3f} MPa), "
                f"\u03c6'={ar.mc.phi_eq:.1f}\u00b0"
            )
            self.tabs.setCurrentWidget(self.plot_tab)
            self.plot_tabs.setCurrentIndex(0)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"计算过程中出错:\n{str(e)}")

    @staticmethod
    def _parse_application(text: str) -> str:
        t = (text or "").lower()
        if "slope" in t or "边坡" in (text or ""):
            return "slope"
        return "tunnel"

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
        self.combo_application.setCurrentIndex(0)
        self.text_results.clear()
        for c in (self.metric_scm, self.metric_c, self.metric_phi, self.metric_em, self.metric_s3):
            c.set_value("\u2014")
        self._clear_plots()
        self.statusBar().showMessage("输入已重置为默认值")

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
        """切换到图表分析页"""
        if not self.analysis_result:
            QMessageBox.warning(self, "警告", "请先执行计算！")
            return
        self.tabs.setCurrentWidget(self.plot_tab)

    def _update_plots(self):
        """按主题分页更新图表（每页严格 ≤2 图，水平并排）"""
        if not self.analysis_result:
            return

        ar = self.analysis_result
        hb, mc = ar.hb, ar.mc
        self._clear_plots()

        # --- 包络线（H-B + MC）: 2 图 ---
        fig_p = plot_principal_envelope(hb.sigma_ci, hb.mb, hb.s, hb.a, mc.c_eq, mc.phi_eq)
        fig_s = plot_shear_envelope(mc.c_eq, mc.phi_eq)
        self._fill_plot_page(self.tab_envelope, [
            (fig_p, "主应力空间 H-B + MC"),
            (fig_s, "剪应力空间等效 MC"),
        ])

        # --- 面积平衡 + Mohr: 2 图 ---
        fig_ab = plot_area_balance(ar)
        fig_mohr = plot_mohr_circles(hb.sigma_ci, hb.mb, hb.s, hb.a, mc.c_eq, mc.phi_eq)
        self._fill_plot_page(self.tab_mohr_area, [
            (fig_ab, "面积平衡 (σn-τ)"),
            (fig_mohr, "Mohr 圆与 H-B 包络"),
        ])

        # --- 软化 + 深度: 2 图 ---
        fig_soft = plot_strain_softening(ar.strain_results)
        fig_depth = plot_depth_profile(ar.depth_profile)
        self._fill_plot_page(self.tab_soft_depth, [
            (fig_soft, "峰后应变软化"),
            (fig_depth, "深度应力剖面"),
        ])

        # --- 模量 + SRF: 2 图 ---
        fig_mod = plot_modulus_comparison(ar.modulus)
        fig_srf = plot_srf_scan(ar.srf_scan)
        self._fill_plot_page(self.tab_mod_srf, [
            (fig_mod, "变形模量对比"),
            (fig_srf, "强度折减扫描 SRF"),
        ])

    def _fill_plot_page(self, page: QWidget, items):
        """向页面填充 1–2 个 figure（水平 splitter，保证窗口内并排 ≤2 图）"""
        import matplotlib.pyplot as plt
        layout = page.layout()
        if layout is None:
            return
        # 清空
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

        if not items:
            return
        if len(items) == 1:
            fig, title = items[0]
            self._plot_figures.append(fig)
            layout.addWidget(self._make_figure_widget(fig, title), 1)
            return

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        for fig, title in items[:2]:  # 硬上限 2
            self._plot_figures.append(fig)
            splitter.addWidget(self._make_figure_widget(fig, title))
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

    def _make_figure_widget(self, figure: Figure, title: str = "") -> QWidget:
        """单个 figure + 工具栏包装"""
        wrapper = QWidget()
        w_layout = QVBoxLayout(wrapper)
        w_layout.setContentsMargins(2, 2, 2, 2)
        w_layout.setSpacing(2)

        if title:
            label = QLabel(title)
            label.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
            label.setStyleSheet(f"color: {DARK_BLUE}; padding: 2px 4px;")
            w_layout.addWidget(label)

        canvas = MatplotlibCanvas(wrapper, figure=figure)
        toolbar = NavigationToolbar(canvas, wrapper)
        toolbar.setMinimumHeight(36)
        toolbar.setMaximumHeight(40)
        toolbar.setStyleSheet(
            f"background-color: {PANEL_BG}; border: 1px solid {BORDER}; "
            f"border-radius: 4px; padding: 1px;"
        )
        w_layout.addWidget(canvas, 1)
        w_layout.addWidget(toolbar)
        return wrapper

    def _clear_plots(self):
        """清理四页图表控件并关闭本会话创建的 figure（避免全局 close 误伤）"""
        import matplotlib.pyplot as plt
        for tab_widget in (
            self.tab_envelope, self.tab_mohr_area,
            self.tab_soft_depth, self.tab_mod_srf,
        ):
            old_layout = tab_widget.layout()
            if old_layout is None:
                continue
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget() if item is not None else None
                if widget is not None:
                    widget.setParent(None)
                    widget.deleteLater()
        for fig in self._plot_figures:
            try:
                plt.close(fig)
            except Exception:
                pass
        self._plot_figures.clear()



# ============================================================================
# 入口
# ============================================================================

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_styles(app)

    window = HBReductionApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
