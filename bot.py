import config
import telebot
from html.parser import HTMLParser
import urllib.request as urllib
import networkx as nx
import numpy as np
import matplotlib
import chardet
import requests
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import flask

WEBHOOK_URL_BASE = "https://{}:{}".format(config.WEBHOOK_HOST, config.WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/{}/".format(config.token)

bot = telebot.TeleBot(config.token, threaded=False)

bot.remove_webhook()

#bot.set_webhook(url=WEBHOOK_URL_BASE+WEBHOOK_URL_PATH, data={"url": ""})
requests.post(WEBHOOK_URL_BASE + WEBHOOK_URL_PATH, data={"url": ""})

all_text = ""

class BotParser(HTMLParser):
    def handle_data(self, data):
        global all_text
        english_counter = 0
        data = data.strip()
        for c in data:
            if ('a' <= c <= 'z') or ('A' <= c <= 'Z'):
                english_counter = english_counter + 1
        if (len(data) > 3) and (english_counter / len(data) < 0.5):
            all_text = all_text + data.strip() + '\n'
parser = BotParser()

app = flask.Flask(__name__)


def draw_net(nodes_number, word_list, Matrix, message):
    G = nx.Graph()
    for i in range(0, nodes_number):
        G.add_node(i)
    for i in range(0, nodes_number):
        for j in range(0, nodes_number):
            if Matrix[i][j] > 0:
                G.add_edge(i, j, weight=Matrix[i][j])

    labels={}
    for i in range(0, nodes_number):
        labels[i] = word_list[i][1]

    pos = nx.spring_layout(G, scale=50.0)
    nx.draw_networkx_nodes(G, pos, node_color='red', node_size=10)
    nx.draw_networkx_edges(G, pos, edge_color='yellow')
    nx.draw_networkx_labels(G, pos, labels, font_size=10, font_family='Arial')
    plt.axis('off')
    plt.savefig("graph.png", format="PNG")
    bot.send_photo(message.chat.id, open('graph.png', 'rb'), reply_to_message_id=message.message_id)
    plt.clf()

@bot.message_handler(content_types=["text"])
def repeat_all_messages(message):
    global all_text
    all_text = ""
    bot.send_message(message.chat.id, "Скачиваю страницу...")
    try:
        mt = message.text
        if (mt.find("github.com") > -1) and (mt.find("blob") > -1):
            mt = mt.replace("github.com", "raw.githubusercontent.com")
            mt = mt.replace("blob/", "")
        f = urllib.urlopen(mt)
    except:
        bot.send_message(message.chat.id, 'Текст сообщения не является веб-адресом')
        return
    fr = f.read()
    if chardet.detect(fr)['encoding'] == 'windows-1251':
        fr = fr.decode('cp1251').encode('utf8').decode('utf-8')
        data = str(fr)
    else:
        data = str(fr, 'utf-8', errors='replace')
    parser.feed(data)
    all_text_array = all_text.split()
    unique_words = set(all_text_array)
    bot.send_message(message.chat.id, "Встречаемость слов:")
    word_list = []
    for word in unique_words:
        english_counter = 0
        for c in word:
            if ('a' <= c <= 'z') or ('A' <= c <= 'Z'):
                english_counter = english_counter + 1
        if (len(word) > 3) and (english_counter / len(word) < 0.1):
            word_list.append( (all_text.count(str(word)), str(word)) )
    word_list.sort(reverse=True)
    max_words = min(len(word_list), 400)
    word_list = word_list[:max_words]
    word_list_str = ""
    max_top = 50
    t = 0
    for q, s in word_list:
        if t < max_top:
            word_list_str = word_list_str + s + ' ' + str(q) + '\n'
            t += 1
    bot.send_message(message.chat.id, word_list_str)

    bot.send_message(message.chat.id, "Строю матрицу совместной встречаемости...")
    Matrix = [[0 for x in range(max_words)] for y in range(max_words)]
    for y in range(0, max_words):
        print(str(y/max_words*100) + '%')
        for x in range(0, max_words):
            c = 0
            first = word_list[y][1]
            second = word_list[x][1]
            for i in range(0, len(all_text_array)):
                if all_text_array[i] == first:
                    for j in range(max(i - 3, 0), min(i + 4, len(all_text_array))):
                        if all_text_array[j] == second:
                            c = c + 1
            Matrix[y][x] = c

    bot.send_message(message.chat.id, "Рисую граф")
    bot.send_message(message.chat.id, str(max_words) + " наиболее встречающихся слов")
    draw_net(max_words, word_list, Matrix, message)
    bot.send_message(message.chat.id, str(max_words / 2) + " наиболее встречающихся слов")
    draw_net(int(max_words / 2), word_list, Matrix, message)
    bot.send_message(message.chat.id, str(max_words / 4) + " наиболее встречающихся слов")
    draw_net(int(max_words / 4), word_list, Matrix, message)
    bot.send_message(message.chat.id, str(max_words / 8) + " наиболее встречающихся слов")
    draw_net(int(max_words / 8), word_list, Matrix, message)
    bot.send_message(message.chat.id, str(max_words / 16) + " наиболее встречающихся слов")
    draw_net(int(max_words / 16), word_list, Matrix, message)
    bot.send_message(message.chat.id, "Вуаля!")


@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        flask.abort(403)


if __name__ == '__main__':
     bot.polling(none_stop=True)
