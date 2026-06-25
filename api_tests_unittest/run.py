import unittest
import xmlrunner
import sys
import os

# 确保能找到测试模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.discover('.', pattern='test_*.py')

    # ✅ 关键：使用 xmlrunner 生成 JUnit XML 格式报告
    runner = xmlrunner.XMLTestRunner(
        output='reports',  # 报告输出目录
        output_filename='result.xml'
    )
    result = runner.run(suite)

    # 如果有失败，返回非0退出码，让Jenkins感知
    sys.exit(0 if result.wasSuccessful() else 1)