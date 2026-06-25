import unittest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "http://localhost:8081"


class BaseE2ETest(unittest.TestCase):
    PANEL_MAP = {
        '商品管理': 'panel-product',
        '药品管理': 'panel-medicine',
        '用户管理': 'panel-user'
    }

    @classmethod
    def setUpClass(cls):
        opts = Options()
        opts.add_argument('--headless')
        opts.add_argument('--disable-gpu')
        opts.add_argument('--window-size=1280,900')
        cls.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=opts
        )
        cls.driver.implicitly_wait(3)
        cls.wait = WebDriverWait(cls.driver, 15)
        cls.current_panel = None

    @classmethod
    def tearDownClass(cls):
        """✅ 防御性清理：任何步骤失败都不影响后续测试"""
        try:
            for _ in range(5):
                try:
                    alert = WebDriverWait(cls.driver, 1).until(EC.alert_is_present())
                    alert.accept()
                except Exception:
                    break
        except Exception:
            pass

        try:
            cls.driver.execute_script("window.stop();")
        except Exception:
            pass

        try:
            cls.driver.delete_all_cookies()
        except Exception:
            pass

        try:
            cls.driver.get('about:blank')
            WebDriverWait(cls.driver, 5).until(
                lambda d: d.current_url == 'about:blank'
            )
        except Exception:
            pass

        cls.current_panel = None

    @classmethod
    def init_panel(cls, tab_text):
        """✅ 终极版：JS 点击 + 强制清理遮罩"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 清理所有可能的 alert
                for _ in range(5):
                    try:
                        alert = WebDriverWait(cls.driver, 1).until(EC.alert_is_present())
                        alert.accept()
                    except Exception:
                        break

                cls.driver.get(BASE_URL)
                WebDriverWait(cls.driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )

                # ✅ 关键修复：先用 JS 移除所有可能的遮罩层
                cls.driver.execute_script("""
                    // 移除常见的 loading/modal/overlay 遮罩
                    document.querySelectorAll('.loading, .modal, .overlay, .mask, [class*="loading"], [class*="modal"]').forEach(el => el.remove());
                    // 确保 body 可交互
                    document.body.style.pointerEvents = 'auto';
                    document.body.style.overflow = 'auto';
                """)

                # ✅ 关键修复：用 JS 查找并点击 Tab（绕过 Selenium 遮挡检测）
                panel_id = cls.PANEL_MAP[tab_text]
                clicked = cls.driver.execute_script(f"""
                    const tabs = document.querySelectorAll('div.tab');
                    for (const tab of tabs) {{
                        if (tab.textContent.trim() === '{tab_text}') {{
                            tab.click();
                            return true;
                        }}
                    }}
                    return false;
                """)

                if not clicked:
                    raise Exception(f"JS 未找到 Tab: {tab_text}")

                cls.current_panel = panel_id
                WebDriverWait(cls.driver, 15).until(
                    EC.visibility_of_element_located((By.ID, panel_id))
                )
                print(f"✅ init_panel('{tab_text}') 成功 (第{attempt + 1}次尝试)")
                return

            except Exception as e:
                print(f"⚠️ init_panel('{tab_text}') 第{attempt + 1}次失败: {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    try:
                        cls.driver.get('about:blank')
                    except Exception:
                        pass
                    time.sleep(1)
                else:
                    # ✅ 最终失败时截图保存，便于人工排查
                    try:
                        cls.driver.save_screenshot(f"init_panel_failed_{tab_text}.png")
                        print(f"📸 已保存失败截图: init_panel_failed_{tab_text}.png")
                    except Exception:
                        pass
                    raise

    # ---------- 作用域安全操作 ----------
    def _scope(self, element_id):
        if self.current_panel:
            return self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, f"#{self.current_panel} #{element_id}")
            ))
        return self.wait.until(EC.presence_of_element_located((By.ID, element_id)))

    def fill_input(self, element_id, value):
        el = self._scope(element_id)
        # ✅ date 输入框用 JS 赋值，避免 headless 下 send_keys 格式不兼容
        if el.get_attribute('type') == 'date':
            self.driver.execute_script(
                "arguments[0].value = arguments[1]; "
                "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
                el, str(value)
            )
        else:
            el.clear()
            el.send_keys(str(value))

    def select_dropdown(self, element_id, value):
        sel = Select(self._scope(element_id))
        sel.select_by_value(value)

    def get_dropdown_value(self, element_id):
        sel = Select(self._scope(element_id))
        return sel.first_selected_option.get_attribute('value')

    def click_button(self, btn_class):
        selector = f"#{self.current_panel} .{btn_class}" if self.current_panel else f".{btn_class}"
        btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        btn.click()

    def get_alert_text_and_accept(self, timeout=10):
        alert = WebDriverWait(self.driver, timeout).until(EC.alert_is_present())
        text = alert.text
        alert.accept()
        return text

    # ✅ 核心修复：Stale-proof 表格读取
    def get_table_rows(self, tbody_id, min_rows=0):
        """一次性通过 JS 提取表格文本，彻底避免 StaleElement"""
        if min_rows > 0:
            self.wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, f"#{tbody_id} tr")) >= min_rows)
        script = f"""
            const rows = document.querySelectorAll('#{tbody_id} tr');
            return Array.from(rows).map(row =>
                Array.from(row.querySelectorAll('td')).map(td => td.textContent.trim())
            );
        """
        return self.driver.execute_script(script) or []

    # ✅ 核心修复：等待特定内容出现在表格中（而非仅检查行数）
    def wait_for_table_content(self, tbody_id, keyword, col_index=1):
        """等待表格指定列中出现目标关键词"""
        self.wait.until(lambda d: any(
            keyword in row[col_index]
            for row in (self.get_table_rows(tbody_id) or [])
        ))

    def wait_for_input_value(self, element_id, expected_value, timeout=10):
        """✅ 新增：等待输入框的值变为预期值（解决异步回填问题）"""
        WebDriverWait(self.driver, timeout).until(
            lambda d: self._scope(element_id).get_attribute('value') == expected_value
        )

    def wait_for_dropdown_value(self, element_id, expected_value, timeout=10):
        """✅ 新增：等待下拉框选中值变为预期值"""
        WebDriverWait(self.driver, timeout).until(
            lambda d: Select(self._scope(element_id)).first_selected_option.get_attribute('value') == expected_value
        )

    def _safe_click_btn_in_row(self, tbody_id, keyword, btn_class):
        max_retries = 5
        for _ in range(max_retries):
            try:
                row = self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, f"//tbody[@id='{tbody_id}']//tr[contains(.,'{keyword}')]")
                ))
                btn = row.find_element(By.CLASS_NAME, btn_class)
                self.wait.until(EC.element_to_be_clickable(btn))
                btn.click()
                return
            except StaleElementReferenceException:
                time.sleep(0.5)
        raise TimeoutException(f"无法点击{btn_class}: {keyword} (重试{max_retries}次后仍失败)")

    def find_edit_btn_in_row(self, tbody_id, keyword):
        self._safe_click_btn_in_row(tbody_id, keyword, 'btn-edit')

    def find_del_btn_in_row(self, tbody_id, keyword):
        self._safe_click_btn_in_row(tbody_id, keyword, 'btn-del')


# ==================== 商品管理 E2E ====================
class TestProductE2E(BaseE2ETest):
    TEST_NAME = 'E2E测试商品'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.init_panel('商品管理')

    def test_01_create_product(self):
        self.fill_input('p-name', self.TEST_NAME)
        self.fill_input('p-price', '29.99')
        self.fill_input('p-stock', '50')
        self.fill_input('p-desc', '自动化测试创建')
        self.click_button('btn-save')
        msg = self.get_alert_text_and_accept()
        self.assertIn('成功', msg)
        self.wait_for_table_content('tb-product', self.TEST_NAME, col_index=1)
        rows = self.get_table_rows('tb-product')
        self.assertIn(self.TEST_NAME, [r[1] for r in rows])

    def test_02_create_product_negative_price(self):
        self.click_button('btn-reset')
        self.fill_input('p-name', '负价商品')
        self.fill_input('p-price', '-5')
        self.click_button('btn-save')
        msg = self.get_alert_text_and_accept()
        self.assertIn('负数', msg)

    def test_03_create_product_empty_name(self):
        self.click_button('btn-reset')
        self.fill_input('p-price', '10')
        self.click_button('btn-save')
        msg = self.get_alert_text_and_accept()
        self.assertIn('不能为空', msg)

    def test_04_edit_product(self):
        self.find_edit_btn_in_row('tb-product', self.TEST_NAME)

        # ✅ 关键修复：等待 p-name 输入框的值变为目标商品名
        # 这证明前端的 fetch + 表单回填已经完成
        self.wait_for_input_value('p-name', self.TEST_NAME)

        self.assertEqual(
            self.driver.find_element(By.ID, 'p-name').get_attribute('value'),
            self.TEST_NAME
        )
        self.fill_input('p-price', '39.99')
        self.click_button('btn-save')
        msg = self.get_alert_text_and_accept()
        self.assertIn('成功', msg)
        self.wait_for_table_content('tb-product', '39.99', col_index=2)
        rows = self.get_table_rows('tb-product')
        target = [r for r in rows if r[1] == self.TEST_NAME][0]
        self.assertEqual(target[2], '39.99')

    def test_05_reset_form(self):
        self.fill_input('p-name', '临时数据')
        self.click_button('btn-reset')
        self.assertEqual(self.driver.find_element(By.ID, 'p-name').get_attribute('value'), '')
        self.assertIn('新增', self.driver.find_element(By.ID, 'title-product').text)

    def test_06_delete_product(self):
        self.find_del_btn_in_row('tb-product', self.TEST_NAME)
        self.wait.until(EC.alert_is_present())
        self.driver.switch_to.alert.accept()
        msg = self.get_alert_text_and_accept()
        self.assertIn('成功', msg)
        time.sleep(1)
        rows = self.get_table_rows('tb-product')
        self.assertNotIn(self.TEST_NAME, [r[1] for r in rows])


# ==================== 药品管理 E2E ====================
class TestMedicineE2E(BaseE2ETest):
    TEST_NAME = 'E2E测试药品'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.init_panel('药品管理')

    def test_01_create_medicine(self):
        self.fill_input('m-name', self.TEST_NAME)
        self.fill_input('m-batch', 'B20260622')
        self.fill_input('m-expiry', '2027-12-31')
        self.fill_input('m-price', '18.50')
        self.fill_input('m-stock', '200')
        self.fill_input('m-manufacturer', '测试制药')
        self.click_button('btn-save')
        msg = self.get_alert_text_and_accept()
        self.assertIn('成功', msg)
        # ✅ 等待特定内容出现，而非仅检查行数
        self.wait_for_table_content('tb-medicine', self.TEST_NAME, col_index=1)
        rows = self.get_table_rows('tb-medicine')
        self.assertIn(self.TEST_NAME, [r[1] for r in rows])

    def test_02_create_medicine_negative_stock(self):
        self.click_button('btn-reset')
        self.fill_input('m-name', '负库存药')
        self.fill_input('m-batch', 'B000')
        self.fill_input('m-expiry', '2027-01-01')
        self.fill_input('m-price', '10')
        self.fill_input('m-stock', '-1')
        self.click_button('btn-save')
        msg = self.get_alert_text_and_accept()
        self.assertIn('负数', msg)

    def test_03_edit_medicine(self):
        self.find_edit_btn_in_row('tb-medicine', self.TEST_NAME)
        # ✅ 修复：等待表单回填完成后再断言
        self.wait_for_input_value('m-manufacturer', '测试制药')
        self.assertEqual(
            self.driver.find_element(By.ID, 'm-manufacturer').get_attribute('value'),
            '测试制药'
        )
        self.fill_input('m-manufacturer', '更新制药')
        self.click_button('btn-save')
        msg = self.get_alert_text_and_accept()
        self.assertIn('成功', msg)
        # ✅ 等待表格内容更新
        self.wait_for_table_content('tb-medicine', '更新制药', col_index=6)
        rows = self.get_table_rows('tb-medicine')
        target = [r for r in rows if r[1] == self.TEST_NAME][0]
        self.assertEqual(target[6], '更新制药')

    def test_04_delete_medicine(self):
        self.find_del_btn_in_row('tb-medicine', self.TEST_NAME)
        self.wait.until(EC.alert_is_present())
        self.driver.switch_to.alert.accept()
        msg = self.get_alert_text_and_accept()
        self.assertIn('成功', msg)
        time.sleep(1)
        rows = self.get_table_rows('tb-medicine')
        self.assertNotIn(self.TEST_NAME, [r[1] for r in rows])


# ==================== 用户管理 E2E ====================
class TestUserE2E(BaseE2ETest):
    TEST_USER = 'e2e_test_user'
    MERCHANT_USER = 'e2e_merchant'  # ✅ 修复：补上缺失的类变量

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.init_panel('用户管理')

    def _create_user(self, username, password, role='user'):
        self.click_button('btn-reset')
        self.fill_input('u-username', username)
        self.fill_input('u-password', password)
        if role != 'user':
            self.select_dropdown('u-role', role)
        self.click_button('btn-save')
        msg = self.get_alert_text_and_accept()
        self.assertIn('成功', msg)
        # ✅ 等待该用户出现在表格第2列(用户名)
        self.wait_for_table_content('tb-user', username, col_index=1)

    def _delete_user_if_exists(self, username):
        rows = self.get_table_rows('tb-user')
        # ✅ 修复：用户名在 index=1（ID=0, 用户名=1, 角色=2, 操作=3）
        usernames = [r[1] for r in rows if len(r) > 1]
        if username in usernames:
            self.find_del_btn_in_row('tb-user', username)
            self.wait.until(EC.alert_is_present())
            self.driver.switch_to.alert.accept()
            self.get_alert_text_and_accept()
            time.sleep(0.5)

    def test_01_create_user_default_role(self):
        self._delete_user_if_exists(self.TEST_USER)
        self._create_user(self.TEST_USER, 'Test@123')
        rows = self.get_table_rows('tb-user')
        target = [r for r in rows if len(r) > 2 and r[1] == self.TEST_USER][0]
        self.assertEqual(target[2], 'user')

    def test_02_create_user_merchant_role(self):
        self._delete_user_if_exists(self.MERCHANT_USER)
        self._create_user(self.MERCHANT_USER, 'Merch@123', role='merchant')
        rows = self.get_table_rows('tb-user')
        target = [r for r in rows if len(r) > 2 and r[1] == self.MERCHANT_USER][0]
        self.assertEqual(target[2], 'merchant')

    def test_03_edit_user_role_change(self):
        self._delete_user_if_exists(self.TEST_USER)
        self._create_user(self.TEST_USER, 'Test@123')

        # 第一次编辑：user -> supplier
        self.find_edit_btn_in_row('tb-user', self.TEST_USER)
        self.wait_for_dropdown_value('u-role', 'user')  # ✅ 等待回填
        self.assertEqual(self.get_dropdown_value('u-role'), 'user')
        self.select_dropdown('u-role', 'supplier')
        self.click_button('btn-save')
        msg = self.get_alert_text_and_accept()
        self.assertIn('成功', msg)

        # ✅ 关键修复：等待表格中角色列更新为 supplier 后再二次编辑
        self.wait_for_table_content('tb-user', 'supplier', col_index=2)
        time.sleep(0.5)  # 额外等待 DOM 稳定

        # 第二次编辑：验证 supplier 已回填
        self.find_edit_btn_in_row('tb-user', self.TEST_USER)
        self.wait_for_dropdown_value('u-role', 'supplier')  # ✅ 等待回填
        self.assertEqual(self.get_dropdown_value('u-role'), 'supplier')

        # 恢复为 user
        self.select_dropdown('u-role', 'user')
        self.click_button('btn-save')
        self.get_alert_text_and_accept()
        self.wait_for_table_content('tb-user', 'user', col_index=2)

    def test_04_edit_user_password_empty_preserved(self):
        self._delete_user_if_exists(self.TEST_USER)
        self._create_user(self.TEST_USER, 'Test@123')

        self.find_edit_btn_in_row('tb-user', self.TEST_USER)
        # ✅ 等待用户名回填作为"表单已加载"的信号
        self.wait_for_input_value('u-username', self.TEST_USER)
        self.assertEqual(
            self.driver.find_element(By.ID, 'u-password').get_attribute('value'), ''
        )
        self.select_dropdown('u-role', 'merchant')
        self.click_button('btn-save')
        msg = self.get_alert_text_and_accept()
        self.assertIn('成功', msg)

        # 恢复角色
        self.wait_for_table_content('tb-user', 'merchant', col_index=2)
        time.sleep(0.5)
        self.find_edit_btn_in_row('tb-user', self.TEST_USER)
        self.wait_for_dropdown_value('u-role', 'merchant')
        self.select_dropdown('u-role', 'user')
        self.click_button('btn-save')
        self.get_alert_text_and_accept()

    def test_05_reset_user_form_select_default(self):
        self.click_button('btn-reset')
        self.select_dropdown('u-role', 'admin')
        self.fill_input('u-username', 'temp')
        self.click_button('btn-reset')
        self.assertEqual(self.get_dropdown_value('u-role'), 'user')
        self.assertEqual(self.driver.find_element(By.ID, 'u-username').get_attribute('value'), '')

    def test_06_delete_user(self):
        self._delete_user_if_exists(self.TEST_USER)
        self._create_user(self.TEST_USER, 'Test@123')
        self.find_del_btn_in_row('tb-user', self.TEST_USER)
        self.wait.until(EC.alert_is_present())
        self.driver.switch_to.alert.accept()
        msg = self.get_alert_text_and_accept()
        self.assertIn('成功', msg)
        time.sleep(1)
        rows = self.get_table_rows('tb-user')
        self.assertNotIn(self.TEST_USER, [r[1] for r in rows if len(r) > 1])


# ==================== 导航 E2E ====================
class TestNavigationE2E(BaseE2ETest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.driver.get(BASE_URL)
        cls.current_panel = 'panel-product'

    def test_01_default_tab_is_product(self):
        self.assertTrue(self.driver.find_element(By.ID, 'panel-product').is_displayed())

    def test_02_switch_to_medicine_tab(self):
        tab = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//div[@class='tab' and text()='药品管理']")
        ))
        tab.click()
        self.assertTrue(self.driver.find_element(By.ID, 'panel-medicine').is_displayed())
        self.assertFalse(self.driver.find_element(By.ID, 'panel-product').is_displayed())

    def test_03_switch_to_user_tab(self):
        tab = self.wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//div[@class='tab' and text()='用户管理']")
        ))
        tab.click()
        self.assertTrue(self.driver.find_element(By.ID, 'panel-user').is_displayed())

    def test_04_page_title(self):
        self.assertIn('综合信息管理系统', self.driver.title)


if __name__ == '__main__':
    unittest.main(verbosity=2)