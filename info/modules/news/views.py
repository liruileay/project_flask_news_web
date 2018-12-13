from flask import render_template, current_app, g, abort, jsonify, request
from info import db
from info.constants import *
from info.models import News, Comment, CommentLike, User
from info.modules.news import news_blu
from info.utils.common import get_user
from info.utils.response_code import RET


@news_blu.route("/followed_user", methods=["POST"])
@get_user
def followed_user():
    """
    新闻关注
    :return:
    """
    if not g.user_id:
        return jsonify(errno=RET.SESSIONERR, errmsg="请先登陆")
    user_id = request.json.get("user_id")
    action = request.json.get("action")
    if not all([user_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        user_id = int(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action not in ["follow", "unfollow"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="参数错误")
    if not user:
        return jsonify(errno=RET.DATAEXIST, errmsg="数据不存在")
    if action == "follow":
        if g.user_id not in user.followers:
            user.followers.append(g.user_id)
        return jsonify(errno=RET.OK, errmsg="OK")
    else:
        if g.user_id in user.followers:
            user.followers.remove(g.user_id)
        return jsonify(errno=RET.OK, errmsg="OK")


@news_blu.route("/comment_like", methods=["POST"])
@get_user
def comment_like():
    """
    新闻点赞
    :return:
    """
    user = g.user_id
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户没有登陆")

    comment_id = request.json.get("comment_id")
    action = request.json.get("action")
    if not all([comment_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        comment_id = int(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action not in ["add", "remove"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        comment_model = Comment.query.get(comment_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库查询错误")
    if not comment_model:
        return jsonify(errno=RET.DATAERR, errmsg="没有评论没法点赞")

    try:
        comment_like_model = CommentLike.query.filter(CommentLike.comment_id == comment_id,
                                                      CommentLike.user_id == user.id).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库错误")

    if action == "add":
        if not comment_like_model:
            comment_like_model = CommentLike()
            comment_like_model.user_id = user.id
            comment_like_model.comment_id = comment_model.id
            db.session.add(comment_like_model)
            comment_model.like_count += 1

    else:
        if comment_like_model:
            db.session.delete(comment_like_model)
            comment_model.like_count -= 1
    return jsonify(errno=RET.OK, errmsg="ok")


@news_blu.route("/news_comment", methods=["POST"])
@get_user
def news_comment():
    """
    新闻评论
    :return:
    """
    user = g.user_id
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户没有登陆")
    news_id = request.json.get("news_id", None)
    comment_content = request.json.get("comment", None)
    parent_id = request.json.get("parent_id", None)
    if not all([news_id, comment_content]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不正确")
    try:
        news_id = int(news_id)
        if parent_id:
            parent_id = int(parent_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数不正确")
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")
    if not news:
        return jsonify(errno=RET.PARAMERR, errmsg="新闻不存在")
    comment = Comment()
    comment.news_id = news_id
    comment.user_id = user.id
    comment.content = comment_content
    if parent_id:
        comment.parent_id = parent_id
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据库保存错误")
    return jsonify(errno=RET.OK, errmsg="ok", data=comment.to_dict())


@news_blu.route("/news_collect", methods=["POST"])
@get_user
def news_collect():
    """
    新闻收藏
    :return:
    """
    user = g.user_id
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="请先登录")
    news_id = request.json.get("news_id", None)
    action = request.json.get("action", None)
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    try:
        news_id = int(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if action not in ["collect", "cancel_collect"]:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if not news:
        return jsonify(errno=RET.DATAERR, errmsg="新闻不存在")
    if action == "collect":
        if news not in user.collection_news:
            user.collection_news.append(news)
    else:
        if news in user.collection_news:
            user.collection_news.remove(news)
    return jsonify(errno=RET.OK, errmsg="OK")


@news_blu.route("/<int:news_id>")
@get_user
def index_news(news_id):
    """
    新闻详情页
    :param news_id:
    :return:
    """
    user = g.user_id
    news_model = None
    try:
        news_model = News.query.order_by(News.clicks.desc()).limit(CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if not news:
        abort(404)
    news_li = news.to_dict()

    news.clicks += 1
    is_collected = False
    if user:
        if news_model in user.collection_news:
            is_collected = True
    news_dict_li = []
    for new in news_model:
        news_dict_li.append(new.to_dict())
    comments_models = []
    try:
        comments_models = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
    comments_likes_id = []
    if user:
        try:
            comments_ids = [comment.id for comment in comments_models]
            # 找出当前用户点赞了那些评论
            comments_likes = CommentLike.query.filter(CommentLike.comment_id.in_(comments_ids),
                                                      CommentLike.user_id == user.id).all()
            # 生成当前用户点赞的评论的id
            comments_likes_id = [comment.comment_id for comment in comments_likes]
        except Exception as e:
            current_app.logger.error(e)
    comments_dict_li = []
    if comments_models:
        for comment in comments_models:
            comment_dict = comment.to_dict()
            comment_dict["is_like"] = False
            if comment.id in comments_likes_id:
                comment_dict["is_like"] = True
            comments_dict_li.append(comment_dict)
    is_follow = False
    if news.user and user:
        if news.user in user.followed:
            is_follow = True

    data = {"user": user.to_dict() if user else None,
            "news_dict_li": news_dict_li,
            "news": news_li,
            "is_collected": is_collected,
            "comments": comments_dict_li,
            "is_follow": is_follow
            }
    return render_template("news/detail.html", data=data)
