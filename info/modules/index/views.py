from flask import render_template, current_app, session, jsonify, request, g
from info.utils.response_code import RET
from . import views_blu
from info.models import User, News, Category
from info.constants import *
from info.utils.common import get_user


@views_blu.route("/news_list")
def news_list():
    """
    新闻排行
    :return:
    """
    cid = request.args.get("cid", 1)
    page = request.args.get("page", 1)
    per_page = request.args.get("per_page", 10)
    try:
        cid = int(cid)
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.OK, errmsg="数据格式不正确")

    filters = [News.status == 0]
    if cid != 1:
        filters.append(News.category_id == cid)
    try:
        paginate = News.query.filter(*filters).order_by(News.create_time.desc()).paginate(page, per_page, False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
    if not paginate:
        return jsonify(errno=RET.NODATA, errmsg="数据不存在")
    news_model_list = paginate.items
    total_page = paginate.pages
    current_page = paginate.page

    news_dict_li = []
    for news in news_model_list:
        news_dict_li.append(news.to_dict())

    data = {
        "total_page": total_page,
        "current_page": current_page,
        "news_dict_li": news_dict_li
    }
    return jsonify(errno=RET.OK, errmsg="ok", data=data)


@views_blu.route('/')
@get_user
def index():
    """
    新闻首页
    :return:
    """
    user = g.user_id
    news_model_list = []
    try:
        news_model_list = News.query.order_by(News.clicks.desc()).limit(CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
    news_dict_li = []
    for news in news_model_list:
        news_dict_li.append(news.to_basic_dict())

    category_mode_list = Category.query.all()
    categories_dict_li = []
    for categories in category_mode_list:
        categories_dict_li.append(categories.to_dict())

    data = {
        "user": user.to_dict() if user else None,
        "news_dict_li": news_dict_li,
        "category_li": categories_dict_li
        # 将用户的信息传入到模板代码中去
    }

    return render_template("news/index.html", data=data)


@views_blu.route('/favicon.ico')
def favicon_image():
    """Function used internally to send static files from the static
           folder to the browser."""
    return current_app.send_static_file('news/favicon.ico')
