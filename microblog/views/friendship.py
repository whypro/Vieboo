# -*- coding: utf-8 -*-
from flask import Module, g, redirect, url_for, flash
from flask.ext.login import login_required
from microblog.forms import ChatForm, GroupForm
from microblog.models import People, Friendship, Chatting, Group, Blackship
from microblog.database import db
from microblog.tools import render_template


friendship = Module(__name__, url_prefix='/friendship')


@friendship.route('/follow/<int:id>/')
@login_required
def follow(id):
    """关注"""
    if g.user.id == id:
        flash(u'不能关注自己', 'warning')
    else:
        people = People.query.get(id)
        if g.user.is_following(id):
            flash(u'不能重复关注', 'warning')
        elif g.user.is_blocking(id):
            flash(u'不能关注黑名单中的人，请先移出黑名单', 'warning')
        elif people.is_blocking(g.user.id):
            flash(u'对方拒绝了您的关注请求', 'warning')
        else:
            g.user.following.append(people)
            db.session.add(g.user)
            db.session.commit()
            flash(u'关注成功', 'success')
    return redirect(url_for('frontend.index'))


@friendship.route('/unfollow/<int:id>/')
@login_required
def unfollow(id):
    """取消关注"""
    people = People.query.get(id)
    if g.user.is_following(id):
        g.user.following.remove(people)
        db.session.add(g.user)
        db.session.commit()
        flash(u'取消成功', 'success')
    return redirect(url_for('frontend.index'))


@friendship.route('/following/', defaults={'page': 1})
@friendship.route('/following/page/<int:page>/')
@friendship.route('/following/group/<int:gid>/', defaults={'page': 1})
@friendship.route('/following/group/<int:gid>/page/<int:page>/')
@login_required
def show_following(page, gid=None):
    """查看我关注的人"""
    if not gid:
        pagination = g.user.following.order_by(Friendship.c.follow_time).paginate(page, per_page=10)
        following = pagination.items
    else:
        pagination = g.user.following.filter(Friendship.c.group_id==gid).order_by(Friendship.c.follow_time).paginate(page, per_page=10)
        following = pagination.items

    add_group_form = GroupForm()
    return render_template('friendship.html',
                           people=following,
                           pagination=pagination,
                           active_page='show_following',
                           active_gid=gid,
                           add_group_form=add_group_form,
                           title=u'我关注的')


@friendship.route('/followed/', defaults={'page': 1})
@friendship.route('/followed/page/<int:page>/')
@login_required
def show_followed(page):
    """查看关注我的人"""
    pagination = g.user.followed.order_by(Friendship.c.follow_time).paginate(page, per_page=10)
    followed = pagination.items
    return render_template('friendship.html',
                           people=followed,
                           pagination=pagination,
                           active_page='show_followed',
                           title=u'关注我的')


@friendship.route('/mutual/', defaults={'page': 1})
@friendship.route('/mutual/page/<int:page>/')
@login_required
def show_mutual(page):
    """查看互相关注的人"""
    # TODO:
    pagination = g.user.following.order_by(Friendship.c.follow_time).paginate(page, per_page=10)
    mutual = pagination.items
    return render_template('friendship.html',
                           people=mutual,
                           pagination=pagination,
                           active_page='show_mutual',
                           title=u'互相关注')


@friendship.route('/block/<int:id>/')
@login_required
def block(id):
    if g.user.id == id:
        flash(u'不能将自己加入黑名单', 'warning')
    else:
        people = People.query.get(id)
        if g.user.is_blocking(id):
            flash(u'不能重复加入黑名单', 'warning')
        else:
            g.user.blocking.append(people)
            # 取消关注
            if g.user.is_following(id):
                g.user.following.remove(people)
            db.session.add(g.user)
            db.session.commit()
            flash(u'加入黑名单成功', 'success')
    return redirect(url_for('frontend.index'))


@friendship.route('/unblock/<int:id>/')
@login_required
def unblock(id):
    people = People.query.get(id)
    if g.user.is_blocking(id):
        g.user.blocking.remove(people)
        db.session.add(g.user)
        db.session.commit()
        flash(u'取消黑名单成功', 'success')
    return redirect(url_for('frontend.index'))


@friendship.route('/blocking/', defaults={'page': 1})
@friendship.route('/blocking/page/<int:page>/')
@login_required
def show_blocking(page):
    """查看黑名单"""
    pagination = g.user.blocking.order_by(Blackship.c.block_time.desc()).paginate(page, per_page=10)
    blocking = pagination.items
    return render_template('friendship.html',
                           people=blocking,
                           pagination=pagination,
                           active_page='show_blocking',
                           title=u'黑名单')


@friendship.route('/chat/<int:id>/', methods=['GET', 'POST'])
@login_required
def send_chatting(id):
    if g.user.id == id:
        flash(u'不能给自己发送私信', 'warning')
        return redirect(url_for('frontend.index'))
    chat_form = ChatForm()
    from_people = g.user
    to_people = People.query.get(id)

    if chat_form.validate_on_submit():
        chatting = Chatting(from_people.id, to_people.id, content=chat_form.content.data)
        db.session.add(chatting)
        db.session.commit()
        flash(u'发送成功', 'success')
        return redirect(url_for('frontend.index'))

    return render_template(
        'chatting-new.html',
        chat_form=chat_form,
        from_people=from_people,
        to_people=to_people
    )


@friendship.route('/chat/inbox/', defaults={'page': 1})
@friendship.route('/chat/inbox/page/<int:page>/')
@login_required
def show_inbox(page):
    pagination = Chatting.query.filter_by(to_id=g.user.id).order_by(Chatting.chat_time.desc()).paginate(page, per_page=10)
    chatting = pagination.items
    return render_template('chatting-inbox.html', chattings=chatting, pagination=pagination)


@friendship.route('/chat/detail/<int:id>/')
@login_required
def show_chatting_detail(id):
    chattings = Chatting.query.get(id)
    return render_template('chatting-detail.html', chatting=chattings)


@friendship.route('/chat/outbox/', defaults={'page': 1})
@friendship.route('/chat/outbox/page/<int:page>/')
@login_required
def show_outbox(page):
    pagination = Chatting.query.filter_by(from_id=g.user.id).order_by(Chatting.chat_time.desc()).paginate(page, per_page=10)
    chattings = pagination.items
    return render_template('chatting-outbox.html', chattings=chattings, pagination=pagination)


@friendship.route('/following/group/add/', methods=['GET', 'POST'])
@login_required
def add_group():
    group_form = GroupForm()
    if group_form.validate_on_submit():
        group = Group(name=group_form.name.data, people_id=g.user.id)
        db.session.add(group)
        db.session.commit()
        flash(u'新建成功', 'success')
    return redirect(url_for('frontend.index'))


@friendship.route('/following/group/delete/<int:id>/')
@login_required
def delete_group(id):
    group = Group.query.get(id)
    if group in g.user.groups:
        g.user.groups.remove(group)
        db.session.add(g.user)
        db.session.commit()
        flash(u'删除成功', 'success')
    return redirect(url_for('frontend.index'))


