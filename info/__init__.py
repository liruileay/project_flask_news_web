import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from redis import StrictRedis
from config import config

db = SQLAlchemy()  # 先初始化扩展对象在调用init_app添加app
redis_store = None  # type: StrictRedis #给变量加一个注释


def logging_app(config_name):
    # 设置日志的记录等级
    logging.basicConfig(level=config[config_name].LOG_LEVEL)  # 调试debug级
    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024, backupCount=10)
    # 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)


# create_app相当于工厂函数
def create_app(config_name):
    app = Flask(__name__)
    # 设置log日志等级
    logging_app(config_name)
    # 添加配置类
    app.config.from_object(config[config_name])
    # 初始化redis
    global redis_store
    redis_store = StrictRedis(host=config[config_name].REDIS_HOST,
                              port=config[config_name].REDIS_PORT,
                              password=123456, decode_responses=True)

    # 设置为受保护
    CSRFProtect(app)

    @app.after_request
    def after_request(response):
        csrf_token = generate_csrf()
        response.set_cookie("csrf_token", csrf_token)
        return response

    # 初始化数据库
    db.init_app(app)
    # 不使用flask的session初始话flask_session里面的session
    Session(app)
    from info.modules.index import views_blu
    from info.modules.passport import passport_blu
    app.register_blueprint(views_blu)
    app.register_blueprint(passport_blu)
    from info.modules.news import news_blu
    app.register_blueprint(news_blu)
    from info.utils.common import do_index_class
    app.add_template_filter(do_index_class, "do_index_class")
    from info.modules.profile import profile_blu
    app.register_blueprint(profile_blu)
    from info.modules.admin import admin_blu
    app.register_blueprint(admin_blu)
    from info.utils.common import get_user

    @app.errorhandler(404)
    @get_user
    def error(error):
        return render_template("news/404.html")

    return app
