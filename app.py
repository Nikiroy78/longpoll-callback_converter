from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.Qt import *
from threading import Thread
import mainwindow
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

import json, requests, os, random, pyperclip, traceback, vk_api

history_requests = list()
request_status = list()


def genToken(lenght=32, dictonary='0123456789abcdef'):
    TOKEN = ''
    for _ in range(lenght):
        TOKEN += dictonary[random.randint(0, len(dictonary) - 1)]
    return TOKEN


class callback_clientException(Exception):
    pass


class callback_server(Thread):
    def connect(self, group_id, server_url, secret_key, ret_str, ACCESS_TOKEN):
        global history_requests, request_status

        self.runned = False
        try:
            vk_session = vk_api.VkApi(token=ACCESS_TOKEN)
            vk = vk_session.get_api()
            self.longpoll = VkBotLongPoll(vk_session, group_id)
        except:
            print(traceback.format_exc())
            raise callback_clientException('Invalid session info')
        
        r_body = {
            "type": "confirmation",
            "group_id": group_id,
            "event_id": genToken(40),
            "secret": secret_key
        }
        request_status.append(0)
        history_requests.append(r_body)
        r = requests.post(server_url, json=r_body)
        if r.text != ret_str:
            request_status[history_requests.index(r_body)] = -1
            exc = callback_clientException('Invalid response code')
            exc.content = r.text
            raise exc
        else:
            request_status[history_requests.index(r_body)] = 1
            self.group_id = group_id
            self.secret_key = secret_key
            self.ret_str = ret_str
            self.server_url = server_url
            self.runned = True
            self.start()

    def run(self):
        global history_requests, request_status
        while True:
            try:
                for event in self.longpoll.listen():
            
                    if not(self.runned):
                        break
                    if 'obj' in dir(event):
                        r_body = {
                            "type": event.type.name.lower(),
                            "object": dict(event.object),
                            "group_id": self.group_id,
                            "event_id": genToken(40),
                            "secret": self.secret_key
                        }
                    else:
                        r_body = {
                            "type": event.name.lower(),
                            "group_id": self.group_id,
                            "event_id": genToken(40),
                            "secret": self.secret_key
                        }
                    request_status.append(0)
                    history_requests.append(r_body)
                    try:
                        r = requests.post(self.server_url, json=r_body)
                        if r.text != 'ok':
                            request_status[history_requests.index(r_body)] = -1
                        else:
                            request_status[history_requests.index(r_body)] = 1
                    except:
                        request_status[history_requests.index(r_body)] = -1
            except:
                pass
            if not(self.runned):
                break


def filtrating_integer(string: str):
    ret_str = ''
    for symbol in string:
        if symbol in '1234567890':
            ret_str += symbol
    return ret_str


class app_win(QMainWindow):
    def __init__(self, app):
        global history_requests
        super(app_win, self).__init__()
        self.ui = mainwindow.Ui_Form()
        self.ui.setupUi(self)
        self.setMouseTracking(True)
        self.callback_server = callback_server()

        # Other
        retStr_file = open('ret_str.txt', 'r', encoding='utf-8')
        self.ret_str = retStr_file.read()
        self.connected = False
        retStr_file.close()
        del retStr_file
        if not(self.ret_str):
            self.ret_str = genToken(8)
            retStr_file = open('ret_str.txt', 'wt', encoding='utf-8')
            retStr_file.write(self.ret_str)
            retStr_file.close()
            del retStr_file
        self.ui.ret_str.setText(f"Строка, которую должен вернуть сервер: {self.ret_str}")
        self.parsed_requests = list()
        self.parsed_responses = list()
        # Вызов старых данных
        secret_keyFile = open('secret_key.txt', 'r', encoding='utf-8')
        self.ui.secret_key.setText(secret_keyFile.read())
        tokenFile = open('token.txt', 'r', encoding='utf-8')
        self.ui.group_token.setText(tokenFile.read())
        group_idFile = open('group_id.txt', 'r', encoding='utf-8')
        self.ui.group_idInput.setText(group_idFile.read())
        server_urlFile = open('server_url.txt', 'r', encoding='utf-8')
        self.ui.server_url.setText(server_urlFile.read())

        secret_keyFile.close()
        tokenFile.close()
        group_idFile.close()
        server_urlFile.close()

        self.qtimer = QTimer()
        self.qtimer.timeout.connect(self.qTimer_void)
        self.qtimer.start(1)
        
        self.show()
        self.json_code_view = ''
        # Button's functions
        self.ui.copy_ret_str.clicked.connect(lambda: pyperclip.copy(self.ret_str))
        self.ui.gen_ret_str.clicked.connect(self.generate_returnString)
        self.ui.start.clicked.connect(self.connect_callback)
    
    def update_info_requests(self):
        global history_requests, request_status
        self.ui.requestsWidget.clear()
        for request in history_requests:
            r_status = request_status[history_requests.index(request)]
            item = QtWidgets.QListWidgetItem(request['type'])
            icon = QtGui.QIcon()
            if r_status == -1:
                icon.addPixmap(QtGui.QPixmap(":/response_codes/Failed.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            elif r_status == 1:
                icon.addPixmap(QtGui.QPixmap(":/response_codes/Sended.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            elif r_status == 0:
                icon.addPixmap(QtGui.QPixmap(":/response_codes/Sending.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
            item.setIcon(icon)
            self.ui.requestsWidget.addItem(item)
        
    def qTimer_void(self):
        global history_requests, request_status
        self.ui.start.setEnabled(bool(self.ui.server_url.text()) and bool(self.ui.group_idInput.text()) and bool(self.ui.group_token.text()) and not(self.connected))
        if self.parsed_requests != history_requests or self.parsed_responses != request_status:
            self.update_info_requests()
            self.parsed_requests = history_requests.copy()
            self.parsed_responses = request_status.copy()
        if self.ui.requestsWidget.currentRow() != -1:
            JSON_CONTENT = history_requests[self.ui.requestsWidget.currentRow()]
            JSON_CONTENT = json.dumps(JSON_CONTENT, ensure_ascii=False, indent=4)
            if self.json_code_view != JSON_CONTENT:
                self.json_code_view = JSON_CONTENT
                self.ui.requestBody.setText(self.json_code_view)
        if self.ui.group_idInput.text() != filtrating_integer(self.ui.group_idInput.text()):
            self.ui.group_idInput.setText(filtrating_integer(self.ui.group_idInput.text()))

    def connect_callback(self):
        try:
            if bool(self.ui.secret_key.text()):
                secret_key = self.ui.secret_key.text()
            else:
                secret_key = 'aaQ13axAPQEcczQa'
            self.callback_server.connect(
                group_id=int(self.ui.group_idInput.text()),
                server_url=self.ui.server_url.text(),
                secret_key=secret_key,
                ret_str=self.ret_str,
                ACCESS_TOKEN=self.ui.group_token.text()
            )
            # Записать данные
            secret_keyFile = open('secret_key.txt', 'wt', encoding='utf-8')
            secret_keyFile.write(self.ui.secret_key.text())
            tokenFile = open('token.txt', 'wt', encoding='utf-8')
            tokenFile.write(self.ui.group_token.text())
            group_idFile = open('group_id.txt', 'wt', encoding='utf-8')
            group_idFile.write(self.ui.group_idInput.text())
            server_urlFile = open('server_url.txt', 'wt', encoding='utf-8')
            server_urlFile.write(self.ui.server_url.text())

            secret_keyFile.close()
            tokenFile.close()
            group_idFile.close()
            server_urlFile.close()

            self.connected = True
            self.ui.work_status.setText("<html><head/><body><p><img src=\":/response_codes/Sended.png\"/> Сервер запущен!</p></body></html>")
            QMessageBox.information(self, 'Успех!', "Сервер подключён", QMessageBox.Ok)
        except Exception as exc:
            if 'session info' in str(exc):
                QMessageBox.critical(self, 'Блять!', "Неверный ключ сесии", QMessageBox.Ok)
            elif 'response code' in str(exc):
                QMessageBox.critical(self, 'Блять!', f"Сервер вернул не ту строку:\n{str(exc.content)}", QMessageBox.Ok)
            else:
                print(traceback.format_exc())
                QMessageBox.critical(self, 'Блять!', str(exc), QMessageBox.Ok)

    def generate_returnString(self):
        self.ret_str = genToken(8)
        retStr_file = open('ret_str.txt', 'wt', encoding='utf-8')
        retStr_file.write(self.ret_str)
        retStr_file.close()
        self.ui.ret_str.setText(f"Строка, которую должен вернуть сервер: {self.ret_str}")


app = QApplication([])

application = app_win(app)
app.exec()
os.abort()