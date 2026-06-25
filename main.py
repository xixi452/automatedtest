from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime,date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from datetime import date as date_type

app = Flask(__name__, static_folder='static')  # 【关键】指定正确的静态文件夹
CORS(app)

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost:3306/product_db?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ==================== 数据模型定义 ====================
class User(db.Model):
    __tablename__ = 'users'

    VALID_ROLES = ['admin', 'user', 'merchant', 'supplier']

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')

    def set_password(self, pwd):
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)

    def to_dict(self):
        return {'id': self.id, 'username': self.username, 'role': self.role}


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'price': float(self.price),
            'stock': self.stock, 'description': self.description,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class Medicine(db.Model):
    __tablename__ = 'medicines'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    batch_no = db.Column(db.String(50), nullable=False)  # 批号
    expiry_date = db.Column(db.Date, nullable=False)  # 有效期
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, default=0)
    manufacturer = db.Column(db.String(200), nullable=False, default='')

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'batch_no': self.batch_no,
            'expiry_date': self.expiry_date.strftime('%Y-%m-%d') if self.expiry_date else None,
            'price': float(self.price), 'stock': self.stock,
            'manufacturer': self.manufacturer
        }


# 初始化表
with app.app_context():
    db.create_all()


# ==================== 通用 CRUD 工厂函数 ====================
def create_crud_routes(model, url_prefix, required_fields):
    """动态生成增删改查路由，减少重复代码"""

    # 从 url_prefix 提取唯一标识，如 '/api/products' -> 'products'
    resource_name = url_prefix.strip('/').split('/')[-1]

    @app.route(f'{url_prefix}', methods=['GET'], endpoint=f'{resource_name}_list')
    def get_list():
        items = model.query.all()
        return jsonify({'code': 200, 'data': [i.to_dict() for i in items]})

    @app.route(f'{url_prefix}/<int:id>', methods=['GET'], endpoint=f'{resource_name}_detail')
    def get_one(id):
        item = model.query.get(id)
        if not item:
            return jsonify({'code': 404, 'message': '未找到'}), 404
        return jsonify({'code': 200, 'data': item.to_dict()})

    @app.route(f'{url_prefix}', methods=['POST'], endpoint=f'{resource_name}_create')
    def create():
        data = request.get_json()
        if not data or any(f not in data or data[f] is None for f in required_fields):
            return jsonify({'code': 400, 'message': f'必填字段: {required_fields}'}), 400

        if model == Medicine:
            if 'expiry_date' in data and isinstance(data['expiry_date'], str):
                try:
                    data['expiry_date'] = date_type.fromisoformat(data['expiry_date'])
                except (ValueError, TypeError):
                    return jsonify({'code': 400, 'message': '有效期格式错误，应为YYYY-MM-DD'}), 400

        if model in (Product, Medicine):
            if float(data.get('price', 0)) < 0:
                return jsonify({'code': 400, 'message': '价格不能为负数'}), 400
            if int(data.get('stock', 0)) < 0:
                return jsonify({'code': 400, 'message': '库存不能为负数'}), 400

        if model == User:
            role = data.get('role', 'user')
            if role not in User.VALID_ROLES:
                return jsonify({'code': 400, 'message': f'非法角色，允许值: {User.VALID_ROLES}'}), 400
            item = User(username=data['username'], role=role)
            item.set_password(data['password'])
        else:
            item = model(**data)

        db.session.add(item)
        db.session.commit()
        return jsonify({'code': 201, 'message': '创建成功', 'data': item.to_dict()}), 201

    @app.route(f'{url_prefix}/<int:id>', methods=['PUT'], endpoint=f'{resource_name}_update')
    def update(id):
        item = model.query.get(id)
        if not item:
            return jsonify({'code': 404, 'message': '未找到'}), 404
        data = request.get_json()

        if model in (Product, Medicine):
            if 'price' in data and float(data['price']) < 0:
                return jsonify({'code': 400, 'message': '价格不能为负数'}), 400
            if 'stock' in data and int(data['stock']) < 0:
                return jsonify({'code': 400, 'message': '库存不能为负数'}), 400

        if model == User and 'role' in data:
            if data['role'] not in User.VALID_ROLES:
                return jsonify({'code': 400, 'message': f'非法角色，允许值: {User.VALID_ROLES}'}), 400

        if model == User and 'password' in data and data['password']:
            item.set_password(data['password'])

        for k, v in data.items():
            if hasattr(item, k) and k != 'id' and k != 'password':
                setattr(item, k, v)

        db.session.commit()
        return jsonify({'code': 200, 'message': '更新成功', 'data': item.to_dict()})

    @app.route(f'{url_prefix}/<int:id>', methods=['DELETE'], endpoint=f'{resource_name}_delete')
    def delete(id):
        item = model.query.get(id)
        if not item:
            return jsonify({'code': 404, 'message': '未找到'}), 404
        db.session.delete(item)
        db.session.commit()
        return jsonify({'code': 200, 'message': '删除成功'})
# 注册三组 CRUD 接口
create_crud_routes(User, '/api/users', ['username', 'password'])
create_crud_routes(Product, '/api/products', ['name', 'price'])
create_crud_routes(Medicine, '/api/medicines', ['name', 'batch_no', 'expiry_date', 'price'])


# 登录专用接口
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    if user and user.check_password(data.get('password', '')):
        return jsonify({'code': 0, 'message': '登录成功', 'data': user.to_dict()})
    return jsonify({'code': -1, 'message': '账号或密码错误'}), 401


# 返回前端SPA页面
@app.route('/')
@app.route('/<path:path>')
def serve_frontend(path=''):
    if path.startswith('api/'):
        from flask import abort
        abort(404)
    return app.send_static_file('index.html')

@app.errorhandler(404)
def not_found(e):
    # 如果请求路径以 /api/ 开头，返回 JSON；否则返回前端页面（SPA 刷新场景）
    if request.path.startswith('/api/'):
        return jsonify({'code': 404, 'message': '接口不存在'}), 404
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8081)


