@echo off
chcp 65001 >nul
echo ====================================
echo CAD看图工具 - 打包脚本
echo ====================================
echo.

echo [1/3] 清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "CAD看图工具.spec" del "CAD看图工具.spec"
echo 清理完成！
echo.

echo [2/3] 开始打包程序...
python -m PyInstaller --onefile --windowed --name "CAD看图工具" ^
    --hidden-import=ezdxf ^
    --hidden-import=ezdxf.addons ^
    --hidden-import=ezdxf.addons.drawing ^
    --hidden-import=ezdxf.addons.drawing.matplotlib ^
    --hidden-import=matplotlib.backends.backend_agg ^
    cad_viewer.py

if %errorlevel% neq 0 (
    echo.
    echo 打包失败！请检查错误信息。
    pause
    exit /b 1
)

echo 打包完成！
echo.

echo [3/3] 生成的文件位置:
echo dist\CAD看图工具.exe
echo.

echo ====================================
echo 打包成功！
echo ====================================
echo.
echo 您可以将 dist\CAD看图工具.exe 复制到任何位置使用
echo 支持直接拖拽DWG/DXF文件到exe图标上打开
echo.
pause
