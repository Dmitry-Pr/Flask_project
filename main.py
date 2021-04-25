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
from flask import request  # Для обработка запросов из форм
from flask import redirect  # Для автоматического перенаправления
import datetime  # Для получения текущей даты и врмени
from data import db_session

app = Flask(__name__)

pswd = ''
country = ''
a = []
point = ''
distance = ''


@app.route('/', methods=['GET', 'POST'])
def reg():
    if request.method == "POST":
        if 'sign_in' in request.form:
            return redirect('/sign_in')
        if len(request.form['login']) > 0 and len(request.form['password']) > 0:
            if 'regist' in request.form:
                global pswd
                global country
                country = request.form['country']
                log = request.form['login']
                pswd = request.form['password']
                if not user_in_base(log, pswd):
                    add_user(log, pswd)
                    id = get_user_id(log, pswd)
                    return redirect('/' + id)
                else:
                    return render_template('registration.html', flag=True, used=True)
        else:
            return render_template('registration.html', flag=False, used=False)

    else:
        return render_template('registration.html', flag=True, used=False)


@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if request.method == "POST":
        if 'sign' in request.form:
            if user_in_base(request.form['login'], request.form['password']):
                log = request.form['login']
                id = get_user_id(request.form['login'], request.form['password'])
                return redirect('/' + id)
            else:
                return render_template('sign_in.html', flag=False)

    else:
        return render_template('sign_in.html', flag=True)


@app.route("/<user_id>", methods=['GET', 'POST'])
def find(user_id):
    if request.method == 'POST':
        if 'out' in request.form:
            return redirect('/')
        elif 'place' in request.form:
            if len(request.form['place']) > 0:
                dist = request.form['dist'] if request.form['dist'] != '' else '500'
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
            return redirect('/' + user_id + '/' + request.form['place'] + '/' + request.form['dist'])
    all_places = get_all_places(place, dist, user_id)
    return render_template('index.html',
                           data=all_places,
                           login=user_id,
                           name=get_user_name(user_id),
                           text=place,
                           dist=dist)


# Обрабатываем пути вида user/XXX, где XXX - user_id
# Вызов страницы может быть методами с GET или POST
@app.route("/<user_id>/place/<place_id>", methods=['GET', 'POST'])
def user(user_id, place_id):
    global distance, point, a
    print(a)
    if request.method == "POST":  # Если были переданы данные из формы методом POST
        if 'delete_button' in request.form:  # Если была нажата кнопка delete_button
            place_delete_all_messages(place_id)  # То вызываем фукнцию удаления всех сообщений пользователя
        elif 'message_text' in request.form:  # Если была нажата кнопка отправки текста
            if len(request.form['message_text']) > 0:  # Если текст был введен
                add_message(place_id, request.form['message_text'], user_id)  # Вызываем функцию записи данных
        return redirect('/' + user_id + '/place/' + str(
            place_id))  # Необходимо еще раз перейти на эту страницу, но уже без вызова меода POST

    place_info = get_place_info(place_id)
    print(place_info)
    # place_comments = get_comments_about_place(place_id)  # Получить все сообщения пользователя

    # user_subscriptions = get_same_places(place_id)  # Получить ID всех подписок пользователя
    # user_subscriptions_info = []  #

    # for sub in user_subscriptions:
    #     subscription_id = sub['id']
    #     user_subscriptions_info.append(get_place_info(subscription_id))

    return render_template('user.html',
                           login=user_id,
                           place=place_info,
                           point=point,
                           distance=distance,
                           name=get_user_name(user_id)
                           # messages=place_comments,
                           # subscriptions=user_subscriptions_info,
                           )


@app.route("/<user_id>/likes", methods=['GET', 'POST'])
def likes(user_id):
    return render_template(
        'likes.html',
        login=user_id,
        data=get_user_likes(user_id)
    )


def dump(x):  # Для отладки
    return flask.json.dumps(x)


def get_place_info(place_id):  # Получить информацию о пользователе по user_id
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
        if len(photos) > 10:
            photos = photos[:10]
        d = {
            'place': res['name'],
            'photos': photos,
            'place_id': place_id,
            'rating': res['rating'],

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
    id = 0
    for i in range(len(res)):
        d = {}
        d['id'] = id
        d['place_id'] = res[i]['place_id']
        id += 1
        d['place'] = res[i]['name']
        try:
            d['pict'] = res[i]['photos'][0]['photo_reference']
        except KeyError:
            d['pict'] = 'Не найдено'
        d['country'] = res[i]['plus_code']['compound_code'].split()[-1]
        d['type'] = 'attraction'
        d['info'] = ''
        a.append(d)
        d['pict'] = get_pict(d['pict'])
        db_sess = db_session.create_session()
        ab = []
        for user in db_sess.query(LikePlaces).filter(LikePlaces.place == d["place_id"], LikePlaces.user_id == user_id):
            ab.append(user)
        if len(ab) > 0:
            d['liked'] = True
        else:
            d['liked'] = False
    all_places = [dict(row, n=i) for i, row in enumerate(a)]  # Создаем список строк из таблицы
    return all_places


def get_comments_about_place(place_id):  # Получить все сообщения пользователя user_id
    connection = engine.connect()  # Подключаемся к базе
    # Все сообщения для которых user_id = user_id,
    # отсортированные по времени от новых к старым
    messages_table = connection.execute("select * from message where place_id=%s order by time DESC", place_id)
    connection.close()  # Закрываем подключение к базе
    messages = [dict(row) for row in messages_table]  # Создаем список строк из таблицы
    return messages


def place_delete_all_messages(place_id):  # Удалить все сообщения пользователя user_id
    connection = engine.connect()  # Подключаемся к базе
    trans = connection.begin()  # Запускаем транзакцию
    connection.execute("DELETE FROM message WHERE place_id=%s", place_id)  # Запрос на удаление строк из таблицы
    trans.commit()  # Применяем транзакцию
    connection.close()
    return


def get_same_places(place_id):  # Получить список всех подписок пользователя
    connection = engine.connect()  # Подключаемся к базе
    type = list(connection.execute('select type from Places where id = %s', place_id))[0]
    subscriptions_table = connection.execute("select * from Places where type = %s",
                                             type)  # Все подписки для которых user1_id = user_id
    connection.close()  # Закрываем подключение к базе
    subscriptions = [dict(row) for row in subscriptions_table if
                     dict(row)['id'] != place_id]  # Создаем список строк из таблицы
    return subscriptions


def add_user(log, pswd):
    user = User()
    user.login = log
    user.password = pswd
    db_sess = db_session.create_session()
    db_sess.add(user)
    db_sess.commit()


def add_message(place_id, message_text, login):  # Сохранить сообщение пользователя в базу
    connection = engine.connect()  # Устанавливаем соединение
    trans = connection.begin()  # Открываем транзакцию
    current_time = datetime.datetime.now()  # Получаем теущие дату и время

    # Записываем данные в таблицу
    connection.execute("INSERT INTO message(place_id, text, time, user) VALUES (%s, %s, %s, %s)",
                       (place_id, message_text, current_time, login))

    trans.commit()  # Применяем транзакцию
    connection.close()

    return


def user_in_base(log, pswd):
    db_sess = db_session.create_session()
    a = []
    for user in db_sess.query(User).filter((User.login == log) & (User.password == pswd)):
        a.append(user)

    if len(list(a)) > 0:
        return True
    return False


def get_user_id(log, pswd):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter((User.login == log) & (User.password == pswd)).first()
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
    pass


def add_liked(user_id, place_id):
    pass


def get_user_name(user_id):
    pass


def get_user_likes(user_id):
    return {}


if __name__ == "__main__":  # Запуск приложения при вызове модуля
    db_session.global_init("db/blogs.db")
    app.run()
