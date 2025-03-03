from setuptools import setup, find_packages
import sys
import os

# 获取 backend 目录的绝对路径
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# 将常用路径加入 sys.path 方便导包
COMMON_PATHS = [
    BASE_DIR,  # backend 根目录
    os.path.join(BASE_DIR, "app"),  # app 目录
    os.path.join(BASE_DIR, "app/models"),  # models 目录
    os.path.join(BASE_DIR, "app/routers"),  # routers 目录
    os.path.join(BASE_DIR, "app/services"),  # services 目录
    os.path.join(BASE_DIR, "config"),  # config 目录
    os.path.join(BASE_DIR, "tests"),  # tests 目录
]

for path in COMMON_PATHS:
    if path not in sys.path:
        sys.path.insert(0, path)

setup(
    name="performance-review-api",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "sqlalchemy",
        "pytest",
        "httpx",
        "pydantic",
        "alembic",
        "PyJWT",
    ],
    include_package_data=True,
    python_requires=">=3.8",
)
