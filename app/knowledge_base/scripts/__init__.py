import sys
from loguru import logger
import os

# ===============================
# 日志配置（生产级）
# ===============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "crawl_{time}.log")

logger.remove()

# 控制台输出
logger.add(
    sys.stdout,
    level="INFO",
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level}</level> | "
           "<cyan>{message}</cyan>",
    enqueue=True
)

# 文件日志
logger.add(
    LOG_FILE,
    level="DEBUG",
    rotation="20 MB",
    retention=None,  # 永久保存
    encoding="utf-8",
    enqueue=True
)
