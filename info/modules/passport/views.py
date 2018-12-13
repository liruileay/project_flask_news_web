import random
import re
from datetime import datetime
from flask import request, abort, make_response, current_app, jsonify, session
from info import constants
from info import redis_store, db
from info.constants import IMAGE_CODE_REDIS_EXPIRES
from info.libs.yuntongxun.sms import CCP
from info.models import User
from info.modules.passport import passport_blu
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET


@passport_blu.route("/logout")
def logout():
    """
    退出登陆逻辑
    :return:
    """
    session.pop("user_id", None)
    session.pop("nick_name", None)
    session.pop("mobile", None)
    session.pop("is_admin",None)
    return jsonify(errno=RET.OK, errmsg="退出成功")


@passport_blu.route("/login", methods=["POST"])
def login():
    """
    登陆逻辑
    :return:
    """
    params_dict = request.json
    mobile = params_dict.get("mobile")
    password = params_dict.get("passport")

    if not all([mobile, password]):
        return jsonify(errno=RET.DATAERR, errmsg="密码或者账号输入错误")
    if not re.match(r"1[3456789]\d{9}", mobile):
        return jsonify(errno=RET.DATAERR, errmsg="手机格式不正确")
    try:
        user = User.query.filter(User.mobile == mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")
    if not user:
        return jsonify(errno=RET.NODATA, errmsg="用户不存在")
    if not user.check_password(password):
        return jsonify(errno=RET.PWDERR, errmsg="密码输入错误")

    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    session["user_id"] = user.id

    user.last_login = datetime.now()
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="登陆时间保存错误")

    return jsonify(errno=RET.OK, errmsg="登陆成功")


@passport_blu.route("/register", methods=["POST"])
def register():
    """
    注册逻辑
    :return:
    """
    params_dict = request.json
    mobile = params_dict.get("mobile")
    password = params_dict.get("password")
    smscode = params_dict.get("smscode")

    if not all([mobile, password, smscode]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if not re.match(r"1[3456789]\d{9}", mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号码不正确")
    try:
        real_sms = redis_store.get("SMS" + mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")
    if not real_sms:
        return jsonify(erron=RET.DATAERR, errmsg="验证码过期")
    if real_sms != smscode:
        return jsonify(errno=RET.DATAERR, errmsg="验证码输入不正确")

    user = User()

    user.mobile = mobile
    user.nick_name = mobile
    user.last_login = datetime.now()
    user.password = password

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.debug(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库存储错误")

    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile

    return jsonify(errno=RET.OK, errmsg="注册成功")


@passport_blu.route("/sms_code", methods=["POST"])
def get_sms_code():
    """
    生成短信验证码
    :return:
    """
    params_dict = request.json
    mobile = params_dict["mobile"]
    image_code = params_dict["image_code"]
    image_code_id = params_dict["image_code_id"]

    if not all([mobile, image_code_id, image_code]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if not re.match(r"1[3456789]\d{9}", mobile):
        return jsonify(errno=RET.PARAMERR, errmsg="手机号码输入格式不正确")
    try:
        real_image_code = redis_store.get("imageCodeId" + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")
    if not real_image_code:
        return jsonify(errno=RET.PARAMERR, errmsg="验证码过期")
    if image_code.upper() != real_image_code.upper():
        return jsonify(errno=RET.PARAMERR, errmsg="验证码输入不正确")
    sms_code_id = "%06d" % random.randint(0, 999999)
    print(sms_code_id)
    result = CCP().send_template_sms(mobile, [sms_code_id, constants.SMS_CODE_REDIS_EXPIRES], 1)
    if result:
        return jsonify(errno=RET.DATAERR, errmsg="短信验证码发送失败")
    if not result:
        try:
            redis_store.set("SMS" + mobile, sms_code_id, constants.SMS_CODE_REDIS_EXPIRES)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(RET.DBERR, errmsg="数据存储错误")
    return jsonify(errno=RET.OK, errmsg="验证成功")


@passport_blu.route('/image_code')
def get_image_code():
    """
    生成图片验证码
    :return:
    """
    image_code_id = request.args.get("imageCodeId", None)
    if not image_code_id:
        return abort(404)
    name, text, image = captcha.generate_captcha()
    try:
        redis_store.set("imageCodeId%s" % image_code_id, text, ex=IMAGE_CODE_REDIS_EXPIRES)
    except Exception as E:
        current_app.logger.debug(E)
        return abort(500)

    response = make_response(image)
    response.headers["Content-Type"] = "image/jpg"
    return response
