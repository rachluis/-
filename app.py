from flask import Flask, redirect, url_for
from routes.login import login_bp
from routes.dashboard import dashboard_bp
from routes.user_interaction import user_interaction_bp

# 初始化Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # 生产环境中应使用环境变量

# 注册蓝图
app.register_blueprint(login_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(user_interaction_bp)


def index():
    return redirect(url_for('login.login'))

# 启动应用
if __name__ == '__main__':
    app.run(debug=True)