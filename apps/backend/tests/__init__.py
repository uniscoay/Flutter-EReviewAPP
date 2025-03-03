# 添加导入处理代码以帮助pytest找到正确的模块
import sys
import os

# 获取项目根目录并添加到Python路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir) 