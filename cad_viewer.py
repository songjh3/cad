"""
CAD看图工具 - 主程序
支持DWG/DXF文件查看，可拖拽打开文件
"""
import sys
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QLabel,
                             QScrollArea, QMessageBox, QToolBar, QAction,
                             QStatusBar, QSplitter, QListWidget, QListWidgetItem,
                             QProgressDialog)
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QThread, pyqtSignal as Signal
from PyQt5.QtGui import QPainter, QPixmap, QPen, QColor, QWheelEvent, QTransform
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO


class ODAConverter:
    """获取ODA File Converter路径并执行转换"""
    
    @staticmethod
    def find_oda_converter():
        """查找ODA File Converter安装路径"""
        possible_paths = [
            r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
            r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
            r"C:\ODA\ODAFileConverter\ODAFileConverter.exe",
        ]
        
        # 检查常见安装路径
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 在PATH环境变量中查找
        try:
            result = subprocess.run(
                ['where', 'ODAFileConverter.exe'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
        except:
            pass
        
        return None
    
    @staticmethod
    def convert_dwg_to_dxf(dwg_path, output_dir=None):
        """
        使用ODA File Converter将DWG转换为DXF
        
        Args:
            dwg_path: DWG文件路径
            output_dir: 输出目录，如果为None则使用临时目录
            
        Returns:
            转换后的DXF文件路径，失败返回None
        """
        oda_path = ODAConverter.find_oda_converter()
        if not oda_path:
            return None
        
        try:
            # 创建临时目录
            if output_dir is None:
                output_dir = tempfile.mkdtemp(prefix='cad_temp_')
            else:
                os.makedirs(output_dir, exist_ok=True)
            
            # 获取输入文件信息
            dwg_file = Path(dwg_path)
            input_dir = str(dwg_file.parent)
            
            # ODA File Converter命令行参数
            # 语法: ODAFileConverter.exe <input_folder> <output_folder> <output_version> <output_format> [options]
            cmd = [
                oda_path,
                input_dir,           # 输入文件夹
                output_dir,          # 输出文件夹
                'ACAD2018',          # 输出版本
                'DXF',               # 输出格式
                '0',                 # 递归子目录 (0=否)
                '1',                 # 审计信息 (1=是)
                dwg_file.name        # 指定要转换的文件
            ]
            
            # 执行转换
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2分钟超时
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # 查找输出的DXF文件
            dxf_name = dwg_file.stem + '.dxf'
            dxf_path = os.path.join(output_dir, dxf_name)
            
            if os.path.exists(dxf_path):
                return dxf_path
            else:
                return None
                
        except Exception as e:
            print(f"ODA转换错误: {e}")
            return None


class CADCanvas(QLabel):
    """CAD绘图画布，支持缩放和平移"""
    
    def __init__(self):
        super().__init__()
        self.setMinimumSize(800, 600)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #1e1e1e; border: 1px solid #3e3e3e;")
        self.setAcceptDrops(True)
        
        self.original_pixmap = None
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.last_pos = None
        
    def set_drawing(self, pixmap):
        """设置图纸"""
        self.original_pixmap = pixmap
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.update_display()
        
    def update_display(self):
        """更新显示"""
        if self.original_pixmap:
            scaled_pixmap = self.original_pixmap.scaled(
                int(self.original_pixmap.width() * self.scale_factor),
                int(self.original_pixmap.height() * self.scale_factor),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)
            
    def wheelEvent(self, event: QWheelEvent):
        """鼠标滚轮缩放"""
        if self.original_pixmap:
            delta = event.angleDelta().y()
            if delta > 0:
                self.scale_factor *= 1.1
            else:
                self.scale_factor *= 0.9
            self.scale_factor = max(0.1, min(10.0, self.scale_factor))
            self.update_display()
            
    def mousePressEvent(self, event):
        """鼠标按下"""
        if event.button() == Qt.LeftButton:
            self.last_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            
    def mouseReleaseEvent(self, event):
        """鼠标释放"""
        if event.button() == Qt.LeftButton:
            self.last_pos = None
            self.setCursor(Qt.ArrowCursor)
            
    def mouseMoveEvent(self, event):
        """鼠标移动平移"""
        if self.last_pos and self.original_pixmap:
            delta = event.pos() - self.last_pos
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self.last_pos = event.pos()


class CADViewer(QMainWindow):
    """CAD看图工具主窗口"""
    
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.doc = None
        self.init_ui()
        
        # 检查命令行参数
        if len(sys.argv) > 1:
            file_path = sys.argv[1]
            if os.path.exists(file_path) and file_path.lower().endswith(('.dwg', '.dxf')):
                self.open_file(file_path)
        
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("CAD看图工具")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧图层列表
        self.layer_list = QListWidget()
        self.layer_list.setMaximumWidth(200)
        self.layer_list.itemChanged.connect(self.toggle_layer)
        splitter.addWidget(self.layer_list)
        
        # 右侧画布
        self.canvas = CADCanvas()
        self.canvas.setAcceptDrops(True)
        splitter.addWidget(self.canvas)
        
        splitter.setStretchFactor(1, 1)
        
        # 主布局
        layout = QVBoxLayout()
        layout.addWidget(splitter)
        central_widget.setLayout(layout)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
        # 启用拖拽
        self.setAcceptDrops(True)
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # 打开文件
        open_action = QAction("打开文件", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file_dialog)
        toolbar.addAction(open_action)
        
        toolbar.addSeparator()
        
        # 放大
        zoom_in_action = QAction("放大", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)
        
        # 缩小
        zoom_out_action = QAction("缩小", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)
        
        # 适应窗口
        fit_action = QAction("适应窗口", self)
        fit_action.setShortcut("Ctrl+0")
        fit_action.triggered.connect(self.fit_to_window)
        toolbar.addAction(fit_action)
        
        toolbar.addSeparator()
        
        # 关于
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        toolbar.addAction(about_action)
        
    def dragEnterEvent(self, event):
        """拖拽进入"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        """拖拽放下"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            file_path = files[0]
            if file_path.lower().endswith(('.dwg', '.dxf')):
                self.open_file(file_path)
            else:
                QMessageBox.warning(self, "错误", "请拖入DWG或DXF文件！")
                
    def open_file_dialog(self):
        """打开文件对话框"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "打开CAD文件", 
            "", 
            "CAD文件 (*.dwg *.dxf);;所有文件 (*.*)"
        )
        if file_path:
            self.open_file(file_path)
            
    def open_file(self, file_path):
        """打开CAD文件"""
        try:
            self.statusBar.showMessage(f"正在加载: {os.path.basename(file_path)}...")
            QApplication.processEvents()
            
            # 检查文件格式
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.dwg':
                # DWG格式需要特殊处理
                try:
                    # 尝试直接读取（ezdxf 1.1+支持部分DWG）
                    self.doc = ezdxf.readfile(file_path)
                except Exception as dwg_error:
                    # 直接读取失败，尝试使用ODA转换
                    self.statusBar.showMessage("检测到较高版本DWG，正在尝试自动转换...")
                    QApplication.processEvents()
                    
                    dxf_path = self.try_auto_convert_dwg(file_path, str(dwg_error))
                    if dxf_path:
                        # 转换成功，打开DXF文件
                        self.doc = ezdxf.readfile(dxf_path)
                        self.statusBar.showMessage("自动转换成功，正在渲染...")
                        QApplication.processEvents()
                    else:
                        # 转换失败
                        return
            else:
                # DXF格式直接读取
                self.doc = ezdxf.readfile(file_path)
            
            self.current_file = file_path
            
            # 渲染图纸
            self.render_drawing()
            
            # 更新图层列表
            self.update_layer_list()
            
            self.statusBar.showMessage(f"已打开: {os.path.basename(file_path)}")
            self.setWindowTitle(f"CAD看图工具 - {os.path.basename(file_path)}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件:\n{str(e)}")
            self.statusBar.showMessage("打开文件失败")
    
    def try_auto_convert_dwg(self, dwg_path, error_msg):
        """尝试自动转换DWG文件"""
        # 检查是否安装了ODA File Converter
        oda_path = ODAConverter.find_oda_converter()
        
        if not oda_path:
            # 未安装ODA，显示提示
            error_msg = (
                f"无法直接读取DWG文件。\n\n"
                f"原因：{error_msg}\n\n"
                f"解决方案：\n"
                f"1. 安装ODA File Converter实现自动转换\n"
                f"   下载地址: https://www.opendesign.com/guestfiles/oda_file_converter\n\n"
                f"2. 手动将DWG转换为DXF格式\n\n"
                f"3. 使用DWG版本较低的文件（R2000-R2018）\n\n"
                f"提示：本工具完美支持DXF格式文件"
            )
            QMessageBox.warning(self, "DWG格式限制", error_msg)
            self.statusBar.showMessage("DWG文件打开失败")
            return None
        
        # 已安装ODA，询问是否转换
        reply = QMessageBox.question(
            self,
            "自动转换DWG文件",
            f"无法直接读取该DWG文件（可能是较高版本）。\n\n"
            f"检测到已安装ODA File Converter，\n"
            f"是否自动转换为DXF格式后打开？\n\n"
            f"转换过程可能需要几秒钟...",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.No:
            self.statusBar.showMessage("用户取消转换")
            return None
        
        # 显示进度对话框
        progress = QProgressDialog("正在转换DWG文件...", "取消", 0, 0, self)
        progress.setWindowTitle("请稍候")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        QApplication.processEvents()
        
        try:
            # 执行转换
            dxf_path = ODAConverter.convert_dwg_to_dxf(dwg_path)
            progress.close()
            
            if dxf_path and os.path.exists(dxf_path):
                QMessageBox.information(
                    self,
                    "转换成功",
                    f"已自动将DWG转换为DXF格式！\n\n"
                    f"转换后的文件保存在：\n{dxf_path}\n\n"
                    f"现在将打开转换后的文件..."
                )
                return dxf_path
            else:
                progress.close()
                QMessageBox.warning(
                    self,
                    "转换失败",
                    f"自动转换失败，请尝试：\n\n"
                    f"1. 手动使用ODA File Converter转换\n"
                    f"2. 使用AutoCAD将DWG另存为DXF\n"
                    f"3. 使用在线转换工具"
                )
                return None
                
        except Exception as e:
            progress.close()
            QMessageBox.critical(
                self,
                "转换错误",
                f"转换过程出错：\n{str(e)}"
            )
            return None
            
    def render_drawing(self):
        """渲染图纸"""
        if not self.doc:
            return
            
        try:
            # 创建matplotlib后端
            fig = plt.figure(figsize=(12, 9), dpi=100)
            ax = fig.add_axes([0, 0, 1, 1])
            ctx = RenderContext(self.doc)
            out = MatplotlibBackend(ax)
            Frontend(ctx, out).draw_layout(self.doc.modelspace(), finalize=True)
            
            # 设置样式
            ax.set_aspect('equal')
            ax.axis('off')
            fig.patch.set_facecolor('#1e1e1e')
            
            # 转换为QPixmap
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', 
                       facecolor='#1e1e1e', edgecolor='none')
            buf.seek(0)
            plt.close(fig)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buf.read())
            self.canvas.set_drawing(pixmap)
            
        except Exception as e:
            QMessageBox.warning(self, "渲染警告", f"渲染图纸时出现问题:\n{str(e)}")
            
    def update_layer_list(self):
        """更新图层列表"""
        self.layer_list.clear()
        if not self.doc:
            return
            
        try:
            layers = self.doc.layers
            for layer in layers:
                item = QListWidgetItem(layer.dxf.name)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.layer_list.addItem(item)
        except:
            pass
            
    def toggle_layer(self, item):
        """切换图层显示"""
        # 这里可以实现图层的显示/隐藏功能
        pass
        
    def zoom_in(self):
        """放大"""
        self.canvas.scale_factor *= 1.2
        self.canvas.update_display()
        
    def zoom_out(self):
        """缩小"""
        self.canvas.scale_factor /= 1.2
        self.canvas.update_display()
        
    def fit_to_window(self):
        """适应窗口"""
        self.canvas.scale_factor = 1.0
        self.canvas.offset_x = 0
        self.canvas.offset_y = 0
        self.canvas.update_display()
        
    def show_about(self):
        """关于对话框"""
        QMessageBox.about(
            self,
            "关于CAD看图工具",
            "CAD看图工具 v1.0\n\n"
            "支持DWG和DXF文件查看\n"
            "功能：\n"
            "- 拖拽打开文件\n"
            "- 鼠标滚轮缩放\n"
            "- 鼠标拖拽平移\n"
            "- 图层管理\n\n"
            "使用ezdxf库开发"
        )


def main():
    """主程序入口"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置深色主题
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
        }
        QToolBar {
            background-color: #3c3c3c;
            border: none;
            padding: 5px;
        }
        QToolBar QToolButton {
            background-color: #3c3c3c;
            color: #ffffff;
            border: none;
            padding: 8px;
            margin: 2px;
        }
        QToolBar QToolButton:hover {
            background-color: #4c4c4c;
        }
        QStatusBar {
            background-color: #007acc;
            color: white;
        }
        QListWidget {
            background-color: #252526;
            color: #cccccc;
            border: 1px solid #3e3e3e;
        }
        QListWidget::item:hover {
            background-color: #2a2d2e;
        }
        QListWidget::item:selected {
            background-color: #094771;
        }
    """)
    
    viewer = CADViewer()
    viewer.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
