import math
import os
import pickle
import random
import sys
import time

from PyQt5.QtCore import Qt, QPoint, QPointF
from PyQt5.QtGui import QPainter, QPixmap, QPen, QFont, QStandardItemModel, QStandardItem, QIcon, QIntValidator, QColor
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QSizePolicy, QTableView, QGridLayout, QGroupBox, \
    QPushButton, QCheckBox, QLineEdit, QMainWindow, QAction, QFileDialog, QTextEdit, QComboBox

from adjacency_matrix_to_pos import get_position
from mc_algorithm.mc_base_bk import *


#  1、右下角给出求最大团算法的复选框
#  2、各操作的状态栏更新
#  3、调用最大团算法，渲染结果到pix [[4,3,2,1,0],[5,4,3,2]] 每行一次查找结果
#         输出到log区，每行结束 标红结果
class MainDrawWindow(QMainWindow):
    # <editor-fold desc="窗体属性及数据属性">
    # 窗口大小
    WINDOW_WIDTH = 1700
    # WINDOW_HEIGHT = 1060
    WINDOW_HEIGHT = round(WINDOW_WIDTH / 1.8888888)

    # 点数
    POINTS_NUM = 20
    # 所绘制的圆的半径
    CIRCULAR_RADIUS = 20

    # 画布长宽
    # 根据窗口大小算出画布大小
    PIX_WIDTH = round(WINDOW_WIDTH * 0.7)
    PIX_HEIGHT = WINDOW_HEIGHT - 50

    # 鼠标相对于画布的偏置
    # 获取鼠标在画布上的点击坐标时需要
    MOUSE_BIAS_X = 10
    MOUSE_BIAS_Y = 40
    # 表格行高、列宽
    TABLE_ROW_HEIGHT = 40
    TABLE_COL_WIDTH = TABLE_ROW_HEIGHT
    # 最多点数
    MAX_POINTS_NUM = 0
    # 在给定点数时允许输入的最多边数
    ALLOW_INPUT_MAX_EDGES = 0

    # 生成的上三角阵
    MATRIX_TRIU = None
    # 对角阵
    MATRIX_DIAGONAL = None
    # 仅显示对角阵在右上角
    ONLY_SHOW_MATRIX_TRIU = False
    # 矩阵备份 只备份上三角阵即可
    BACKUP_MATRIX_TRIU = None

    # numpy 保存路径
    NUMPY_PATH = './numpy_file/'
    # 默认名
    NUMPY_TXT_NAME = 'matrix_triu.npy'
    # 边列
    line_list = []
    # 备份边列
    backup_line_list = []
    # 点集
    circular_pos_dict = dict()
    # 备份点集
    backup_pos_dict = dict()

    # 日志内容
    log_text = ''

    # 手动停止算法标志
    MC_IS_NEED_STOP = False
    # 单步模式标志
    MC_STEP_MODEL = False
    # 单步执行到的节点
    mc_step_current_point = -1
    # 最大团节点列表
    clique_list = list()
    # 极大团解集
    solution_all = list()
    # 最大团解集
    solution_max = list()
    # 当前遍历的最大团索引
    solution_index = -1

    # 随机游走路径模型
    models = []

    # </editor-fold>

    def __init__(self, parent=None):
        super(MainDrawWindow, self).__init__(parent)

        self.setWindowTitle(u'最大团可视化工具')
        self.setWindowIcon(QIcon('./images/six_blue.png'))
        # 状态栏
        self.statusBar().showMessage('就绪')
        # 工具栏
        toolBar = self.addToolBar('Tool')
        self.tool_new_file = QAction(QIcon("./images/file-add.png"), '新建图', self)
        self.tool_open_file = QAction(QIcon("./images/file-open.png"), '打开矩阵', self)
        self.tool_save_file = QAction(QIcon("./images/save.png"), '保存矩阵', self)

        self.tool_add_circular = QAction(QIcon("./images/add-circle.png"), '添加节点', self)
        self.tool_add_edge = QAction(QIcon("./images/add.png"), '添加边', self)

        self.tool_add_circular.setCheckable(True)
        self.tool_add_edge.setCheckable(True)

        toolBar.addAction(self.tool_new_file)
        toolBar.addAction(self.tool_open_file)
        toolBar.addAction(self.tool_save_file)
        # 分隔符
        toolBar.addSeparator()

        toolBar.addAction(self.tool_add_circular)
        toolBar.addAction(self.tool_add_edge)

        self.setWindowTitle(u'最大团可视化工具')
        # 网格布局
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(5)
        self.draw_widget = QWidget()
        self.draw_widget.setLayout(self.grid_layout)
        self.setCentralWidget(self.draw_widget)

        # <editor-fold desc="设置左侧画布大小">
        self.q_label = QLabel()
        self.q_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.grid_layout.addWidget(self.q_label, 0, 0, 10, 6)

        # 画布大小为局部变量，已算过
        self.pix = QPixmap(self.PIX_WIDTH, self.PIX_HEIGHT)
        self.pix.fill(Qt.white)
        self.q_label.setPixmap(self.pix)

        self.font_num = QFont("Microsoft YaHei UI", 18, QFont.Normal)
        self.font_table = QFont("Microsoft YaHei UI", 14, QFont.Normal)
        self.font_table_header = QFont("Microsoft YaHei UI", 12, QFont.Normal)
        # </editor-fold>

        # <editor-fold desc="右侧按钮区">
        # 按钮组一
        self.group_box_btn = QGroupBox('邻接矩阵操作区')
        self.grid_layout.addWidget(self.group_box_btn, 5, 7, 2, 4)

        # 按钮组 网格布局
        self.group_box_btn_grid_layout = QGridLayout()
        self.group_box_btn_grid_layout.setSpacing(10)
        self.group_box_btn.setLayout(self.group_box_btn_grid_layout)

        # 清空矩阵
        self.only_triu_matrix_checkbox = QCheckBox('仅显示对角阵')

        # 第一行按钮
        self.btn_clear_matrix = QPushButton('清空矩阵')
        self.btn_add_circular = QPushButton('添加点')
        self.btn_commit = QPushButton('应用修改')
        self.btn_cancel_all = QPushButton('撤销修改')

        self.group_box_btn_grid_layout.addWidget(self.only_triu_matrix_checkbox, 0, 0, 1, 1)
        self.group_box_btn_grid_layout.addWidget(self.btn_clear_matrix, 1, 0, 1, 1)
        self.group_box_btn_grid_layout.addWidget(self.btn_add_circular, 1, 1, 1, 1)
        self.group_box_btn_grid_layout.addWidget(self.btn_commit, 1, 2, 1, 1)
        self.group_box_btn_grid_layout.addWidget(self.btn_cancel_all, 1, 3, 1, 1)

        # 第二行按钮
        self.label_generate_matrix_hint = QLabel('随机生成矩阵的参数：')
        self.label_matrix_points = QLabel('节点个数：')
        self.label_matrix_edges = QLabel('边数：')
        self.label_matrix_seed = QLabel('随机种子（可选）：')

        self.edit_points = QLineEdit()
        self.edit_points.setValidator(QIntValidator())
        self.edit_points.setMinimumWidth(150)
        self.edit_edges = QLineEdit()
        self.edit_edges.setValidator(QIntValidator())
        self.edit_edges.setMinimumWidth(150)
        self.edit_seed = QLineEdit()

        self.btn_generate = QPushButton('随机生成矩阵')
        self.group_box_btn_grid_layout.addWidget(self.label_generate_matrix_hint, 2, 0, 1, 1)
        self.group_box_btn_grid_layout.addWidget(self.label_matrix_points, 3, 0, 1, 1)
        self.group_box_btn_grid_layout.addWidget(self.edit_points, 3, 1, 1, 1)
        self.group_box_btn_grid_layout.addWidget(self.label_matrix_seed, 3, 2, 1, 1)
        self.group_box_btn_grid_layout.addWidget(self.edit_seed, 3, 3, 1, 1)
        self.group_box_btn_grid_layout.addWidget(self.label_matrix_edges, 4, 0, 1, 1)
        self.group_box_btn_grid_layout.addWidget(self.edit_edges, 4, 1, 1, 1)
        self.group_box_btn_grid_layout.addWidget(self.btn_generate, 4, 2, 1, 2)

        # 按钮组二
        self.group_box_max_clique = QGroupBox('最大团算法')
        self.grid_layout.addWidget(self.group_box_max_clique, 7, 7, 4, 4)

        self.group_box_mc_grid_layout = QGridLayout()
        self.group_box_mc_grid_layout.setSpacing(10)
        self.group_box_max_clique.setLayout(self.group_box_mc_grid_layout)

        # 算法选择框，按钮
        self.combobox_mc_algorithm = QComboBox()
        self.combobox_mc_algorithm.addItems(['random walk algorithm', 'mc base on bk'])
        self.group_box_mc_grid_layout.addWidget(self.combobox_mc_algorithm, 0, 0, 1, 2)

        # 操作按钮
        self.btn_mc_stop = QPushButton('终止/重置')
        self.btn_mc_play = QPushButton('执行')
        self.btn_mc_previous = QPushButton('上一步')
        self.btn_mc_next = QPushButton('下一步')

        self.btn_mc_play.setCheckable(True)
        self.btn_mc_play.setEnabled(False)

        self.group_box_mc_grid_layout.addWidget(self.btn_mc_stop, 1, 0)
        self.group_box_mc_grid_layout.addWidget(self.btn_mc_play, 1, 1)
        self.group_box_mc_grid_layout.addWidget(self.btn_mc_previous, 1, 2)
        self.group_box_mc_grid_layout.addWidget(self.btn_mc_next, 1, 3)

        # 日志框
        self.text_log_edit = QTextEdit()
        self.text_log_edit.setReadOnly(True)
        # self.text_log.setHtml("""
        # line1<br/>
        # <font color='red'>line2</font>
        # """)
        self.group_box_mc_grid_layout.addWidget(self.text_log_edit, 2, 0, 3, 4)

        # </editor-fold>

        # <editor-fold desc="绘画属性及参数">
        # 绘制种类
        self.draw_tag = 'nothing'
        # 主画布
        # self.pix = QPixmap()
        # 备份画布
        self.backupPix = QPixmap()
        # 辅助画布
        self.tempPix = QPixmap()
        # 是否正在绘图
        self.isDrawing = False
        # 是否保存绘制结果
        self.isSavePix = False
        # 是否能移动圆
        # self.isCanMove = False
        # 待移动的点 id
        self.moving_point_id = None
        # 保存移动时点的边
        self.temp_moving_point_line = []

        self.lastPoint = QPoint()
        self.endPoint = QPoint()
        # </editor-fold>

        # <editor-fold desc="右侧table widget 邻接矩阵区域">
        # 数据表格
        self.table_view = QTableView()
        self.grid_layout.addWidget(self.table_view, 0, 7, 5, 4)
        # 先声明，渲染时初始化
        self.table_model = QStandardItemModel()
        self.render_matrix(None)

        # </editor-fold>

        # <editor-fold desc="窗体位置及总布局">
        # 设置窗口位置 居中显示 和窗口大小
        self.resize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        self.center()
        self.show()
        # </editor-fold>

        # <editor-fold desc="按钮绑定事件">
        # 状态栏按钮
        # 新建矩阵 -> 清空矩阵
        self.tool_new_file.triggered.connect(self.func_clear_matrix)
        # 打开矩阵
        self.tool_open_file.triggered.connect(self.func_open_matrix)
        # 保存矩阵
        self.tool_save_file.triggered.connect(self.func_save_matrix)

        # noinspection PyTypeChecker
        self.tool_add_circular.triggered.connect(lambda: self.func_btn_check_able_check(self.tool_add_circular))
        # noinspection PyTypeChecker
        self.tool_add_edge.triggered.connect(lambda: self.func_btn_check_able_check(self.tool_add_edge))

        # 点数输入框
        self.edit_points.textChanged.connect(self.func_edit_points_changed)
        # 只显示对角阵复选框
        self.only_triu_matrix_checkbox.clicked.connect(self.func_checkbox_changed)
        self.btn_add_circular.clicked.connect(self.func_add_circular_in_model)
        self.btn_clear_matrix.clicked.connect(self.func_clear_matrix)
        self.btn_generate.clicked.connect(self.func_generate_matrix)
        self.btn_commit.clicked.connect(self.func_commit_changes)
        self.btn_cancel_all.clicked.connect(self.func_cancel_changes)

        # 最大团算法事件
        self.btn_mc_stop.clicked.connect(self.func_mc_stop)
        self.btn_mc_play.clicked.connect(self.func_mc_play)
        self.btn_mc_next.clicked.connect(self.func_mc_next)
        self.btn_mc_previous.clicked.connect(self.func_mc_previous)
        self.combobox_mc_algorithm.currentIndexChanged.connect(self.func_combobox_change)
        # </editor-fold>

    # <editor-fold desc="按钮事件方法">
    # 工具栏函数
    def func_open_matrix(self):
        fileName_choose, filetype = QFileDialog.getOpenFileName(
            self, '选择 numpy 文件', self.NUMPY_PATH, "Numpy Files (*.npy);;Numpy Text (*.txt);;All Files (*)"
        )

        if fileName_choose != '':
            filetype = fileName_choose[fileName_choose.rfind('.') + 1:]
            if filetype == 'npy':
                self.MATRIX_TRIU = np.load(fileName_choose)
            elif filetype == 'txt':
                self.MATRIX_TRIU = np.loadtxt(fileName_choose)
            else:
                self.statusBar().showMessage(f'不支持所选文件：*.{filetype}')
                return
            # 载入矩阵生成参数 若果有
            if os.path.exists(fileName_choose + '.params'):
                params_file = open(fileName_choose + '.params')
                self.edit_points.setText(params_file.readline().split('=')[1].strip())
                self.edit_edges.setText(params_file.readline().split('=')[1].strip())
                if (_seed := params_file.readline().split('=')[1]) != 'None':
                    self.edit_seed.setText(_seed.strip())

            self.ONLY_SHOW_MATRIX_TRIU = True
            self.MATRIX_DIAGONAL = self.MATRIX_TRIU + self.MATRIX_TRIU.T
            self.render_matrix(self.MATRIX_TRIU)
            self.statusBar().showMessage('载入矩阵成功')

    def func_save_matrix(self):
        if self.table_model is not None:
            fileName_choose, filetype = QFileDialog.getSaveFileName(
                self, '保存 numpy 文件，包含随机参数', self.NUMPY_PATH + self.NUMPY_TXT_NAME,
                "Numpy Files (*.npy);;Numpy Text (*.txt);;All Files (*)"
            )

            _m = None
            if self.ONLY_SHOW_MATRIX_TRIU:
                _m = self.MATRIX_TRIU
            else:
                _m = self.MATRIX_DIAGONAL
            if _m is not None:
                if filetype.find('npy') > 0:
                    np.save(fileName_choose, _m)
                    with open(fileName_choose + '.params', 'w') as f:
                        f.write(f'points={self.edit_points.text()}\n')
                        f.write(f'edges={self.edit_edges.text()}\n')
                        f.write(f'random_seed={None if self.edit_seed.text() == "" else self.edit_seed.text()}')
                        self.statusBar().showMessage('文件保存成功')

                elif filetype.find('txt') > 0:
                    # noinspection PyTypeChecker
                    np.savetxt(fileName_choose, _m)
                    with open(fileName_choose + '.params', 'w') as f:
                        f.write(f'points={self.edit_points.text()}\n')
                        f.write(f'edges={self.edit_edges.text()}\n')
                        f.write(f'random_seed={None if self.edit_seed.text() == "" else self.edit_seed.text()}')
                        self.statusBar().showMessage('文件保存成功')
                else:
                    self.statusBar().showMessage(f'不支持所选文件：{fileName_choose}')
            else:
                self.statusBar().showMessage('当前矩阵为空')

    def func_btn_check_able_check(self, btn: QPushButton):
        if btn.text() == '添加节点':
            if self.tool_add_edge.isChecked():
                self.tool_add_edge.toggle()
                self.statusBar().showMessage('添加节点中...')
        else:
            if self.tool_add_circular.isChecked():
                self.tool_add_circular.toggle()
                self.statusBar().showMessage('添加边中...')

    def func_clear_matrix(self):
        """
        清空数据模型 数据表 左侧绘图区
        """
        if self.MATRIX_TRIU is None:
            return

        self.BACKUP_MATRIX_TRIU = self.MATRIX_TRIU.copy()
        self.table_model = None
        self.MATRIX_TRIU = None
        self.MATRIX_DIAGONAL = None
        self.table_view.setModel(None)
        self.circular_pos_dict.clear()
        self.line_list.clear()
        # 清空输入框
        self.clear_edit()

        # 重画 复制到主画布
        self.paint_points_to_temp_pix()
        self.paint_line_between_circular()
        self.pix = self.tempPix.copy()
        self.q_label.setPixmap(self.pix)
        self.statusBar().showMessage('矩阵已清除，画布已清除')

    def func_edit_points_changed(self):
        """
        节点数输入时，更新允许输入的最大边数（属性），同时显示到边数输入框
        """
        if (_p := self.edit_points.text()).isdecimal():
            _p = int(_p)
            self.ALLOW_INPUT_MAX_EDGES = int((_p * _p - _p) / 2)
            self.edit_edges.setPlaceholderText(str(f'max edge is {self.ALLOW_INPUT_MAX_EDGES}'))

    def func_generate_matrix(self):
        """
        生成随机矩阵
        """
        _points = self.edit_points.text()
        _edges = self.edit_edges.text()
        # 随机数种子可以是字符串，但不应是空串，防止每次结果相同
        _seed = self.edit_seed.text()

        if _points.isdecimal() and _edges.isdecimal():
            _points = int(_points)
            _edges = int(_edges)
            self.generate_matrix_by_params(_points, _edges, None if _seed == '' else _seed)
            # 生成完了备份
            self.BACKUP_MATRIX_TRIU = self.MATRIX_TRIU.copy()
            self.render_matrix(self.MATRIX_TRIU)
            self.statusBar().showMessage(f'已使用随机参数：点={_points}，边={_edges}，随机种子={"无" if _seed == "" else _seed}')
        else:
            # 状态栏或对话框提示错误
            self.statusBar().showMessage('随机参数非法，只接受数字')

    def func_checkbox_changed(self):
        """
        只显示对角阵状态改变时
        """
        self.ONLY_SHOW_MATRIX_TRIU = self.only_triu_matrix_checkbox.isChecked()
        # print(self.ONLY_SHOW_MATRIX_TRIU)

    def func_add_circular_in_model(self):
        # 仅做添加行列，应用后再渲染
        # 先插行 再查列 再把光标定位到(0, newCol)
        if not self.table_model:
            self.table_model = QStandardItemModel()

        _rows = self.table_model.rowCount() + 1
        self.table_model.appendRow([QStandardItem('0')] * _rows)
        _rows -= 1
        # 设置行高列宽 字体大小
        self.table_model.setHorizontalHeaderItem(_rows, QStandardItem(str(_rows)))
        self.table_model.setVerticalHeaderItem(_rows, QStandardItem(str(_rows)))
        self.table_model.horizontalHeaderItem(_rows).setFont(self.font_table_header)
        self.table_model.verticalHeaderItem(_rows).setFont(self.font_table_header)

        self.table_view.setRowHeight(_rows, self.TABLE_ROW_HEIGHT)
        self.table_view.setColumnWidth(_rows, self.TABLE_COL_WIDTH)

        # 为新添加的单元格设置字体
        for _r in range(_rows + 1):
            # 行列均相同
            _item = QStandardItem('0')
            _item.setTextAlignment(Qt.AlignCenter)
            _item.setFont(self.font_table)
            self.table_model.setItem(_rows, _r, _item)

            _item_copy = QStandardItem('0')
            _item_copy.setTextAlignment(Qt.AlignCenter)
            _item_copy.setFont(self.font_table)
            self.table_model.setItem(_r, _rows, _item_copy)

        self.statusBar().showMessage(f'已添加新节点 {_rows + 1}')

        # 若是从0到1则渲染
        if _rows == 0:
            _m = np.triu(np.zeros((1, 1)))
            self.MATRIX_TRIU = _m
            self.render_matrix(_m)

    def func_commit_changes(self):
        # 获取tableView数据 即 model数据
        # 只能遍历单元格
        _row = self.table_model.rowCount()
        _col = self.table_model.columnCount()
        _matrix = np.zeros((_row, _col))
        # 实际只需上三角部分
        for _r in range(_row):
            for _c in range(_r + 1, _col):
                _ = self.table_model.item(_r, _c).text()
                if _.isdecimal():
                    _ = int(_)
                    # 大于1的值也认为为1，其余情况为零
                    _ = 1 if _ > 0 else 0
                    _matrix[_r][_c] = _

        # 备份矩阵
        if self.MATRIX_TRIU is not None:
            self.BACKUP_MATRIX_TRIU = self.MATRIX_TRIU.copy()
        # 存入矩阵后渲染
        self.MATRIX_TRIU = _matrix
        self.MATRIX_DIAGONAL = _matrix + _matrix.T
        self.render_matrix(_matrix)
        self.statusBar().showMessage(f'已应用修改，上次矩阵结果已备份')

    def func_cancel_changes(self):
        # 从备份矩阵中恢复，渲染
        _m = self.BACKUP_MATRIX_TRIU
        if _m is None:
            # 非空才可恢复
            self.statusBar().showMessage('备份为空')
            return
        # 从备份恢复 也是拷贝
        self.MATRIX_TRIU = self.BACKUP_MATRIX_TRIU.copy()
        self.render_matrix(_m)
        self.statusBar().showMessage('已从备份中恢复矩阵')

    def func_mc_play(self):
        # 防手贱重复点击
        if not self.btn_mc_play.isCheckable() or self.MC_STEP_MODEL:
            print(self.btn_mc_play.isCheckable())
            self.statusBar().showMessage('不可重复点击/单步模式时不可用')
            return
        # 按钮禁用
        self.btn_mc_play.setCheckable(False)
        # 获取算法名称
        mc_name = self.combobox_mc_algorithm.currentText()
        self.solution_all = []
        self.solution_max = []
        # 算法可以被手动停止标志位
        self.MC_IS_NEED_STOP = False
        _mc = None
        self.mc_prepare()
        # 执行算法 显示结果
        # 循环每个解
        # 备份没有画最大团的画布
        self.backupPix = self.pix.copy()
        for _each_solution in self.solution_all:
            # 恢复画布
            self.pix = self.backupPix.copy()
            # self.q_label.setPixmap(self.pix)
            self.clique_list.clear()
            # 循环每个选择的最大团节点
            for _each_point in _each_solution:
                # 手动停止标志
                if self.MC_IS_NEED_STOP:
                    # 恢复标志
                    self.MC_IS_NEED_STOP = False
                    # 恢复按钮状态
                    self.btn_mc_play.setCheckable(True)
                    return
                # 添加所选点 及所选点之间的连线（若有）到最大团节点列表
                self.clique_list.append(_each_point)
                self.paint_single_point(self.pix, str(_each_point), color='red', broad=4)
                if len(self.clique_list) > 1:
                    self.paint_single_line(self.pix, str(self.clique_list[-2]), str(self.clique_list[-1]), color='red',
                                           broad=4)
                self.q_label.setPixmap(self.pix)
                # 打印所选节点到log
                # self.text_log_edit.append(f'{_each_point} ')
                # 刷新界面 因为for循环占用了线程
                QApplication.processEvents()
                # 延时一秒，动态展示
                time.sleep(1)
            # 打印当前最大团结果 红色
            self.paint_single_line(self.pix, str(self.clique_list[-1]), str(self.clique_list[0]), color='red', broad=4)
            self.q_label.setPixmap(self.pix)
            # 打印log
            _each_solution = [str(_) for _ in _each_solution]
            self.text_log_edit.append(f'当前极大团：{", ".join(_each_solution)}<br>')
            QApplication.processEvents()
            time.sleep(2)
        # 最大团
        self.text_log_edit.append(f'最大团：<font color="red">{", ".join(self.solution_max)}</font><br>')
        # 恢复按钮
        self.statusBar().showMessage('算法执行完成')
        # 恢复画布但不绘制
        self.pix = self.backupPix.copy()
        self.btn_mc_play.setCheckable(True)

    def mc_prepare(self):
        if self.combobox_mc_algorithm.currentText() == 'mc base on bk':
            self.statusBar().showMessage('mc算法执行中')
            self.text_log_edit.setHtml('')
            if self.MATRIX_TRIU is None:
                self.statusBar().showMessage('矩阵为空，无法执行算法')
            self.MATRIX_TRIU = np.triu(self.MATRIX_TRIU)
            self.MATRIX_DIAGONAL = self.MATRIX_TRIU + self.MATRIX_TRIU.T
            _mc = MC(self.MATRIX_DIAGONAL)
            self.solution_all = _mc.search()
            self.solution_max = [str(_) for _ in _mc.solution]
        else:
            # load skip gram model
            model_path = './mc_algorithm/model/'
            for model_file in os.listdir(model_path):
                self.models.append(pickle.load(open(model_path + model_file, 'rb')))

            self.statusBar().showMessage('随机游走路径模型加载完成')

    def func_mc_stop(self):
        # 初始备份画布为空，此时重置会出错
        if self.backupPix.size().width() < 1:
            return
        elif not self.MC_IS_NEED_STOP or self.MC_STEP_MODEL:
            self.MC_IS_NEED_STOP = True
            self.MC_STEP_MODEL = False
            self.pix = self.backupPix.copy()
            self.q_label.setPixmap(self.pix)
            self.statusBar().showMessage('算法已停止，画布已重置')

    def func_mc_next(self):
        if self.combobox_mc_algorithm.currentText() == 'mc base on bk':
            # 准备进入单步模式
            if not self.MC_STEP_MODEL:
                # 进入单步模式
                self.MC_STEP_MODEL = True
                self.mc_prepare()
                # 先画一个点
                self.mc_step_current_point = 0
                self.clique_list = self.solution_all[0]
                self.solution_index = 0
                # 备份
                self.backupPix = self.pix.copy()
                self.paint_single_point(self.pix, str(self.clique_list[0]), color='red', broad=4)
                self.text_log_edit.clear()
                # self.q_label.setPixmap(self.pix)
            else:
                self.mc_step_current_point += 1
                if self.mc_step_current_point > len(self.clique_list):
                    self.mc_step_current_point = 0
                    # 进入下一极大团解集
                    self.solution_index += 1
                    self.clique_list = self.solution_all[self.solution_index]
                    self.pix = self.backupPix.copy()
                    self.paint_single_point(self.pix, str(self.clique_list[0]), color='red', broad=4)

                elif self.mc_step_current_point < len(self.clique_list):
                    self.paint_single_point(self.pix, str(self.clique_list[self.mc_step_current_point]), color='red',
                                            broad=4)
                    self.paint_single_line(self.pix, str(self.clique_list[self.mc_step_current_point - 1]),
                                           str(self.clique_list[self.mc_step_current_point]), color='red', broad=4)
                    # self.q_label.setPixmap(self.pix)
                else:
                    # 最后一个节点的情况，画最后一条边 最后一个节点（上一步已画） -> 第一个节点
                    self.paint_single_line(self.pix, str(self.clique_list[0]),
                                           str(self.clique_list[self.mc_step_current_point - 1]), color='red', broad=4)
                    self.text_log_edit.append(f'极大团：{", ".join([str(_) for _ in self.clique_list])}')
                    # 若当前极大团遍历完
                    if self.solution_index + 1 == len(self.solution_all):
                        # 遍历完成
                        self.statusBar().showMessage('算法单步执行完成')
                        self.text_log_edit.append(
                            f'最大团：<font color="red">{", ".join([str(_) for _ in self.solution_max])}'
                            f'</font>')
                        # 完成单步遍历
                        self.MC_STEP_MODEL = False
                        # 还原画布
                        self.pix = self.backupPix.copy()
                        self.q_label.setPixmap(self.pix)
                        return
        else:
            if not self.MC_STEP_MODEL:
                self.MC_STEP_MODEL = True
                self.mc_step_current_point = 0
                self.mc_prepare()
                self.backupPix = self.pix.copy()
                self.text_log_edit.clear()
                # 随机游走每一步只需画每一个节点及其相似节点
                similar_nodes = self.get_similar_nodes(0, 5, self.models[0])

                for _index, node in enumerate(similar_nodes):
                    if _index == 0:
                        self.paint_single_point(self.pix, '0', color='red', broad=4)
                    else:
                        self.paint_single_point(self.pix, str(node), color='green', broad=4)
                self.text_log_edit.append(
                    f'for node <font color="red">0</font>, '
                    f'the similar <font color="green">{", ".join([str(_) for _ in similar_nodes[1:].tolist()])}</font>')
            else:
                self.mc_step_current_point += 1
                self.mc_step_current_point = self.mc_step_current_point % len(self.MATRIX_DIAGONAL)
                if self.mc_step_current_point < len(self.models):
                    self.pix = self.backupPix.copy()
                    similar_nodes = self.get_similar_nodes(self.mc_step_current_point, 5, self.models[0])

                    for _index, node in enumerate(similar_nodes):
                        if _index == 0:
                            self.paint_single_point(self.pix, str(node), color='red', broad=4)
                        else:
                            self.paint_single_point(self.pix, str(node), color='green', broad=4)
                    self.text_log_edit.append(
                        f'for node <font color="red">{similar_nodes[0]}</font>, '
                        f'the similar <font color="green">{", ".join([str(_) for _ in similar_nodes[1:].tolist()])}</font>')
                else:
                    self.MC_STEP_MODEL = False
                    self.pix = self.backupPix.copy()
                    self.statusBar().showMessage('随机游走节点遍历完成')
        self.q_label.setPixmap(self.pix)

    def func_mc_previous(self):
        if self.combobox_mc_algorithm.currentText() == 'mc base on bk':
            if not self.MC_STEP_MODEL:
                self.statusBar().showMessage('单步执行未开始')
                return
            # 恢复画布
            self.MC_STEP_MODEL = True
            self.pix = self.backupPix.copy()
            # 需要回退到上一极大团
            if self.mc_step_current_point == 0:
                if self.solution_index == 0:
                    self.statusBar().showMessage('当前为第一个极大团，无法回退')
                    self.MC_STEP_MODEL = False
                    return
                else:
                    self.solution_index -= 1
                    self.clique_list = self.solution_all[self.solution_index]
                    self.mc_step_current_point = len(self.clique_list)
                    self.statusBar().showMessage('回退到上一最大团')

            # 还在当前极大团遍历，直接回退
            elif self.mc_step_current_point <= len(self.clique_list):
                self.mc_step_current_point -= 1
                self.statusBar().showMessage('回退一步')

            # 画图 若当前遍历的节点数 和极大团节点数相等 则只画前len个
            for _i in range(self.mc_step_current_point if self.mc_step_current_point == len(
                    self.clique_list) else self.mc_step_current_point + 1):
                self.paint_single_point(self.pix, str(self.clique_list[_i]), color='red', broad=4)
                if _i > 0:
                    self.paint_single_line(self.pix, str(self.clique_list[_i - 1]), str(self.clique_list[_i]),
                                           color='red',
                                           broad=4)
            # 最后一条边
            if self.mc_step_current_point == len(self.clique_list):
                self.paint_single_line(self.pix, str(self.clique_list[self.mc_step_current_point - 1]),
                                       str(self.clique_list[0]), color='red', broad=4)

        else:
            if not self.MC_STEP_MODEL:
                self.statusBar().showMessage('单步执行未开始')
                return

            self.pix = self.backupPix.copy()
            self.mc_step_current_point -= 1
            if self.mc_step_current_point >= 0:
                similar_nodes = self.get_similar_nodes(self.mc_step_current_point, 5, self.models[0])

                for _index, node in enumerate(similar_nodes):
                    if _index == 0:
                        self.paint_single_point(self.pix, '0', color='red', broad=4)
                    else:
                        self.paint_single_point(self.pix, str(node), color='green', broad=4)
                self.text_log_edit.append(
                    f'for node <font color="red">{similar_nodes[0]}</font>, '
                    f'the similar <font color="green">{", ".join([str(_) for _ in similar_nodes[1:].tolist()])}</font>')
            # else:
            #     QPainter(self).drawPixmap()

        self.q_label.setPixmap(self.pix)

    def func_combobox_change(self):
        if self.combobox_mc_algorithm.currentText() == 'random walk algorithm':
            self.btn_mc_play.setEnabled(False)
        else:
            self.btn_mc_play.setEnabled(True)
    # </editor-fold>

    def generate_matrix_by_params(self, p: int, e: int, seed: str):
        # 生成全零矩阵
        # 指定数据类型为int8
        m = np.zeros((p, p), dtype=np.int8)
        # 准备随机序列 前e个1，后补零
        e_list = [1] * e + [0] * (self.ALLOW_INPUT_MAX_EDGES - e)
        # 随机数种子
        if None is not seed:
            random.seed(seed)

        # 打乱随机序列
        random.shuffle(e_list)

        for _r in range(p):
            for _c in range(_r + 1, p):
                # pop 是取最后一个元素
                m[_r][_c] = e_list.pop()

        # 矩阵取整
        # m = np.ceil(m)

        self.MATRIX_TRIU = m
        self.MATRIX_DIAGONAL = m + m.T

    def render_matrix(self, aj_matrix: np.array = None):
        if aj_matrix is None:
            # 无参数测试矩阵, 非对称
            _m = np.load('./numpy_file/presentation_matrix.npy')
            # aj_matrix = np.array([
            #     [0, 1, 1, 1, 1, 0],
            #     [1, 0, 1, 1, 1, 1],
            #     [1, 1, 0, 1, 1, 1],
            #     [1, 1, 1, 0, 1, 1],
            #     [1, 1, 1, 1, 0, 0],
            #     [0, 1, 1, 1, 0, 0]], dtype=np.int8)
            aj_matrix = np.array(_m, dtype=np.int8)
            self.MATRIX_TRIU = aj_matrix
            self.MATRIX_DIAGONAL = aj_matrix + aj_matrix.T

        elif self.ONLY_SHOW_MATRIX_TRIU:
            aj_matrix = self.MATRIX_TRIU
        else:
            self.MATRIX_DIAGONAL = self.MATRIX_TRIU + self.MATRIX_TRIU.T
            aj_matrix = self.MATRIX_DIAGONAL

        aj_matrix = np.array(aj_matrix, np.int8)

        self.POINTS_NUM = len(aj_matrix)
        # 当前点数 + 1
        self.MAX_POINTS_NUM = self.POINTS_NUM + 1

        # 生成数据模型 -> 数据表
        self.table_model = QStandardItemModel(self.POINTS_NUM, self.POINTS_NUM)
        self.table_model.setHorizontalHeaderLabels([str(x) for x in range(self.POINTS_NUM)])
        self.table_model.setVerticalHeaderLabels([str(x) for x in range(self.POINTS_NUM)])

        for _c in range(self.POINTS_NUM):
            self.table_model.horizontalHeaderItem(_c).setFont(self.font_table_header)
            self.table_model.verticalHeaderItem(_c).setFont(self.font_table_header)

        for row in range(len(aj_matrix)):
            for col in range(len(aj_matrix[row])):
                item = QStandardItem(str(aj_matrix[row][col]))
                item.setTextAlignment(Qt.AlignCenter)
                item.setFont(self.font_table)
                self.table_model.setItem(row, col, item)

        # 数据表格
        self.table_view.setModel(self.table_model)
        for _ in range(self.POINTS_NUM):
            self.table_view.setRowHeight(_, self.TABLE_ROW_HEIGHT)
            self.table_view.setColumnWidth(_, self.TABLE_COL_WIDTH)

        # 清空之前的点 边信息
        self.circular_pos_dict.clear()
        self.line_list.clear()
        # 加载节点坐标，边信息
        temp_pos_dict, self.line_list = get_position(self.PIX_WIDTH - 100, self.PIX_HEIGHT - 100, aj_matrix)

        for _id, _tp in temp_pos_dict.items():
            self.circular_pos_dict[str(_id)] = QPoint(_tp[0], _tp[1])

        self.draw_tag = 'draw_matrix'

    def paint_points_to_temp_pix(self):
        """
        根据点列重绘图
        """
        self.tempPix = QPixmap(self.PIX_WIDTH, self.PIX_HEIGHT)
        self.tempPix.fill(Qt.white)

        # pp = QPainter(self.tempPix)
        # pp.begin(self)
        # pp.setPen(QPen(Qt.black, 2, Qt.SolidLine))
        # pp.setFont(self.font_num)
        # for _pid, c in self.circular_pos_dict.items():
        #     pp.drawEllipse(c, self.CIRCULAR_RADIUS, self.CIRCULAR_RADIUS)
        #     if len(_pid) < 2:
        #         pp.drawText(round(c.x() - self.CIRCULAR_RADIUS / 3), round(c.y() + self.CIRCULAR_RADIUS / 2), _pid)
        #     else:
        #         pp.drawText(round(c.x() - self.CIRCULAR_RADIUS / 1.3), round(c.y() + self.CIRCULAR_RADIUS / 2), _pid)
        # pp.end()
        for k in self.circular_pos_dict.keys():
            self.paint_single_point(self.tempPix, k)
            # QApplication.processEvents()

        # painter = QPainter(self)
        # painter.drawPixmap(10, 10, self.tempPix)

    def paint_single_point(self, pix: QPixmap, p_id: str, color: str = 'black', broad: int = 2):
        pp = QPainter(pix)
        pp.begin(self)
        pen_color = {'black': Qt.black, 'red': Qt.red, 'green': QColor(112, 173, 71)}.get(color)
        pp.setPen(QPen(pen_color, broad, Qt.SolidLine))
        pp.setFont(self.font_num)
        c = self.circular_pos_dict[p_id]
        pp.drawEllipse(c, self.CIRCULAR_RADIUS, self.CIRCULAR_RADIUS)
        if len(p_id) < 2:
            pp.drawText(round(c.x() - self.CIRCULAR_RADIUS / 3), round(c.y() + self.CIRCULAR_RADIUS / 2), p_id)
        else:
            pp.drawText(round(c.x() - self.CIRCULAR_RADIUS / 1.3), round(c.y() + self.CIRCULAR_RADIUS / 2), p_id)
        pp.end()

    def paint_line_between_circular(self):
        # pp = QPainter(self.tempPix)
        # pp.begin(self)
        for line in self.line_list:
            # p1 = self.circular_pos_dict[str(line[0])]
            # p2 = self.circular_pos_dict[str(line[1])]
            #
            # pp.setPen(QPen(Qt.black, 2, Qt.SolidLine))
            # p1, p2 = self.calc_line_point(p1, p2)
            # pp.drawLine(p1, p2)
            self.paint_single_line(self.tempPix, str(line[0]), str(line[1]))

        # pp.end()
        # painter = QPainter(self)
        # painter.drawPixmap(10, 10, self.tempPix)

    def paint_single_line(self, pix: QPixmap, p1_id: str, p2_id: str, color: str = 'black', broad: int = 2):
        pp = QPainter(pix)
        pp.begin(self)
        p1 = self.circular_pos_dict[p1_id]
        p2 = self.circular_pos_dict[p2_id]
        pen_color = Qt.black if color == 'black' else Qt.red
        pp.setPen(QPen(pen_color, broad, Qt.SolidLine))
        p1, p2 = self.calc_line_point(p1, p2)
        pp.drawLine(p1, p2)
        pp.end()

    def calc_line_point(self, p1: QPoint, p2: QPoint):
        """
        计算两圆心坐标之间的连线，两端减掉半径
        :return:
        """
        radius = self.CIRCULAR_RADIUS

        x1 = p1.x()
        y1 = p1.y()
        x2 = p2.x()
        y2 = p2.y()

        if x1 - x2 == 0:
            if y1 > y2:
                y1 -= radius
                y2 += radius
            else:
                y1 += radius
                y2 -= radius

        elif y1 - y2 == 0:
            if x1 > x2:
                x1 -= radius
                x2 += radius
            else:
                x1 += radius
                x2 -= radius

        else:
            k = (y1 - y2) / (x1 - x2)
            r_cos = radius * 1 / math.sqrt(k ** 2 + 1)
            r_sin = radius * k / math.sqrt(k ** 2 + 1)
            if x1 < x2:
                if y1 > y2:
                    x1 += r_cos
                    y1 -= abs(abs(r_sin))
                    x2 -= r_cos
                    y2 += abs(abs(r_sin))
                else:
                    x1 += r_cos
                    y1 += abs(r_sin)
                    x2 -= r_cos
                    y2 -= abs(r_sin)

            else:
                if y1 > y2:
                    x1 -= r_cos
                    y1 -= abs(r_sin)
                    x2 += r_cos
                    y2 += abs(r_sin)
                else:
                    x1 -= r_cos
                    y1 += abs(r_sin)
                    x2 += r_cos
                    y2 -= abs(r_sin)

        p1 = QPointF(x1, y1)

        p2 = QPointF(x2, y2)

        return p1, p2

    def delete_lines(self, point_id):
        """
        删除和point_id有关的所有连线
        :param point_id: 待删除的线的一端的点 id
        :return: None
        """
        # 清空临时保存的移动时的点的边集
        self.temp_moving_point_line.clear()
        _temp_list = list()
        for _line in self.line_list:
            if int(point_id) not in _line:
                _temp_list.append(_line)
            else:
                self.temp_moving_point_line.append(_line)
        self.line_list = _temp_list

    def paintEvent(self, event):
        if 'circular' == self.draw_tag:
            pp = QPainter(self.pix)
            pp.begin(self)
            pp.setPen(QPen(Qt.black, 2, Qt.SolidLine))
            pp.drawEllipse(self.lastPoint, self.CIRCULAR_RADIUS, self.CIRCULAR_RADIUS)
            pp.end()

            # 重绘之前的全部内容
            # painter = QPainter(self)
            # painter.drawPixmap(10, 10, self.pix)
            self.q_label.setPixmap(self.pix)

        elif 'move_circular' == self.draw_tag:
            # 如果正在绘图，就在辅助画布上绘制
            if self.isDrawing:
                # 复制以前pix画布中的内容到tempPix中，移动时的绘制在辅助画布上
                # print('moving circular')
                self.pix = self.tempPix.copy()
                pp = QPainter(self.pix)
                pp.setPen(QPen(Qt.black, 2, Qt.SolidLine))
                pp.drawEllipse(self.lastPoint, self.CIRCULAR_RADIUS, self.CIRCULAR_RADIUS)
                pp.end()
                self.lastPoint = self.endPoint

                # 重绘之前的全部内容
                # painter = QPainter(self)
                # painter.drawPixmap(10, 10, self.pix)
                self.q_label.setPixmap(self.pix)
            else:
                if not self.isSavePix:
                    # 取消本次移动，恢复主画布
                    self.pix = self.backupPix.copy()
                    # 重绘之前的全部内容
                    # painter = QPainter(self)
                    # painter.drawPixmap(10, 10, self.pix)
                    self.q_label.setPixmap(self.pix)
                else:
                    # 先在辅助画布上（去除待移动点后的结果）添加新点
                    self.paint_points_to_temp_pix()
                    self.paint_line_between_circular()
                    # 保存本次绘制结果到主画布pix
                    self.pix = self.tempPix.copy()
                    self.q_label.setPixmap(self.pix)

                self.isSavePix = False

        elif 'draw_matrix' == self.draw_tag:
            self.paint_points_to_temp_pix()
            self.paint_line_between_circular()

            # 将辅助画布的内容复制到主画布上
            self.pix = self.tempPix.copy()
            self.q_label.setPixmap(self.pix)

        # 重置绘画标签
        self.draw_tag = 'nothing'

    def mousePressEvent(self, event):
        # 若是添加节点状态，添加完也可移动 it works!
        if event.button() == Qt.LeftButton:
            self.lastPoint = QPoint(event.pos().x() - self.MOUSE_BIAS_X, event.pos().y() - self.MOUSE_BIAS_Y)
            # 添加边状态只需记录下点击位置，但需要避免与移动点冲突
            if self.tool_add_edge.isChecked():
                pass
            else:
                # 添加节点状态
                if self.tool_add_circular.isChecked():
                    # self.lastPoint = QPoint(event.pos().x() - self.MOUSE_BIAS_X, event.pos().y() - self.MOUSE_BIAS_Y)
                    if not self.__is_new_circular_exist(self.lastPoint):
                        self.circular_pos_dict[str(self.MAX_POINTS_NUM)] = self.lastPoint
                        self.MAX_POINTS_NUM += 1
                        self.draw_tag = 'circular'
                        self.update()

                        # 更新model状态
                        self.func_add_circular_in_model()

                # 选中点时精确判断
                if point_id := self.__is_new_circular_exist(self.lastPoint, exact=True):
                    # 按下位置有圆才能移动
                    self.draw_tag = 'move_circular'
                    self.isDrawing = True
                    # 记录正在移动的点的 id
                    self.moving_point_id = point_id
                    # self.isCanMove = True
                    # 备份主画布
                    self.backupPix = self.pix.copy()
                    # 备份点列
                    self.backup_pos_dict = self.circular_pos_dict.copy()
                    # 备份边列
                    self.backup_line_list = self.line_list.copy()
                    # 移除选中的点
                    self.circular_pos_dict.pop(point_id)
                    self.delete_lines(point_id)
                    # 将当前去除待移动点的点列重新绘制到tempPix上，作为本次移动时绘制的基本画布
                    self.paint_points_to_temp_pix()
                    self.paint_line_between_circular()

    def mouseMoveEvent(self, event):
        if self.isDrawing:
            self.endPoint = QPoint(event.pos().x() - self.MOUSE_BIAS_X, event.pos().y() - self.MOUSE_BIAS_Y)
            self.draw_tag = 'move_circular'
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.endPoint = QPoint(event.pos().x() - self.MOUSE_BIAS_X, event.pos().y() - self.MOUSE_BIAS_Y)
            if self.isDrawing:
                self.draw_tag = 'move_circular'
                self.isDrawing = False
                # self.isCanMove = False
                if self.__is_new_circular_exist(self.endPoint):
                    # 鼠标释放位置存在圆，则恢复
                    self.pix = self.backupPix.copy()
                    self.circular_pos_dict = self.backup_pos_dict.copy()
                    self.line_list = self.backup_line_list.copy()
                else:
                    # 保存绘制结果
                    self.isSavePix = True
                    # 最终点添加到点列
                    self.circular_pos_dict[self.moving_point_id] = self.endPoint
                    # 恢复边集
                    self.line_list += self.temp_moving_point_line

            elif self.tool_add_edge.isChecked():
                # 在按下添加边按钮时释放鼠标，精确找点
                if (p_start := self.__is_new_circular_exist(self.lastPoint, exact=True)) \
                        and (p_end := self.__is_new_circular_exist(self.endPoint, exact=True)):
                    p_start = int(p_start)
                    # noinspection all
                    p_end = int(p_end)

                    if p_start > p_end:
                        _ = p_start
                        p_start = p_end
                        p_end = _

                    self.line_list.append((p_start, p_end))
                    # 借用画节点完成后的保存操作
                    self.draw_tag = 'move_circular'
                    # 保存绘制结果
                    self.isSavePix = True

                    # 更新model中的边信息
                    item = QStandardItem('1')
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFont(self.font_table)
                    self.table_model.setItem(p_start, p_end, item)

            # 更新移动后的结果
            self.update()

    def mouseDoubleClickEvent(self, event):
        pass
        # 不使用双击添加点
        # if event.button() == Qt.MouseEventCreatedDoubleClick:
        #     self.lastPoint = QPoint(event.pos().x() - self.MOUSE_BIAS_X, event.pos().y() - self.MOUSE_BIAS_Y)
        #     if not self.__is_new_circular_exist(self.lastPoint):
        #         self.circular_pos_dict[str(self.MAX_POINTS_NUM)] = self.lastPoint
        #         self.MAX_POINTS_NUM += 1
        #         self.draw_tag = 'circular'
        #         self.update()

    def __is_new_circular_exist(self, _n: QPoint, exact=False):
        """
        判断新加的圆是否存在于已有的圆中，新圆心在已有的某个圆半径内
        为防止重叠，判断两倍半径
        :param
            n: 待判定的点
        :return: None 不存在 k 已存在的点的 id key
        """
        for k, c in self.circular_pos_dict.items():
            radius = self.CIRCULAR_RADIUS
            if not exact:
                radius *= 2
            if radius >= self.__euclidean_distance(_n.x(), _n.y(), c.x(), c.y()):
                return k
        return None

    @staticmethod
    def __euclidean_distance(x1, y1, x2, y2):
        """
        计算两点之间的欧氏距离
        :return: 欧氏距离
        """
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    def clear_edit(self):
        self.edit_seed.clear()
        self.edit_edges.clear()
        # 清空提示信息
        self.edit_edges.setPlaceholderText(None)
        self.edit_points.clear()

    def center(self):
        desktop = QApplication.desktop()
        self.setGeometry((desktop.width() - self.WINDOW_WIDTH) // 2, (desktop.height() - self.WINDOW_HEIGHT) // 2,
                         self.WINDOW_WIDTH, self.WINDOW_HEIGHT)

    def get_similar_nodes(self, query_node, k, W):
        # 随机游走模型取前k个相似节点
        # W = embed.numpy()
        # saved model not need .numpy()
        # w is a list of center node vector
        x = W[query_node]
        # get query_node's representation
        cos = np.dot(W, x) / np.sqrt(np.sum(W * W, axis=1) * np.sum(x * x) + 1e-9)
        # to mult every node and to avoid zero sep
        flatten = cos.flatten()
        # return collaps into one dimension
        indices = np.argpartition(flatten, -k)[-k:]
        # sort to less k element
        indices = indices[np.argsort(-flatten[indices])]
        # result = dict()
        # indices_list = list()
        for i in indices:
            print(f'for node {query_node}, the similar {i}')
        return indices

    def fun_win_max_or_recv(self) -> None:
        if not self.isMaximized():
            desktop = QApplication.desktop()
            self.WINDOW_WIDTH = desktop.width()
            self.WINDOW_HEIGHT = desktop.height()
            self.PIX_WIDTH = round(self.WINDOW_WIDTH * 0.7)
            self.PIX_HEIGHT = self.WINDOW_HEIGHT - 50

            print(desktop.width())
            self.MOUSE_BIAS_Y = 0
        else:
            self.WINDOW_WIDTH = 1700
            self.WINDOW_HEIGHT = round(self.WINDOW_WIDTH / 1.8888888)
            self.PIX_WIDTH = round(self.WINDOW_WIDTH * 0.7)
            self.PIX_HEIGHT = self.WINDOW_HEIGHT - 50

            print('reset size')
            self.MOUSE_BIAS_Y = 40


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mdw = MainDrawWindow()
    sys.exit(app.exec_())
