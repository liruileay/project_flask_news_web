from flask import current_app
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from info import create_app, db
from info.models import User

app = create_app("development")
manager = Manager(app)
# 添加数据库迁移命令
Migrate(app, db)
manager.add_command("db", MigrateCommand)


# 用命令的方式去添加管理员
@manager.option("-n", "-name", dest="name")
@manager.option("-p", "-password", dest="password")
def createsuperuser(name, password):
    if not all([name, password]):
        print("参数不足")
        return
    user = User()
    user.mobile = name
    user.nick_name = name
    user.password = password
    user.is_admin = True
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        print("添加失败")
    print("添加管理员成功")


if __name__ == '__main__':
    manager.run()
