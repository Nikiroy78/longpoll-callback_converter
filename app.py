from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.Qt import *
from threading import Thread
import mainwindow
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

import json, requests, os, random, pyperclip, traceback, vk_api

history_requests = list()
request_status = list()
history_responses = list()

try:
    os.mkdir('saves');
except Exception as exc:
    pass


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
        history_responses.append('<p>Ждём ответа от сервера...</p>')
        r = requests.post(server_url, json=r_body)
        try:
            history_responses[history_requests.index(r_body)] = r.text
        except:
            history_responses[history_requests.index(r_body)] = f"<p>Ошибка сервера: {r.statusCode}</p>"
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
                    history_responses.append('<p>Ждём ответа от сервера...</p>')
                    try:
                        r = requests.post(self.server_url, json=r_body)
                        try:
                            history_responses[history_requests.index(r_body)] = r.text
                        except:
                            history_responses[history_requests.index(r_body)] = f"<p>Ошибка сервера: {r.statusCode}</p>"
                        
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
        
        self.saves = list()
        
        for root, dirs, files in os.walk('saves'):
            for _dir in dirs:
                files_in_dir = list()
                for _root, _dirs, _files in os.walk(f"saves/{_dir}"):
                    for file in _files:
                        files_in_dir.append(file)
                if ('group_id.txt' in files_in_dir) and ('ret_str.txt' in files_in_dir) and ('secret_key.txt' in files_in_dir) and ('server_url.txt' in files_in_dir) and ('token.txt' in files_in_dir):
                    self.saves.append(_dir)
                    self.ui.saveList.addItem(_dir)

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
        self.ui.new_saveButton.clicked.connect(self.new_saveSession)
        self.ui.loadButton.clicked.connect(self.loadSession)
        self.ui.saveButton.clicked.connect(self.saveSession)
    
    def loadSession(self):
        text = self.ui.saveList.currentText()
        with open('group_id.txt', 'wb') as f:
            with open(f"saves/{text}/group_id.txt", 'rb') as fs:
                content = fs.read()
                f.write(content)
                self.ui.group_idInput.setText(content.decode("utf-8"))
        with open('ret_str.txt', 'wb') as f:
            with open(f"saves/{text}/ret_str.txt", 'rb') as fs:
                content = fs.read()
                f.write(content)
                self.ui.ret_str.setText(f"Строка, которую должен вернуть сервер: {content.decode('utf-8')}")
        with open('secret_key.txt', 'wb') as f:
            with open(f"saves/{text}/secret_key.txt", 'rb') as fs:
                content = fs.read()
                f.write(content)
                self.ui.secret_key.setText(content.decode('utf-8'))
        with open('server_url.txt', 'wb') as f:
            with open(f"saves/{text}/server_url.txt", 'rb') as fs:
                content = fs.read()
                f.write(content)
                self.ui.server_url.setText(content.decode('utf-8'))
        with open('token.txt', 'wb') as f:
            with open(f"saves/{text}/token.txt", 'rb') as fs:
                content = fs.read()
                f.write(content)
                self.ui.group_token.setText(content.decode('utf-8'))
    
    def saveSession(self):
        text = self.ui.saveList.currentText()
        if True:
            try:
                with open('group_id.txt', 'rb') as f:
                    with open(f"saves/{text}/group_id.txt", 'wb') as fs:
                        fs.write(f.read())
                with open('ret_str.txt', 'rb') as f:
                    with open(f"saves/{text}/ret_str.txt", 'wb') as fs:
                        fs.write(f.read())
                with open('secret_key.txt', 'rb') as f:
                    with open(f"saves/{text}/secret_key.txt", 'wb') as fs:
                        fs.write(f.read())
                with open('server_url.txt', 'rb') as f:
                    with open(f"saves/{text}/server_url.txt", 'wb') as fs:
                        fs.write(f.read())
                with open('token.txt', 'rb') as f:
                    with open(f"saves/{text}/token.txt", 'wb') as fs:
                        fs.write(f.read())
            except Exception as exc:
                pass
    
    def new_saveSession(self):
        text, ok = QInputDialog.getText(self, 'Сохранить сессию', 'Введите имя сессии:')
        if ok and not(text in self.saves):
            try:
                os.mkdir(f"saves/{text}")
                with open('group_id.txt', 'rb') as f:
                    with open(f"saves/{text}/group_id.txt", 'wb') as fs:
                        fs.write(f.read())
                with open('ret_str.txt', 'rb') as f:
                    with open(f"saves/{text}/ret_str.txt", 'wb') as fs:
                        fs.write(f.read())
                with open('secret_key.txt', 'rb') as f:
                    with open(f"saves/{text}/secret_key.txt", 'wb') as fs:
                        fs.write(f.read())
                with open('server_url.txt', 'rb') as f:
                    with open(f"saves/{text}/server_url.txt", 'wb') as fs:
                        fs.write(f.read())
                with open('token.txt', 'rb') as f:
                    with open(f"saves/{text}/token.txt", 'wb') as fs:
                        fs.write(f.read())
                
                self.saves.append(text)
                self.ui.saveList.addItem(text)
            except Exception as exc:
                pass
    
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
        self.ui.loadButton.setEnabled(len(self.saves) > 0)
        self.ui.saveButton.setEnabled(len(self.saves) > 0)
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
                self.ui.responseBody.setText(history_responses[self.ui.requestsWidget.currentRow()])
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