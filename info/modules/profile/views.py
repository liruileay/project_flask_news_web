from flask import render_template, g, request, jsonify, current_app, redirect, make_response
from info import db
from info.models import News, Category, User
from info.utils.common import get_user, storage
from info.utils.response_code import RET
from . import profile_blu
from info.constants import USER_COLLECTION_MAX_NEWS, USER_FOLLOWED_MAX_COUNT, OTHER_NEWS_PAGE_MAX_COUNT


@profile_blu.route('/other_news_list')
def other_news_list():
    # 获取页数
    p = request.args.get("p", 1)
    user_id = request.args.get("user_id")
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if not all([p, user_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    if not user:
        return jsonify(errno=RET.NODATA, errmsg="用户不存在")

    try:
        paginate = News.query.filter(News.user_id == user.id).paginate(p, OTHER_NEWS_PAGE_MAX_COUNT, False)
        # 获取当前页数据
        news_li = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    news_dict_li = []

    for news_item in news_li:
        news_dict_li.append(news_item.to_review_dict())
    data = {"news_list": news_dict_li,
            "total_page": total_page,
            "current_page": current_page}
    return jsonify(errno=RET.OK, errmsg="OK", data=data)


@profile_blu.route("/other_info")
@get_user
def other_info():
    if not g.user_id:
        return jsonify(errno=RET.SESSIONERR, errmsg="要登陆才能看别人的新闻喔")
    user_id = request.args.get("user_id")
    try:
        other = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据错误")
    if not other:
        return jsonify(errno=RET.DATAEXIST, errmsg="用户找不到")
    is_followed = False
    if other in g.user_id.followers:
        is_followed = True

    data = {
        "is_followed": is_followed,
        "other_info": other.to_dict(),
        "user": g.user_id.to_dict()

    }

    return render_template("news/other.html", data=data)


@profile_blu.route("/")
@get_user
def user_info():
    """
    个人中心
    :return:
    """
    user = g.user_id
    if not user:
        return redirect("/")
    data = {
        "user": user.to_dict()
    }

    return render_template("news/user.html", data=data)


@profile_blu.route("/base_info", methods=["GET", "POST"])
@get_user
def user_base_info():
    """用户基本加载和修改"""
    user = g.user_id
    if request.method == "POST":
        nick_name = request.json.get("nick_name")
        signature = request.json.get("signature")
        gender = request.json.get("gender")
        if not all([nick_name, signature, gender]):
            return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
        if gender not in ["MAN", "WOMAN"]:
            return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
        user.gender = gender
        user.signature = signature
        user.nick_name = nick_name
        return jsonify(errno=RET.OK, errmsg="OK")
    data = {
        "user": user.to_dict()
    }
    return render_template("news/user_base_info.html", data=data)


@profile_blu.route("/pic_info", methods=["POST", "GET"])
@get_user
def user_pic_info():
    """
    用户图片上传
    :return:
    """
    user = g.user_id
    if not user:
        return redirect("/")
    if request.method == "GET":
        data = {
            "user": user.to_dict()
        }

        return render_template("news/user_pic_info.html", data=data)
    try:
        image_file = request.files.get("avatar").read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg="数据存储错误")

    try:
        key = storage(image_file)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="七牛云存储错误")

    user.avatar_url = key
    return jsonify(errno=RET.OK, errmsg="ok")


@profile_blu.route("/pass_info", methods=["POST", "GET"])
@get_user
def user_pass_info():
    """
    用户密码修改
    :return:
    """
    user = g.user_id
    if not user:
        return redirect("/")
    if request.method == "GET":
        data = {
            "user": user.to_dict()
        }
        return render_template("news/user_pass_info.html", data=data)
    old_password = request.json.get("old_password")
    new_password = request.json.get("new_password")
    if not all([old_password, new_password]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if not user.check_password(old_password):
        return jsonify(errno=RET.PARAMERR, errmsg="数据查询错误")

    user.password = new_password
    make_response()

    return jsonify(errno=RET.OK, errmsg="成功")


@profile_blu.route("/collection")
@get_user
def user_collection():
    """
    新闻收藏
    :return:
    """
    user = g.user_id
    if not user:
        return redirect("/")
    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    total_page = 1
    current_page = 1
    news = []
    try:
        paginate = user.collection_news.paginate(page, USER_COLLECTION_MAX_NEWS, False)
        total_page = paginate.pages
        current_page = paginate.page
        news = paginate.items
    except Exception as e:
        current_app.logger.error(e)

    news_dict_li = []
    for new in news:
        news_dict_li.append(new.to_basic_dict())

    data = {
        "total_page": total_page,
        "current_page": current_page,
        "collections": news_dict_li
    }
    return render_template("news/user_collection.html", data=data)


@profile_blu.route("/news_release", methods=["POST", "GET"])
@get_user
def user_news_release():
    """新闻发布"""
    user = g.user_id
    if not user:
        return redirect("/")
    if request.method == "GET":
        category_list = []
        try:
            category_mode = Category.query.all()
        except Exception as e:
            current_app.logger(e)
            return jsonify(errno=RET.DBERR, errmsg="数据错误")
        for category in category_mode:
            category_list.append(category.to_dict())
        if category_list:
            category_list.pop(0)

        data = {
            "user": user.to_dict(),
            "categories": category_list
        }
        return render_template("news/user_news_release.html", data=data)
    title = request.form.get("title")
    category_id = request.form.get("category_id")
    digest = request.form.get("digest")
    index_image = request.files.get("index_image")
    content = request.form.get("content")
    if not all([title, category_id, digest, index_image, content]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        category_id = int(category_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        index_image = index_image.read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="图片错误")
    try:
        key = storage(index_image)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="上传图片错误")

    new = News()
    new.category_id = category_id
    new.digest = digest
    new.content = content
    new.index_image_url = key
    new.title = title
    new.status = 1

    user.news_list.append(new)
    try:
        db.session.add(new)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据库保存错误")
    return jsonify(errno=RET.OK, errmsg="ok")


@profile_blu.route("/news_list")
@get_user
def user_news_list():
    """
    发布新闻列表
    :return:
    """
    user = g.user_id
    if not user:
        return redirect("/")
    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    total_page = 1
    current_page = 1
    news_list = []
    try:
        paginate = user.news_list.paginate(page, USER_COLLECTION_MAX_NEWS, False)
        total_page = paginate.pages
        current_page = paginate.page
        news_list = paginate.items
    except Exception as e:
        current_app.logger.error(e)
    news_dict_li = []
    for news in news_list:
        news_dict_li.append(news.to_review_dict())

    data = {
        "news_list": news_dict_li,
        "total_page": total_page,
        "current_page": current_page
    }
    return render_template("news/user_news_list.html", data=data)


@profile_blu.route("/user_follow")
@get_user
def user_follow():
    """
    新闻关注
    :return:
    """
    user = g.user_id
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="请先登陆")
    p = request.args.get("p", 1)
    total_page = 1
    current_page = 1
    follow_model = []
    try:
        paginate = user.followed.paginate(p, USER_FOLLOWED_MAX_COUNT, False)
        total_page = paginate.pages
        current_page = paginate.page
        follow_model = paginate.items
    except Exception as e:
        current_app.logger.error(e)
    follow_dict_li = []
    for follow in follow_model:
        follow_dict_li.append(follow.to_dict())

    data = {
        "user": follow_dict_li,
        "total_page": total_page,
        "current_page": current_page
    }
    return render_template("news/user_follow.html", data=data)
