from datetime import datetime
from urllib.parse import urlsplit
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
import sqlalchemy as sa
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, \
    EmptyForm, PostForm, ChangePost
from app.models import User, Post


@app.before_request
def before_request():
    """The function of updating the last visit"""
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    """The function of the main page"""
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Опубликовано')
        return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    posts = db.paginate(current_user.following_posts(), page=page,
                        per_page=app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Подписки', form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@app.route('/explore')
@login_required
def explore():
    """The function of the page of all posts"""
    page = request.args.get('page', 1, type=int)
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title='Лента', posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Account register function
    :return: register or login pages
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, telegram=form.telegram.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Вы зарегистрированы')
        return redirect(url_for('login'))
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Account login function
    :return: index or login pages
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash('Некорректное имя или пароль')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Вход', form=form)


@app.route('/logout')
def logout():
    """
    Account logout function
    :return: index page
    """
    logout_user()
    return redirect(url_for('index'))


@app.route('/user/<username>')
@login_required
def user(username):
    """
    Profile function
    :param username: str
    :return: render profile and data
    """
    user = db.first_or_404(sa.select(User).where(User.username == username))
    page = request.args.get('page', 1, type=int)
    query = user.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=app.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('user', username=user.username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('user', username=user.username, page=posts.prev_num) \
        if posts.has_prev else None
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    Profile change function
    :return: redirect again or render edit page
    """
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Сохранено')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='О себе',
                           form=form)


@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    """
    Subscription function
    :param username: str
    :return: redirect
    """
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(f'User {username} not found.')
            return redirect(url_for('index'))
        if user == current_user:
            flash('Это вы')
            return redirect(url_for('user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(f'Подписались на {username}')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    """
    Unsubscribe function
    :param username: str
    :return: redirect
    """
    form = EmptyForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(f'Пользователь {username} не найден.')
            return redirect(url_for('index'))
        if user == current_user:
            flash('Это вы')
            return redirect(url_for('user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(f'Отписались от {username}.')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/delete_post/<username>/<post_id>', methods=['POST'])
@login_required
def delete_post(username, post_id):
    """
    Post deletion function
    :param username: str
    :param post_id: str
    :return: redirect
    """
    form = EmptyForm()
    if form.validate_on_submit():
        post = db.session.scalar(
            sa.select(Post).where(Post.id == post_id))
        db.session.delete(post)
        db.session.commit()
        flash('Пост удален')
        return redirect(url_for('user', username=username))


@app.route('/change_post/<username>/<post_id>', methods=['POST'])
@login_required
def change_post(username, post_id):
    """
    Post changing function
    :param username: str
    :param post_id: str
    :return: redirect
    """
    form = ChangePost()
    if form.validate_on_submit():
        post = db.session.scalar(
            sa.select(Post).where(Post.id == post_id))
        post.body = form.post.data
        db.session.commit()
        flash('Пост изменен')
        return redirect(url_for('user', username=username))
    return render_template('change_post.html', title='Изменить пост', form=form)
