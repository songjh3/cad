# CAD看图工具

一个轻量级的CAD文件查看工具，支持DWG和DXF格式。

## 功能特性

- ✅ 支持DWG和DXF文件格式
- ✅ 拖拽打开文件
- ✅ 鼠标滚轮缩放
- ✅ 鼠标左键拖拽平移
- ✅ 图层列表显示
- ✅ 深色主题界面
- ✅ 工具栏快捷操作

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行程序

```bash
python cad_viewer.py
```

或者直接拖拽DWG/DXF文件到程序窗口打开。

## 打包成exe

```bash
# 使用spec文件打包
pyinstaller cad_viewer.spec

# 或者使用命令行打包
pyinstaller --onefile --windowed --name "CAD看图工具" cad_viewer.py
```

打包后的exe文件在 `dist` 目录下。

## 使用方法

1. **打开文件**: 点击工具栏"打开文件"按钮，或直接拖拽DWG/DXF文件到窗口
2. **缩放**: 使用鼠标滚轮或工具栏的放大/缩小按钮
3. **平移**: 按住鼠标左键拖动
4. **适应窗口**: 点击工具栏"适应窗口"按钮恢复默认视图

## 快捷键

- `Ctrl+O`: 打开文件
- `Ctrl++`: 放大
- `Ctrl+-`: 缩小
- `Ctrl+0`: 适应窗口

## 技术栈

- Python 3.x
- PyQt5: GUI界面
- ezdxf: DWG/DXF文件读取
- matplotlib: 图形渲染
- PyInstaller: 打包工具

## 注意事项

- 首次打包可能需要较长时间
- exe文件大小约50-100MB（包含所有依赖）
- 支持Windows 7及以上系统
