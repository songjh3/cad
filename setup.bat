@echo off
chcp 65001 >nul
echo ====================================
echo CAD看图工具 - 环境配置脚本
echo ====================================
echo.

echo 正在安装依赖包...
echo 使用清华大学镜像源加速下载
echo.
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

if %errorlevel% neq 0 (
    echo.
    echo 依赖安装失败！请检查Python和pip是否正确安装。
    pause
    exit /b 1
)

echo.
echo ====================================
echo 依赖安装完成！
echo ====================================
echo.
echo 提示: 如果下载速度慢，可以设置永久镜像源:
echo pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
echo.
echo 您现在可以:
echo 1. 运行 python cad_viewer.py 启动程序
echo 2. 运行 build.bat 打包成exe文件
echo.
echo 常用国内镜像源:
echo - 清华: https://pypi.tuna.tsinghua.edu.cn/simple
echo - 阿里云: https://mirrors.aliyun.com/pypi/simple
echo - 腾讯云: https://mirrors.cloud.tencent.com/pypi/simple
echo.
pause
