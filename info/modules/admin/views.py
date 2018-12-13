import time
from datetime import datetime, timedelta
from flask import render_template, request, current_app, session, redirect, url_for, g, jsonify
from info import constants, db
from info.models import User, News, Category
from info.utils.common import get_user
from info.utils.response_code import RET
from . import admin_blu
from info.utils.common import storage


@admin_blu.route("/logout")
def logout():
    session.pop("is_admin")
    session.pop("user_id")
    session.pop("mobile")
    session.pop("nick_name")
    session.pop("password")
    return redirect(url_for("admin.login"))


@admin_blu.route("/news_type", methods=["POST", "GET"])
def news_type():
    categories = []
    try:
        categories = Category.query.all()
    except Exception as e:
        current_app.logger(e)
    category_dict_li = []
    for category in categories:
        category_dict_li.append(category.to_dict())
    category_dict_li.pop(0)
    name_list = [category["name"] for category in category_dict_li]
    if request.method == "GET":
        data = {
            "categories": category_dict_li
        }
        return render_template("admin/news_type.html", data=data)

    category_id = request.json.get("id")
    name = request.json.get("name")
    if not name and name in name_list:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if not category_id:
        category = Category()
        category.name = name
        try:
            db.session.add(category)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="数据库错误")
        return jsonify(errno=RET.OK, errmsg="OK")
    try:
        category_id = int(category_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        category = Category.query.get(category_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
    if not category:
        return jsonify(errno=RET.PARAMERR, errmsg="数据没有")
    category.name = name
    return jsonify(errno=RET.OK, errmsg="OK")


@admin_blu.route("/news_edit_detail", methods=["POST", "GET"])
def news_edit_detail():
    if request.method == "GET":
        news_id = request.args.get("news_id")
        try:
            news_id = int(news_id)
        except Exception as e:
            current_app.logger.error(e)
        news = None
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)
        if not news:
            return jsonify(errno=RET.PARAMERR, errmsg="新闻不存在")
        categories = []
        try:
            categories = Category.query.all()
        except Exception as e:
            current_app.logger(e)
        category_dict_li = []
        for category in categories:
            if category.name ==category_id:
                category.to_dict()["is_selected"]=True
            category_dict_li.append(category.to_dict())
        data = {
            "news": news.to_dict() if news_id else None,
            "categories": category_dict_li
        }
        return render_template("admin/news_edit_detail.html", data=data)

    category_id = request.form.get("category_id", None)
    news_id = request.form.get("news_id", None)
    title = request.form.get("title", None)
    digest = request.form.get("digest", None)
    content = request.form.get("content", None)
    index_image = request.files.get("index_image", None)
    if not all([category_id, news_id, title, digest, content, index_image]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        category_id = int(category_id)
        news_id = int(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        result = storage(index_image.read())
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="第三方错误")
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")
    if not news:
        return jsonify(errno=RET.DATAEXIST, errmsg="数据不存在")
    news.category_id = category_id
    news.content = content
    news.digest = digest
    news.title = title
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + result
    return jsonify(errno=RET.OK, errmsg="ok")


@admin_blu.route("/news_edit")
def news_edit():
    keywords = request.args.get("keywords", None)
    page = request.args.get("page", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    news = []
    current_page = 1
    total_page = 1
    filters = [News.status == 0]
    if keywords:
        filters.append(News.title.contains(keywords))
    try:
        user = News.query.filter(*filters). \
            order_by(News.clicks.desc()).paginate(page,
                                                  constants.ADMIN_USER_PAGE_MAX_COUNT, False)
        current_page = user.page
        total_page = user.pages
        news = user.items
    except Exception as e:
        current_app.logger.error(e)

    news_dict_li = []
    for new in news:
        news_dict_li.append(new.to_dict())
    data = {
        "news_list": news_dict_li,
        "current_page": current_page,
        "total_page": total_page
    }
    return render_template("admin/news_edit.html", data=data)


@admin_blu.route("/news_review_action", methods=["POST"])
def news_detail():
    news_id = request.json.get("news_id")
    action = request.json.get("action")
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action not in ["accept", "reject"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if not news:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action == "accept":
        news.status = 0
    else:
        reason = request.json.get("reason")
        if not reason:
            return jsonify(errno=RET.PARAMERR, errmsg="请输入拒绝原因")
        news.status = -1
        news.reason = reason
    return jsonify(errno=RET.OK, errmsg="ok")


@admin_blu.route("/news_review_detail/<int:news_id>")
def news_review_detail(news_id):
    new = None
    try:
        new = News.query.get(news_id)
    except Exception as e:
        current_app.logger(e)
    data = {
        "news": new.to_dict() if new else None
    }
    return render_template("admin/news_review_detail.html", data=data)


@admin_blu.route("/news_review")
def news_review():
    keywords = request.args.get("keywords", None)
    page = request.args.get("page", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    news = []
    current_page = 1
    total_page = 1
    filters = [News.status != 0]
    if keywords:
        filters.append(News.title.contains(keywords))
    try:
        user = News.query.filter(*filters). \
            order_by(News.create_time.desc()).paginate(page,
                                                       constants.ADMIN_USER_PAGE_MAX_COUNT, False)
        current_page = user.page
        total_page = user.pages
        news = user.items
    except Exception as e:
        current_app.logger.error(e)

    news_dict_li = []
    for new in news:
        news_dict_li.append(new.to_dict())
    data = {
        "news_list": news_dict_li,
        "current_page": current_page,
        "total_page": total_page
    }
    return render_template("admin/news_review.html", data=data)


@admin_blu.route("/user_list")
def user_list():
    page = request.args.get("page", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    users = []
    current_page = 1
    total_page = 1
    try:
        user = User.query.filter(User.is_admin == False).paginate(page, constants.ADMIN_USER_PAGE_MAX_COUNT, False)
        current_page = user.page
        total_page = user.pages
        users = user.items
    except Exception as e:
        current_app.logger.error(e)
    users_dict_li = []
    for user in users:
        users_dict_li.append(user.to_dict())
    data = {
        "users": users_dict_li,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("admin/user_list.html", data=data)


@admin_blu.route("/user_count")
def user_count():
    total_count = 0
    mouth_count = 0
    today_count = 0
    try:
        total_count = User.query.filter(User.is_admin == False).count()
    except Exception as e:
        current_app.logger.error(e)
    # 取到时间对象
    t = time.localtime()
    # 将时间对象转换为具体的时间
    begin_mon_date = datetime.strptime("%d-%02d-01" %
                                       (t.tm_year, t.tm_mon), "%Y-%m-%d")
    try:
        mouth_count = User.query.filter(User.is_admin == False,
                                        User.create_time > begin_mon_date).count()
    except Exception as e:
        current_app.logger.error(e)

    begin_day_date = datetime.strptime("%d-%02d-%02d" %
                                       (t.tm_year, t.tm_mon, t.tm_mday), "%Y-%m-%d")
    try:
        today_count = User.query.filter(User.is_admin == False, User.create_time > begin_day_date).count()
    except Exception as e:
        current_app.logger.error(e)

    active_time = []
    active_count = []
    # 转换成具体的时间 即datetime格式的
    begin_today_date = datetime.strptime("%d-%02d-%02d" % (t.tm_year, t.tm_mon, t.tm_mday), "%Y-%m-%d")
    for i in range(31):
        begin_day = begin_today_date - timedelta(days=i)  # datetime类型
        end_day = begin_today_date - timedelta(days=(i - 1))
        try:
            count = User.query.filter(User.last_login >= begin_day, User.is_admin == False,
                                      User.last_login <= end_day).count()
            active_count.append(count)
            # 格式化成字符串穿给前端 strftime ("%Y-%m-%d") 即str格式的
            active_time.append(begin_day.strftime("%Y-%m-%d"))
        except Exception as e:
            current_app.logger.error(e)
    active_time.reverse()
    active_count.reverse()
    data = {
        "total_count": total_count,
        "mouth_count": mouth_count,
        "today_count": today_count,
        "active_time": active_time,
        "active_count": active_count
    }
    return render_template("admin/user_count.html", data=data)


@admin_blu.route("/index")
@get_user
def index_admin():
    user = g.user_id
    if not user:
        return redirect(url_for("admin.login"))
    if not user.is_admin:
        return redirect(url_for("admin.login"))

    data = {
        "user": user.to_dict()
    }
    return render_template("admin/index.html", data=data)


@admin_blu.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "GET":
        user_id = session.get("user_id", None)
        is_admin = session.get("is_admin", False)
        if user_id and is_admin:
            return redirect(url_for("admin.index_admin"))
        return render_template("admin/login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    if not all([username, password]):
        return redirect("admin/login")

    try:
        user = User.query.filter(User.mobile == username, User.is_admin == True).first()
    except Exception as e:
        current_app.logger.error(e)
        return redirect("admin/login")
    if not user:
        return redirect("admin/login")
    if not user.check_password(password):
        return redirect("admin/login")

    session["is_admin"] = True
    session["mobile"] = user.mobile
    session["user_id"] = user.id
    session["nick_name"] = user.nick_name

    return redirect(url_for("admin.index_admin"))
