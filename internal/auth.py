from flask import render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from internal.appl import app
from simplepam import authenticate
import pwd

login_manager = LoginManager()
login_manager.init_app(app)

users = [x.pw_name for x in pwd.getpwall()]


class User(UserMixin):
    def __init__(self, id):
        self.id = id


@login_manager.user_loader
def user_loader(userId):
    if userId not in users:
        return
    user = User(userId)
    return user


@login_manager.request_loader
def request_loader(request):
    userId = request.form.get('userId')
    if userId not in users:
        return

    user = User(userId)
    return user


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if current_user.is_authenticated:
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error='')

    userId = str(request.form['user'])
    if authenticate(userId, str(request.form['password'])):
        user = User(userId)
        login_user(user)
        return redirect(url_for('home'))

    return render_template('login.html', error='Username and/or password was incorrect!')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect(url_for('login'))
