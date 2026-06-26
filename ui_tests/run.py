import unittest
import xmlrunner
import sys
import os

os.makedirs('reports', exist_ok=True)
# 确保能找到测试模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.discover('.', pattern='test_*.py')

    # ✅ 关键修改：output 直接指定完整文件路径，这样文件名就是 result.xml
    runner = xmlrunner.XMLTestRunner(
        output='E:/rjcs/automatedtest/ui_tests/reports/result.xml'
    )
    result = runner.run(suite)

    # 如果有失败，返回非0退出码，让Jenkins感知
    sys.exit(0 if result.wasSuccessful() else 1)