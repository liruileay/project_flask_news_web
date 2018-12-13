import logging
from redis import StrictRedis
import os
import base64


class Config(object):
    """配置类"""
    DEBUG = True
    SECRET_KEY = base64.b64encode(os.urandom(64))
    # mysql的配置
    SQLALCHEMY_DATABASE_URI = "mysql://root:123456@localhost:3306/flask_project_myself"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 让每次数据库都默认提交不用自己提交
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    # 端口和ip的配置
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    # 配置使用session的存储数据库类型
    SESSION_REDIS = StrictRedis(host=REDIS_HOST, port=REDIS_PORT, password=123456)
    SESSION_TYPE = "redis"
    # 开启session签名
    SESSION_USE_SIGNER = True
    # 设置过期默认是31天
    SESSION_PERMANENT = False
    # 设置过期时间
    PERMANENT_SESSION_LIFETIME = 8000 * 2
    # 设置日志等级
    LOG_LEVEL = logging.ERROR


class DevelopmentConfig(Config):
    """开发环境的配置"""
    DEBUG = True
    LOG_LEVEL = logging.DEBUG


class TestingConfig(Config):
    """单元测试环境下的配置"""
    DEBUG = True
    TESTING = True


class ProductionConfig(Config):
    """生产环境下的配置"""
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "product": ProductionConfig,
    "testing": TestingConfig

}
