from flask import Flask, request, jsonify
import logging
import random
from geo import get_country

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)

cities = {
    'москва': ['1030494/b996c513d88bfbaf1dea', '1521359/485192c9573a1985e5fe'],
    'нью-йорк': ['997614/8f137be68a1f9ea406b9', '965417/a2ff9b10c33b65e65786'],
    'париж': ["937455/1dd1147726ee34623a27", '1540737/6cc1e109315af43276df']
}

sessionStorage = {}


@app.route('/post', methods=['POST'])
def main():
    logging.info('Request: %r', request.json)
    response = {
        'session': request.json['session'],
        'version': request.json['version'],
        'response': {
            'end_session': False
        }
    }
    handle_dialog(response, request.json)
    logging.info('Response: %r', response)
    return jsonify(response)


def handle_dialog(res, req):
    user_id = req['session']['user_id']
    if req['session']['new']:
        res['response']['text'] = 'Привет! Назови своё имя!'
        sessionStorage[user_id] = {
            'first_name': None, 
          'game_started': False,  
          'country_guess': False
        }
        return

    if sessionStorage[user_id]['first_name'] is None:
        first_name = get_first_name(req)
        if first_name is None:
            res['response']['text'] = 'Не расслышала имя. Повтори, пожалуйста!'
        else:
            sessionStorage[user_id]['first_name'] = first_name
            sessionStorage[user_id]['guessed_cities'] = []
            res['response']['text'] = f'Приятно познакомиться, {first_name.title()}. Я Алиса. Отгадаешь город по фото?'
            res['response']['buttons'] = [
                {
                    'title': 'Да',
                    'hide': True
                },
                {
                    'title': 'Нет',
                    'hide': True
                },
                {
                    'title': 'Помощь',
                    'hide': True
                }
            ]
    else:
        if not sessionStorage[user_id]['game_started']:
            if 'да' in req['request']['nlu']['tokens']:
                if len(sessionStorage[user_id]['guessed_cities']) == 3:
                    res['response']['text'] = 'Ты отгадал все города!'
                    res['end_session'] = True
                else:
                    sessionStorage[user_id]['game_started'] = True
                    sessionStorage[user_id]['attempt'] = 1
                    play_game(res, req)
            elif 'нет' in req['request']['nlu']['tokens']:
                res['response']['text'] = 'Ну и ладно!'
                res['end_session'] = True
            elif 'помощь' in req['request']['nlu']['tokens']:
                res['response']['text'] = '''У этой игры очень простые правила. \
Я показываю картинку города, а ты должен угадать город по ней. Сыграем?'''
                res['response']['buttons'] = [{'title': 'Да', 'hide': True}, {'title': 'Нет', 'hide': True}]
            elif 'покажи город на карте' in req['request']['command']:
                res['response']['text'] = 'Сыграем еще?'
                res['response']['buttons'] = [{'title': 'Да', 'hide': True}, {'title': 'Нет', 'hide': True}]
                return
            else:
                res['response']['text'] = 'Не поняла ответа! Так да или нет?'
                res['response']['buttons'] = [{'title': 'Да', 'hide': True}, {'title': 'Нет', 'hide': True}]
        else:
            play_game(res, req)


def play_game(res, req):
    user_id = req['session']['user_id']
    attempt = sessionStorage[user_id]['attempt']
    if attempt == 1 or not(sessionStorage[user_id]['game_started']):
        city = random.choice(list(cities))
        while city in sessionStorage[user_id]['guessed_cities']:
            city = random.choice(list(cities))
        sessionStorage[user_id]['city'] = city
        res['response']['card'] = {}
        res['response']['card']['type'] = 'BigImage'
        res['response']['card']['title'] = 'Что это за город?'
        res['response']['card']['image_id'] = cities[city][attempt - 1]
        res['response']['text'] = 'Тогда сыграем!'
    elif sessionStorage[user_id]['country_guess']:
        city = sessionStorage[user_id]['city']
        if get_country(req['request']['nlu']['tokens'][0]) == get_country(city):
            res['response']['text'] = 'Правильно! Сыграем ещё?'
        else:
            res['response']['text'] = f'Вы пытались. Это {get_country(city)} Сыграем ещё?'
        sessionStorage[user_id]['country_guess'] = False
        sessionStorage[user_id]['game_started'] = False
        res['response']['buttons'] = get_suggests(user_id, city)
        return
    else:
        city = sessionStorage[user_id]['city']
        if get_city(req) == city:
            res['response']['text'] = 'Правильно! А в какой стране этот город?'
            sessionStorage[user_id]['guessed_cities'].append(city)
            sessionStorage[user_id]['country_guess'] = True
            return
        else:
            if attempt == 3:
                res['response']['text'] = f'Вы пытались. Это {city.title()}. Сыграем ещё?'
                res['response']['buttons'] = get_suggests(user_id, city)
                sessionStorage[user_id]['game_started'] = False
                sessionStorage[user_id]['guessed_cities'].append(city)
                return
            else:
                res['response']['card'] = {}
                res['response']['card']['type'] = 'BigImage'
                res['response']['card']['title'] = 'Неправильно. Вот тебе дополнительное фото'
                res['response']['card']['image_id'] = cities[city][attempt - 1]
                res['response']['text'] = 'А вот и не угадал!'
    sessionStorage[user_id]['attempt'] += 1


def get_city(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.GEO':
            return entity['value'].get('city', None)


def get_first_name(req):
    for entity in req['request']['nlu']['entities']:
        if entity['type'] == 'YANDEX.FIO':
            return entity['value'].get('first_name', None)


def get_suggests(user_id, city):
    session = sessionStorage[user_id]
    suggests = [
    {
        "title": "Да",
        "hide": True
    },
    {
        "title": "Нет",
        "hide": True
    },
    {
        "title": "Покажи город на карте",
        "url": f"https://yandex.ru/maps/?mode=search&text={city}",
        "hide": True
    }]
    sessionStorage[user_id] = session
    return suggests



if __name__ == '__main__':
    app.run()
