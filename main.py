# -*- coding: utf-8 -*-

import sys
import os
import flask
import requests
import sys
from flask import Flask  # Подключаем Flask
from flask import render_template  # Подключаем библиотеку для работы с шаблонами
from sqlalchemy import create_engine  # Подключаем библиотеку для работы с базой данных
from data.users import User
from data.places import LikePlaces
from data.comments import Comments
from data.registerform import RegisterForm
from data.loginform import LoginForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask import request  # Для обработка запросов из форм
from flask import redirect  # Для автоматического перенаправления
import datetime  # Для получения текущей даты и врмени
from data import db_session

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)

pswd = ''
country = ''
a = []
point = ''
distance = ''


@app.route('/favicon.ico')
def fav():
    return ''


@app.route('/')
def greet():
    return render_template('greet.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/register', methods=['GET', 'POST'])
def reg():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            login=form.name.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/sign_in')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/" + str(user.id))
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route("/<user_id>", methods=['GET', 'POST'])
def find(user_id):
    if request.method == 'POST':
        if 'out' in request.form:
            return redirect('/')
        elif 'place' in request.form:
            if len(request.form['place']) > 0:
                if request.form['dist'] == '' or request.form['dist'].isdigit() is False:
                    dist = '500'
                else:
                    dist = request.form['dist']
                return redirect('/' + user_id + '/' + request.form['place'] + '/' + dist)
    return render_template('index.html', data={}, login=user_id, text='', dist='', name=get_user_name(user_id))


@app.route("/<user_id>/<place>/<dist>", methods=['GET', 'POST'])  # Обрабатываем корневой путь
def main(user_id, place, dist):
    global point, distance
    point = place
    distance = dist
    if request.method == 'POST':
        if 'out' in request.form:
            return redirect('/')
        elif 'add' in request.form:
            add_liked(user_id, request.form['hid'])
        elif 'delete' in request.form:
            delete_liked(user_id, request.form['hid'])
        elif 'search' in request.form:
            if 'place' in request.form:
                if len(request.form['place']) > 0:
                    if request.form['dist'] == '' or request.form['dist'].isdigit() is False:
                        dist = '500'
                    else:
                        dist = request.form['dist']
            return redirect('/' + user_id + '/' + request.form['place'] + '/' + dist)
    all_places = get_all_places(place, dist, user_id)
    return render_template('index.html',
                           data=all_places,
                           login=user_id,
                           name=get_user_name(user_id),
                           text=place,
                           dist=dist)


@app.route("/<user_id>/place/<place_id>", methods=['GET', 'POST'])
def user(user_id, place_id):
    global distance, point, a
    print(a)
    if request.method == "POST":
        if 'delete_button' in request.form:
            place_delete_all_messages(place_id)
        elif 'message_text' in request.form:
            if len(request.form['message_text']) > 0:
                add_message(place_id, request.form['message_text'], user_id)
        return redirect('/' + user_id + '/place/' + str(
            place_id))

    place_info = get_place_info(place_id)
    print(place_info)
    place_comments = get_comments_about_place(place_id)

    return render_template('user.html',
                           login=user_id,
                           place=place_info,
                           point=point,
                           distance=distance,
                           name=get_user_name(user_id),
                           messages=place_comments,
                           )


@app.route("/<user_id>/likes", methods=['GET', 'POST'])
def likes(user_id):
    if request.method == 'POST':
        if 'add' in request.form:
            add_liked(user_id, request.form['hid'])
        elif 'delete' in request.form:
            delete_liked(user_id, request.form['hid'])
    places = get_user_likes(user_id)
    data = [dict(get_place_info(el), n=i) for i, el in enumerate(places)]
    print(data)
    return render_template(
        'likes.html',
        login=user_id,
        data=data,
        name=get_user_name(user_id)
    )


def dump(x):
    return flask.json.dumps(x)


def get_place_info(place_id):
    serv = 'https://maps.googleapis.com/maps/api/place/details/json'
    params = {
        'key': 'AIzaSyCO-AM_xATjnsGaC8xZXAfoVsg7RSriD8A',
        'place_id': place_id,
        'language': 'ru'
    }
    response = requests.get(serv, params).json()
    try:
        res = response['result']
        ph = res['photos']
        photos = [get_pict(el['photo_reference']) for el in ph]
        if len(photos):
            pict = photos[0]
        if len(photos) > 10:
            photos = photos[:10]
        d = {
            'place': res['name'],
            'photos': photos,
            'pict': pict,
            'place_id': place_id,
            'country': res['plus_code']['compound_code'].split()[-1],
            'rating': res['rating'],
            'link': res['url'],
            'liked': True

        }
    except KeyError:
        d = {}
    return d


def get_all_places(place, dist, user_id):  # Получить список информации о всех пользователях
    try:
        dist = int(dist)
    except ValueError:
        dist = 500
    params_geocode = {
        'key': 'AIzaSyCO-AM_xATjnsGaC8xZXAfoVsg7RSriD8A',
        'address': place,
    }
    serv_geocode = 'https://maps.googleapis.com/maps/api/geocode/json'
    response = requests.get(serv_geocode, params=params_geocode).json()
    if len(response['results']) == 0:
        return []
    lat = response['results'][0]['geometry']['location']['lat']
    lng = response['results'][0]['geometry']['location']['lng']
    params = {
        'location': str(lat) + ',' + str(lng),
        'radius': str(dist),
        'type': 'tourist_attraction',
        'language': 'ru',
        'key': 'AIzaSyCO-AM_xATjnsGaC8xZXAfoVsg7RSriD8A'
    }
    serv = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
    response = requests.get(serv, params=params)
    res = response.json()['results']
    global a
    a = []
    for i in range(len(res)):
        d = {}
        d['place_id'] = res[i]['place_id']
        d['place'] = res[i]['name']
        try:
            d['pict'] = res[i]['photos'][0]['photo_reference']
        except KeyError:
            d['pict'] = 'Не найдено'
        d['country'] = res[i]['plus_code']['compound_code'].split()[-1]
        d['pict'] = get_pict(d['pict'])
        db_sess = db_session.create_session()
        ab = []
        for user in db_sess.query(LikePlaces).filter(LikePlaces.place == d["place_id"], LikePlaces.user_id == user_id):
            ab.append(user)
        if len(ab) > 0:
            d['liked'] = True
        else:
            d['liked'] = False
        a.append(d)
    all_places = [dict(row, n=i) for i, row in enumerate(a)]  # Создаем список строк из таблицы
    return all_places


def get_comments_about_place(place_id):
    db_sess = db_session.create_session()
    a = []
    for comment in db_sess.query(Comments).filter(Comments.place == place_id).all():
        a.append([comment, get_user_name(comment.user_id)])
    return a


def place_delete_all_messages(place_id):
    db_sess = db_session.create_session()
    db_sess.query(Comments).filter(Comments.place == place_id).delete()
    db_sess.commit()
    # Запрос на удаление строк из таблицы

    return


def add_user(log, pswd):
    user = User()
    user.login = log
    user.password = pswd
    db_sess = db_session.create_session()
    db_sess.add(user)
    db_sess.commit()


def add_message(place_id, message_text, login):  # Сохранить сообщение пользователя в базу
    comment = Comments()
    comment.place = place_id
    comment.user_id = login
    comment.text = message_text
    db_sess = db_session.create_session()
    db_sess.add(comment)
    db_sess.commit()
    return


def user_in_base(log, pswd):
    db_sess = db_session.create_session()
    a = []
    for user in db_sess.query(User).filter((User.login == log) & (User.password == pswd)):
        a.append(user)

    if len(list(a)) > 0:
        return True
    return False


def get_user_id(log):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.login == log).first()
    x = user.id
    return str(x)


def get_pict(ref):
    params = {
        'key': 'AIzaSyCO-AM_xATjnsGaC8xZXAfoVsg7RSriD8A',
        'maxwidth': '400',
        'photoreference': ref
    }
    serv = 'https://maps.googleapis.com/maps/api/place/photo'
    return f'{serv}?key={params["key"]}&maxwidth={params["maxwidth"]}&photoreference={params["photoreference"]}'


def delete_liked(user_id, place_id):
    db_sess = db_session.create_session()
    db_sess.query(LikePlaces).filter((LikePlaces.user_id == user_id) & (LikePlaces.place == place_id)).delete()
    db_sess.commit()


def add_liked(user_id, place_id):
    place1 = LikePlaces()
    place1.place = place_id
    place1.user_id = user_id
    db_sess = db_session.create_session()
    db_sess.add(place1)
    db_sess.commit()


def get_user_name(user_id):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == int(user_id)).all()[0]
    return user.login


def get_user_likes(user_id):
    db_sess = db_session.create_session()
    a = []
    for user in db_sess.query(LikePlaces).filter(LikePlaces.user_id == user_id).all():
        a.append(user.place)
    return a


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


if __name__ == "__main__":  # Запуск приложения при вызове модуля
    db_session.global_init("db/blogs.db")
    app.run()
