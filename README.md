# CAD看图工具

一个轻量级的CAD文件查看工具，支持DWG和DXF格式。

## 功能特性

- ✅ **完美支持DXF格式**
- ⚠️ **部分支持DWG格式**（见下方说明）
- ✅ 拖拽打开文件
- ✅ 鼠标滚轮缩放
- ✅ 鼠标左键拖拽平移
- ✅ 图层列表显示
- ✅ 深色主题界面
- ✅ 工具栏快捷操作

## DWG文件支持说明

### 为什么DWG支持有限？

DWG是Autodesk的专有二进制格式，完整支持需要商业授权。本工具使用的ezdxf库：
- ✅ **完美支持DXF格式**（所有版本）
- ⚠️ **有限支持DWG格式**（仅R2000-R2018部分版本）

### 如何打开DWG文件？

**方案1：转换为DXF格式（推荐）**
1. 使用AutoCAD: 文件 → 另存为 → DXF格式
2. 使用免费工具: **DWG TrueView** 或 **ODA File Converter**
3. 在线转换: CloudConvert、Zamzar等网站

**方案2：直接尝试打开**
- 本工具会尝试直接读取DWG文件
- 如果失败，会提示转换为DXF格式
- 建议使用R2000-R2013版本的DWG文件

### 推荐工具

**ODA File Converter（免费）**
- 下载地址: https://www.opendesign.com/guestfiles/oda_file_converter
- 批量转换DWG ↔ DXF
- 支持所有DWG版本

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
