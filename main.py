# -*- coding: utf-8 -*-

import sys
import os
import flask
import requests

from flask import Flask  # Подключаем Flask
from flask import render_template  # Подключаем библиотеку для работы с шаблонами
from sqlalchemy import create_engine  # Подключаем библиотеку для работы с базой данных

from flask import request  # Для обработка запросов из форм
from flask import redirect  # Для автоматического перенаправления
import datetime  # Для получения текущей даты и врмени
from data import db_session

# Создаем связь с базой данных
# XXX - заменить на Ваш номер
# YYY - заменить на Ваш пароль из Яндекс.Контеста, К КОТОРОМУ В НАЧАЛЕ ПРИПИСАНО ЧЕТЫРЕ СИМВОЛА Qq!1

username = "cshse_64"
passwd = "Qq!1bD9aQJUd5Y"
db_name = "cshse_64"

# Раскомментировать после указания базы, логина и пароля
# engine = create_engine("mysql://" + username + ":" + passwd + "@localhost/" + db_name + "?charset=utf8", pool_size=10,
#                        max_overflow=20, echo=True)

# Создаем приложение
app = Flask(__name__)

log = ''
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
                global log
                global pswd
                global country
                country = request.form['country']
                log = request.form['login']
                pswd = request.form['password']
                if not user_in_base(log, pswd):
                    add_user(log, pswd, country)
                    return redirect('/' + log)
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
                global log
                log = request.form['login']
                return redirect('/' + log)
            else:
                return render_template('sign_in.html', flag=False)

    else:
        return render_template('sign_in.html', flag=True)


@app.route("/<login>", methods=['GET', 'POST'])
def find(login):
    if request.method == 'POST':
        if 'place' in request.form:
            if len(request.form['place']) > 0:
                dist = request.form['dist'] if request.form['dist'] != '' else '500'
                return redirect('/' + login + '/' + request.form['place'] + '/' + dist)
    return render_template('index.html', data={}, login=login, text='', dist='')


@app.route("/<login>/<place>/<dist>", methods=['GET', 'POST'])  # Обрабатываем корневой путь
def main(login, place, dist):
    global point, distance
    point = place
    distance = dist
    if request.method == 'POST':
        if 'out' in request.form:
            return redirect('/')
        else:
            return redirect('/' + login + '/' + request.form['place'] + '/' + request.form['dist'])
    all_places = get_all_places(place, dist)
    return render_template('index.html',
                           data=all_places,
                           login=login,
                           text=place,
                           dist=dist)  # Вызываем шаблон main.html, в который в качестве data передано all_users


# Обрабатываем пути вида user/XXX, где XXX - user_id  
# Вызов страницы может быть методами с GET или POST
@app.route("/<login>/place/<int:place_id>", methods=['GET', 'POST'])
def user(login, place_id):
    global distance, point, a
    print(a)
    if request.method == "POST":  # Если были переданы данные из формы методом POST
        if 'delete_button' in request.form:  # Если была нажата кнопка delete_button
            place_delete_all_messages(place_id)  # То вызываем фукнцию удаления всех сообщений пользователя
        elif 'message_text' in request.form:  # Если была нажата кнопка отправки текста
            if len(request.form['message_text']) > 0:  # Если текст был введен
                add_message(place_id, request.form['message_text'], login)  # Вызываем функцию записи данных
        return redirect('/' + login + '/place/' + str(
            place_id))  # Необходимо еще раз перейти на эту страницу, но уже без вызова меода POST

    user_info = get_place_info(place_id)
    print(user_info)
    # place_comments = get_comments_about_place(place_id)  # Получить все сообщения пользователя

    # user_subscriptions = get_same_places(place_id)  # Получить ID всех подписок пользователя
    # user_subscriptions_info = []  #

    # for sub in user_subscriptions:
    #     subscription_id = sub['id']
    #     user_subscriptions_info.append(get_place_info(subscription_id))

    return render_template('user.html',
                           login=login,
                           user=user_info,
                           point=point,
                           distance=distance
                           # messages=place_comments,
                           # subscriptions=user_subscriptions_info,
                           )


def dump(x):  # Для отладки
    return flask.json.dumps(x)


def get_place_info(place_id):  # Получить информацию о пользователе по user_id
    global a
    place_info = {}
    for el in a:
        if el['id'] == place_id:
            place_info = el
            break
    return place_info


def get_all_places(place, dist):  # Получить список информации о всех пользователях
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
        params = {
            'key': 'AIzaSyCO-AM_xATjnsGaC8xZXAfoVsg7RSriD8A',
            'maxwidth': '400',
            'photoreference': d['pict']
        }
        serv = 'https://maps.googleapis.com/maps/api/place/photo'
        response = requests.get(serv, params=params)
        d['pict'] = response.url
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


def add_user(log, pswd, country):
    connection = engine.connect()  # Устанавливаем соединение
    trans = connection.begin()  # Открываем транзакцию
    connection.execute("INSERT INTO user(login, password, country) VALUES (%s, %s, %s)",
                       (log, pswd, country))

    trans.commit()  # Применяем транзакцию
    connection.close()


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
    connection = engine.connect()
    res = connection.execute("select * from user where login = %s and password = %s", (log, pswd))
    connection.close()
    if len(list(res)) > 0:
        return True
    return False


if __name__ == "__main__":  # Запуск приложения при вызове модуля
    db_session.global_init("db/blogs.db")
    app.run()
