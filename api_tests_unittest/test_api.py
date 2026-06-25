import unittest
import requests
from datetime import date, timedelta

BASE_URL = "http://localhost:8081"


class BaseTestCase(unittest.TestCase):
    """测试基类：提供通用请求方法和断言"""

    def get(self, path, **kwargs):
        return requests.get(f"{BASE_URL}{path}", **kwargs)

    def post(self, path, json=None, **kwargs):
        return requests.post(f"{BASE_URL}{path}", json=json, **kwargs)

    def put(self, path, json=None, **kwargs):
        return requests.put(f"{BASE_URL}{path}", json=json, **kwargs)

    def delete(self, path, **kwargs):
        return requests.delete(f"{BASE_URL}{path}", **kwargs)

    def assert_code(self, resp, expected_code):
        self.assertEqual(resp.status_code, expected_code,
                         f"期望状态码{expected_code}, 实际{resp.status_code}, 响应: {resp.text}")

    def assert_json_code(self, resp, expected_code):
        data = resp.json()
        self.assertEqual(data.get('code'), expected_code,
                         f"期望业务码{expected_code}, 实际{data.get('code')}, 响应: {data}")


# ==================== 登录接口测试 ====================
class TestLogin(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        """创建一个测试用户供登录测试使用"""
        cls.test_user = {'username': 'login_tester', 'password': 'Test@123', 'role': 'user'}
        requests.post(f"{BASE_URL}/api/users", json=cls.test_user)

    @classmethod
    def tearDownClass(cls):
        """清理测试用户"""
        users = requests.get(f"{BASE_URL}/api/users").json().get('data', [])
        for u in users:
            if u['username'] == 'login_tester':
                requests.delete(f"{BASE_URL}/api/users/{u['id']}")

    def test_login_success(self):
        resp = self.post('/api/login', json={'username': 'login_tester', 'password': 'Test@123'})
        self.assert_code(resp, 200)
        self.assert_json_code(resp, 0)
        self.assertIn('data', resp.json())
        self.assertEqual(resp.json()['data']['username'], 'login_tester')

    def test_login_wrong_password(self):
        resp = self.post('/api/login', json={'username': 'login_tester', 'password': 'wrong'})
        self.assert_code(resp, 401)
        self.assert_json_code(resp, -1)

    def test_login_nonexistent_user(self):
        resp = self.post('/api/login', json={'username': 'ghost_user', 'password': '123'})
        self.assert_code(resp, 401)

    def test_login_empty_body(self):
        resp = self.post('/api/login', json={})
        self.assert_code(resp, 401)

    def test_login_missing_fields(self):
        resp = self.post('/api/login', json={'username': 'login_tester'})
        self.assert_code(resp, 401)


# ==================== 商品 CRUD 测试 ====================
class TestProductCRUD(BaseTestCase):

    def setUp(self):
        self.valid_product = {'name': '测试商品', 'price': 9.99, 'stock': 10, 'description': '单元测试用'}
        resp = self.post('/api/products', json=self.valid_product)
        self.created_id = resp.json().get('data', {}).get('id')

    def tearDown(self):
        if self.created_id:
            self.delete(f'/api/products/{self.created_id}')

    # --- 创建测试 ---
    def test_create_product_success(self):
        resp = self.post('/api/products', json={'name': '新商品', 'price': 19.9, 'stock': 5})
        self.assert_code(resp, 201)
        self.assert_json_code(resp, 201)
        # 清理
        pid = resp.json()['data']['id']
        self.delete(f'/api/products/{pid}')

    def test_create_product_missing_name(self):
        resp = self.post('/api/products', json={'price': 10})
        self.assert_code(resp, 400)

    def test_create_product_missing_price(self):
        resp = self.post('/api/products', json={'name': '无价格商品'})
        self.assert_code(resp, 400)

    def test_create_product_negative_price(self):
        resp = self.post('/api/products', json={'name': '负价商品', 'price': -1, 'stock': 0})
        self.assert_code(resp, 400)
        self.assertIn('负数', resp.json().get('message', ''))

    def test_create_product_negative_stock(self):
        resp = self.post('/api/products', json={'name': '负库存', 'price': 10, 'stock': -5})
        self.assert_code(resp, 400)
        self.assertIn('负数', resp.json().get('message', ''))

    def test_create_product_zero_price(self):
        """边界值：价格为0应允许"""
        resp = self.post('/api/products', json={'name': '免费商品', 'price': 0, 'stock': 1})
        self.assert_code(resp, 201)
        pid = resp.json()['data']['id']
        self.delete(f'/api/products/{pid}')

    def test_create_product_empty_body(self):
        resp = self.post('/api/products', json={})
        self.assert_code(resp, 400)

    # --- 查询测试 ---
    def test_get_product_list(self):
        resp = self.get('/api/products')
        self.assert_code(resp, 200)
        self.assertIsInstance(resp.json()['data'], list)

    def test_get_product_detail(self):
        resp = self.get(f'/api/products/{self.created_id}')
        self.assert_code(resp, 200)
        self.assertEqual(resp.json()['data']['name'], '测试商品')

    def test_get_product_not_found(self):
        resp = self.get('/api/products/999999')
        self.assert_code(resp, 404)

    # --- 更新测试 ---
    def test_update_product_success(self):
        resp = self.put(f'/api/products/{self.created_id}', json={'name': '已更新', 'price': 29.9})
        self.assert_code(resp, 200)
        self.assertEqual(resp.json()['data']['name'], '已更新')

    def test_update_product_negative_price(self):
        resp = self.put(f'/api/products/{self.created_id}', json={'price': -10})
        self.assert_code(resp, 400)

    def test_update_product_negative_stock(self):
        resp = self.put(f'/api/products/{self.created_id}', json={'stock': -1})
        self.assert_code(resp, 400)

    def test_update_product_partial(self):
        """只更新描述，其他字段不变"""
        resp = self.put(f'/api/products/{self.created_id}', json={'description': '新描述'})
        self.assert_code(resp, 200)
        self.assertEqual(resp.json()['data']['description'], '新描述')
        self.assertEqual(resp.json()['data']['name'], '测试商品')

    def test_update_nonexistent_product(self):
        resp = self.put('/api/products/999999', json={'name': 'x'})
        self.assert_code(resp, 404)

    # --- 删除测试 ---
    def test_delete_product_success(self):
        pid = self.created_id
        resp = self.delete(f'/api/products/{pid}')
        self.assert_code(resp, 200)
        self.created_id = None  # 防止tearDown重复删除
        # 验证确实被删
        resp2 = self.get(f'/api/products/{pid}')
        self.assert_code(resp2, 404)

    def test_delete_nonexistent_product(self):
        resp = self.delete('/api/products/999999')
        self.assert_code(resp, 404)


# ==================== 药品 CRUD 测试 ====================
class TestMedicineCRUD(BaseTestCase):

    def setUp(self):
        self.valid_medicine = {
            'name': '阿莫西林', 'batch_no': 'B20260601',
            'expiry_date': '2027-12-31', 'price': 15.5,
            'stock': 100, 'manufacturer': '华北制药'
        }
        resp = self.post('/api/medicines', json=self.valid_medicine)
        self.created_id = resp.json().get('data', {}).get('id')

    def tearDown(self):
        if self.created_id:
            self.delete(f'/api/medicines/{self.created_id}')

    def test_create_medicine_success(self):
        resp = self.post('/api/medicines', json=self.valid_medicine)
        self.assert_code(resp, 201)
        data = resp.json()['data']
        self.assertEqual(data['manufacturer'], '华北制药')
        pid = data['id']
        self.delete(f'/api/medicines/{pid}')

    def test_create_medicine_missing_batch_no(self):
        data = {**self.valid_medicine}
        del data['batch_no']
        resp = self.post('/api/medicines', json=data)
        self.assert_code(resp, 400)

    def test_create_medicine_missing_expiry_date(self):
        data = {**self.valid_medicine}
        del data['expiry_date']
        resp = self.post('/api/medicines', json=data)
        self.assert_code(resp, 400)

    def test_create_medicine_negative_price(self):
        data = {**self.valid_medicine, 'price': -5}
        resp = self.post('/api/medicines', json=data)
        self.assert_code(resp, 400)

    def test_create_medicine_negative_stock(self):
        data = {**self.valid_medicine, 'stock': -10}
        resp = self.post('/api/medicines', json=data)
        self.assert_code(resp, 400)

    def test_update_medicine_manufacturer(self):
        resp = self.put(f'/api/medicines/{self.created_id}', json={'manufacturer': '更新厂商'})
        self.assert_code(resp, 200)
        self.assertEqual(resp.json()['data']['manufacturer'], '更新厂商')

    def test_get_medicine_list_includes_manufacturer(self):
        resp = self.get('/api/medicines')
        self.assert_code(resp, 200)
        items = resp.json()['data']
        self.assertTrue(len(items) > 0)
        self.assertIn('manufacturer', items[0])

    def test_delete_medicine_success(self):
        resp = self.delete(f'/api/medicines/{self.created_id}')
        self.assert_code(resp, 200)
        self.created_id = None


# ==================== 用户 CRUD + 角色校验测试 ====================
class TestUserCRUD(BaseTestCase):

    def setUp(self):
        self.valid_user = {'username': 'test_user_crud', 'password': 'Pass@123', 'role': 'user'}
        resp = self.post('/api/users', json=self.valid_user)
        self.created_id = resp.json().get('data', {}).get('id')

    def tearDown(self):
        if self.created_id:
            self.delete(f'/api/users/{self.created_id}')

    def test_create_user_success(self):
        resp = self.post('/api/users', json={'username': 'new_user_x', 'password': 'Abc@123', 'role': 'merchant'})
        self.assert_code(resp, 201)
        self.assertEqual(resp.json()['data']['role'], 'merchant')
        uid = resp.json()['data']['id']
        self.delete(f'/api/users/{uid}')

    def test_create_user_invalid_role(self):
        resp = self.post('/api/users', json={'username': 'bad_role', 'password': '123', 'role': 'hacker'})
        self.assert_code(resp, 400)
        self.assertIn('非法角色', resp.json().get('message', ''))

    def test_create_user_all_valid_roles(self):
        """遍历所有合法角色均可创建"""
        for role in ['admin', 'user', 'merchant', 'supplier']:
            resp = self.post('/api/users', json={'username': f'role_{role}_test', 'password': '123', 'role': role})
            self.assert_code(resp, 201, )
            self.assertEqual(resp.json()['data']['role'], role)
            self.delete(f"/api/users/{resp.json()['data']['id']}")

    def test_create_user_missing_username(self):
        resp = self.post('/api/users', json={'password': '123'})
        self.assert_code(resp, 400)

    def test_create_user_missing_password(self):
        resp = self.post('/api/users', json={'username': 'no_pwd'})
        self.assert_code(resp, 400)

    def test_update_user_role_valid(self):
        resp = self.put(f'/api/users/{self.created_id}', json={'role': 'supplier'})
        self.assert_code(resp, 200)
        self.assertEqual(resp.json()['data']['role'], 'supplier')

    def test_update_user_role_invalid(self):
        resp = self.put(f'/api/users/{self.created_id}', json={'role': 'superadmin'})
        self.assert_code(resp, 400)

    def test_update_user_password(self):
        resp = self.put(f'/api/users/{self.created_id}', json={'password': 'NewPass@456'})
        self.assert_code(resp, 200)
        # 验证新密码可登录
        login_resp = self.post('/api/login', json={'username': 'test_user_crud', 'password': 'NewPass@456'})
        self.assert_json_code(login_resp, 0)

    def test_update_user_empty_password_not_changed(self):
        """空密码不应触发密码修改"""
        resp = self.put(f'/api/users/{self.created_id}', json={'password': '', 'role': 'merchant'})
        self.assert_code(resp, 200)
        # 原密码仍可登录
        login_resp = self.post('/api/login', json={'username': 'test_user_crud', 'password': 'Pass@123'})
        self.assert_json_code(login_resp, 0)

    def test_delete_user_success(self):
        resp = self.delete(f'/api/users/{self.created_id}')
        self.assert_code(resp, 200)
        self.created_id = None


# ==================== 前端页面可访问性测试 ====================
class TestFrontendServing(BaseTestCase):

    def test_index_page_accessible(self):
        resp = self.get('/')
        self.assert_code(resp, 200)
        self.assertIn('综合信息管理系统', resp.text)

    def test_spa_fallback_route(self):
        """SPA 路由回退应返回 index.html"""
        resp = self.get('/some/deep/route')
        self.assert_code(resp, 200)
        self.assertIn('综合信息管理系统', resp.text)


if __name__ == '__main__':
    unittest.main(verbosity=2)