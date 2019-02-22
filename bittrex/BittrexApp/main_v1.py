#!-*-coding:utf-8-*-
import json
import sys
import ast
import urllib.error
import urllib.request
import cfscrape
import errno

from os import remove
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import uic
from PyQt5.QtCore import QPropertyAnimation, QRect, pyqtProperty, QThread, pyqtSlot, pyqtSignal, QRegExp
from PyQt5.QtGui import QPixmap, QPainter, QRegExpValidator
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QHBoxLayout, QLineEdit, QVBoxLayout
from PyQt5.QtWidgets import QHeaderView, QTableWidgetItem, QGridLayout, QDialog, QMessageBox, QCheckBox, QSizePolicy

from bittrex.API.bittrexV1 import Bittrex

(Ui_MainWindow, QMainWindow) = uic.loadUiType('window2.ui')
acc1 = Bittrex()


class MainWindow(QMainWindow):
    """MainWindow inherits QMainWindow"""
    dialog_answer = ''

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._dialog = None

    def __del__(self):
        self.ui = None

    @staticmethod
    def is_checked(btn):
        return btn.isChecked()
# END of MainWindow class


class PopUp(QWidget):
    """This class realize popup notifications with animation"""
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.label = QLabel()
        self.layout = QGridLayout()
        self.animation = QPropertyAnimation()
        self.popupOpacity = 1.0
        self.popup_timer = QtCore.QTimer()
        self.mainwindow_size = QRect()

        self.red = 0
        self.green = 0
        self.blue = 0
        self.alpha = 180

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
        self.animation.setTargetObject(self)
        b = bytearray()
        b.extend('total'.encode())
        self.animation.setPropertyName(b)
        self.animation.finished.connect(lambda: self.hide())

        # setup text
        self.label.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        # setup style
        self.label.setStyleSheet("QLabel { color : white; "
                                 "margin-top: 6px;"
                                 "margin-bottom: 6px;"
                                 "margin-left: 10px;"
                                 "margin-right: 10px; }")
        # set text in layout
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)
        self.popup_timer.timeout.connect(lambda: self.hide_animation())

    @pyqtProperty(float)
    def total(self):
        return self.popupOpacity

    @total.read
    def total(self):
        return self.get_popup_opacity()

    @total.write
    def total(self, popup_opacity):
        self.set_popup_opacity(popup_opacity)

    def __del__(self):
        self.ui = None

    def paintEvent(self, event):
        # set background for our window
        # it's rectangle with black background
        painter = QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # rect() returns inner geometry of our widget
        rounded_rect = QRect()
        rounded_rect.setX(self.rect().x() + 5)
        rounded_rect.setY(self.rect().y() + 5)
        rounded_rect.setWidth(self.rect().width() - 10)
        rounded_rect.setHeight(self.rect().height() - 10)

        # Set black colour in brush and transparency set 180 of 255
        painter.setBrush(QtGui.QColor(self.red, self.green, self.blue, self.alpha))
        # border of notification will not be highlighted
        painter.setPen(QtCore.Qt.NoPen)

        # Drawing background with rounding edges in 10px
        painter.drawRoundedRect(rounded_rect, 10, 10)

    def set_popup_text(self, text):
        # set text in label
        self.label.setText(text)
        # with recalculating of notification size
        self.adjustSize()

    def set_window_size(self, window):
        # you must set window size for right positioning of notification
        self.mainwindow_size = window

    def set_custom_color(self, red, green, blue, alpha=180):
        self.red = red
        self.green = green
        self.blue = blue
        self.alpha = alpha

    def show(self):
        # set transparency 0.0
        self.setWindowOpacity(0.0)
        # setting animation duration
        self.animation.setDuration(150)
        # totally nontransparent widget
        self.animation.setStartValue(0.0)
        # end with totally transparent widget
        self.animation.setEndValue(1.0)
        self.setGeometry(self.mainwindow_size.width() - 36 - self.width() + self.mainwindow_size.x(),
                         self.mainwindow_size.height() - 36 - self.height() + self.mainwindow_size.y(),
                         self.width(), self.height())
        QWidget.show(self)

        # animation start
        self.animation.start()
        self.popup_timer.start(3000)

    def hide_animation(self):
        self.popup_timer.stop()
        self.animation.setDuration(1000)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.start()

    def hide(self):
        # if widget already transparent
        if self.get_popup_opacity() == 0.0:
            QWidget.hide(self)

    def set_popup_opacity(self, opacity):
        self.popupOpacity = opacity
        self.setWindowOpacity(opacity)

    def get_popup_opacity(self):
        return self.popupOpacity
# END of popup class


class CustomTableWidgetItem(QTableWidgetItem):
    """Override __lt__ function for sorting in qt tables by the key"""
    def __init__(self, text, sort_key):
        QTableWidgetItem.__init__(self, text, QTableWidgetItem.UserType)
        self.sortKey = sort_key

    def __lt__(self, other):
        return self.sortKey < other.sortKey
# END of class CustomTableWidgetItem


class PubThread(QThread):
    # answer, order_history, order_book, markets_summaries

    sig_step_pub = pyqtSignal(dict, dict, dict, dict)

    def __init__(self, parent=None):
        print('PubThread created')
        QThread.__init__(self, parent)
        self.abort = False

    def __del__(self):
        print('PubThread deleted')
        self.abort = True
        self.wait()

    def run(self):
        while not self.abort and w.dialog_answer != '':
            print('PubThread running')
            answer, order_history, order_book, markets_summaries =\
                None, None, None, None
            try:
                answer = acc1.get_market_summary(w.dialog_answer)
                answer = str(answer).replace(']', '')
                answer = str(answer).replace('[', '')
                answer = json.loads(json.dumps(ast.literal_eval(answer)))
                print('Dialog(server_ask): ' + w.dialog_answer + ' Answer: ' + answer['result']['MarketName'])
                order_history = acc1.get_market_history(w.dialog_answer)
                order_book = acc1.get_order_book(w.dialog_answer, 'both')
                markets_summaries = acc1.get_market_summaries()
                if order_book is not None and answer is not None and order_history \
                        is not None:
                    # check if response is correct
                    if order_book['result'] != 'null' or answer['result'] != 'null' or order_history['result'] != 'null':
                        self.sig_step_pub.emit(answer, order_history, order_book, markets_summaries)
                    else:
                        notification_message('Incorrect currency!')
                else:
                    print('DEBUG: None_type detected in PubThread')
            except Exception as e:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(e).__name__, e.args)
                print(message)
                stop_update(self)
                QMessageBox.critical(w, 'Error', 'No internet connection')
# END PubThread


class AccThread(QThread):
    # balances, open orders, market_summaries (used for update balances)
    sig_step_acc = pyqtSignal(dict, dict, dict)

    def __init__(self, parent=None):
        print('AccThread created')
        QThread.__init__(self, parent)
        self.abort = False

    def __del__(self):
        print('AccThread deleted')
        self.abort = True
        self.wait()

    def run(self):
        while not self.abort and w.dialog_answer != '':
            print('AccThread running')
            balances, open_orders, markets_summaries =\
                None, None, None
            try:
                markets_summaries = acc1.get_market_summaries()
                balances = acc1.get_balances()
                open_orders = acc1.get_open_orders()
                if balances is not None and markets_summaries is not None:
                    # check if response is correct
                    if balances['result'] != 'null':
                        self.sig_step_acc.emit(markets_summaries, balances, open_orders)
                        self.sleep(30)
                    else:
                        notification_message('Incorrect currency!')
                else:
                    print('DEBUG: None_type detected in AccThread')
            except Exception as e:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(e).__name__, e.args)
                print(message)
                stop_update(self)
                QMessageBox.critical(w, 'Error', 'No internet connection')
# END AccThread


# Qt slots/signals START


@pyqtSlot(PubThread, name='start_update')
def start_update(thread_slot):
    thread_slot.abort = False
    thread_slot.start()


@pyqtSlot(AccThread, name='start_update')
def start_update(thread_slot):
    thread_slot.abort = False
    thread_slot.start()


@pyqtSlot(PubThread, name='stop_update')
def stop_update(thread_slot):
    thread_slot.abort = True
    thread_slot.exit()


@pyqtSlot(AccThread, name='stop_update')
def stop_update(thread_slot):
    thread_slot.abort = True
    thread_slot.exit()


@pyqtSlot(dict, dict, dict, dict, name='update')
def process_update_pub(answer, order_history, order_book, markets_summaries):
    set_pub_data(answer, order_history, order_book, markets_summaries)


@pyqtSlot(dict, dict, dict, name='update')
def process_update_acc(markets_summaries, balances, open_orders):
    set_acc_data(markets_summaries, balances, open_orders)
# Qt slots/signals END


def set_all_data(answer, order_book, order_history, markets_summaries, balances, open_orders):
    set_coin_info_data(answer)
    set_order_book_data(order_book)
    set_order_history_data(order_history)
    set_tab_bars_data(markets_summaries)
    set_balances_data(markets_summaries, balances)
    set_your_orders_data(open_orders)
# END of set_all_data


def set_pub_data(answer, order_history, order_book, markets_summaries):
    set_coin_info_data(answer)
    set_order_history_data(order_history)
    set_order_book_data(order_book)
    set_tab_bars_data(markets_summaries)
# END of set_pub_data


def set_acc_data(markets_summaries, balances, open_orders):
    set_balances_data(markets_summaries, balances)
    set_your_orders_data(open_orders)
# END of set_acc_data


class StaticThread(QThread):
    sig_step_stat = pyqtSignal(bytes)

    def __init__(self, parent=None):
        print('StaticThread created')
        QThread.__init__(self, parent)

    def __del__(self):
        print('StaticThread deleted')
        self.wait()

    def run(self):
        print('StaticThread started')
        if w.dialog_answer != '':
            try:
                markets = acc1.get_markets()
                img_file = b'\xff'
                if markets is not None and markets['success'] is True:
                    for markets_result in markets['result']:
                        if markets_result['MarketName'] == w.dialog_answer:
                            if markets_result['LogoUrl'] is not None:
                                # pass cf ddos protection
                                with cfscrape.create_scraper() as s:
                                    p = s.get(markets_result['LogoUrl'])
                                    img_file = p.content
                                # img_file = urllib.request.urlopen(markets_result['LogoUrl']).read()
                            else:
                                img_file = urllib.request.urlopen(
                                    'https://upload.wikimedia.org/wikipedia/commons/5/59/Empty.png'
                                ).read()
                    self.sig_step_stat.emit(img_file)
                else:
                    print('DEBUG: Nonetype detected in get_static_answer')

            except ConnectionError:
                notification_message('Currency info update error!')
            except Exception as e:
                # Except for unknown exceptions
                template = "An exception of type {0} occurred in static_answer. Arguments:\n{1!r}"
                message = template.format(type(e).__name__, e.args)
                print(message)


@pyqtSlot(bytes, name='static_update')
def process_update_stat(img_file):
    static_update(img_file)


class Login(QDialog):
    def __init__(self, parent=None):
        super(Login, self).__init__(parent)
        self.textName = QLineEdit(self)
        self.textPass = QLineEdit(self)
        self.buttonLogin = QPushButton('Login', self)
        self.buttonLogin.clicked.connect(self.handleLogin)
        self.rememberLogin = QCheckBox(self)
        self.data = dict()

        self.rememberLogin.setText('Remember me')
        self.textName.setEchoMode(QLineEdit.Password)
        self.textName.setInputMethodHints(QtCore.Qt.ImhHiddenText)
        self.textName.setPlaceholderText('KEY')
        self.textPass.setEchoMode(QLineEdit.Password)
        self.textPass.setInputMethodHints(QtCore.Qt.ImhHiddenText)
        self.textPass.setPlaceholderText('SECRET')

        try:
            with open("secret_test.json") as login_file:
                login_data = json.load(login_file)
                if login_data is not None:
                    self.textName.setText(login_data['key'])
                    self.textPass.setText(login_data['secret'])
                    self.rememberLogin.setChecked(True)
                login_file.close()
        except OSError as e:
            if e.errno != errno.ENOENT:  # errno.ENOENT = no such file or directory
                raise  # re-raise exception if a different error occurred

        layout = QVBoxLayout(self)
        layout.addWidget(self.textName)
        layout.addWidget(self.textPass)
        layout.addWidget(self.rememberLogin)
        layout.addWidget(self.buttonLogin)

    def handleLogin(self):
        if self.textName.text() != '' and self.textPass.text() != '':
            self.data['key'] = self.textName.text()
            self.data['secret'] = self.textPass.text()
            json_data = json.dumps(self.data)
            if self.rememberLogin.isChecked():
                login_data = open('secret_test.json', 'w')
                login_data.write(json_data)
                login_data.close()
            else:
                try:
                    remove('secret_test.json')
                except OSError as e:  # this would be "except OSError, e:" before Python 2.6
                    if e.errno != errno.ENOENT:  # errno.ENOENT = no such file or directory
                        raise  # re-raise exception if a different error occurred
            print(json_data)
            self.accept()
        else:
            QMessageBox.warning(self, 'Error', 'Empty login or password')


def static_update(img_file):
    web_graph(w.dialog_answer)
    pixmap = QPixmap()
    pixmap.fill(QtCore.Qt.transparent)
    pixmap.loadFromData(img_file)
    w.ui.imageLabel.setPixmap(pixmap.scaled(64, 64, QtCore.Qt.IgnoreAspectRatio,
                                            QtCore.Qt.FastTransformation))


def pub_clear():
    w.ui.imageLabel.clear()
    w.ui.nameLabel.clear()
    w.ui.volLabel.clear()
    w.ui.lowLabel_2.clear()
    w.ui.priceLabel.clear()
    w.ui.dailyChange.clear()
    w.ui.highLabel_2.clear()
    w.ui.orderBookTable.clearContents()
    w.ui.orderHistoryTable.clearContents()


def find_ticker():
    if w.ui.tickersTabWidget.currentIndex() == 0:
        num_row = w.ui.tickersTable_btc.rowCount()
        for i in range(0, num_row):
            w.ui.tickersTable_btc.setRowHidden(i, True)
        items = w.ui.tickersTable_btc.findItems(w.ui.findLine.text(), QtCore.Qt.MatchStartsWith)
        if items:
            for item in items:
                w.ui.tickersTable_btc.setRowHidden(item.row(), False)
        else:
            for i in range(0, num_row):
                w.ui.tickersTable_btc.setRowHidden(i, False)
    elif w.ui.tickersTabWidget.currentIndex() == 1:
        num_row = w.ui.tickersTable_eth.rowCount()
        for i in range(0, num_row):
            w.ui.tickersTable_eth.setRowHidden(i, True)
        items = w.ui.tickersTable_eth.findItems(w.ui.findLine.text(), QtCore.Qt.MatchStartsWith)
        if items:
            for item in items:
                w.ui.tickersTable_eth.setRowHidden(item.row(), False)
        else:
            for i in range(0, num_row):
                w.ui.tickersTable_eth.setRowHidden(i, False)
    elif w.ui.tickersTabWidget.currentIndex() == 2:
        num_row = w.ui.tickersTable_usdt.rowCount()
        for i in range(0, num_row):
            w.ui.tickersTable_usdt.setRowHidden(i, True)
        items = w.ui.tickersTable_usdt.findItems(w.ui.findLine.text(), QtCore.Qt.MatchStartsWith)
        if items:
            for item in items:
                w.ui.tickersTable_usdt.setRowHidden(item.row(), False)
        else:
            for i in range(0, num_row):
                w.ui.tickersTable_usdt.setRowHidden(i, False)


def table_init():
    """Setting up table parameters like rows, columns, headers"""
    w.ui.orderBookTable.setRowCount(20)
    w.ui.orderBookTable.setColumnCount(6)
    history_book_header = w.ui.orderBookTable.horizontalHeader()
    w.ui.orderBookTable.setHorizontalHeaderLabels(['TOTAL', 'SIZE', 'PRICE', 'PRICE', 'SIZE', 'TOTAL'])
    history_book_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
    history_book_header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
    for i in range(1, 5):
        history_book_header.setSectionResizeMode(i, QHeaderView.Stretch)

    w.ui.orderHistoryTable.setRowCount(20)
    w.ui.orderHistoryTable.setColumnCount(4)
    order_history_header = w.ui.orderHistoryTable.horizontalHeader()
    w.ui.orderHistoryTable.setHorizontalHeaderLabels(['', 'TIME', 'PRICE', 'SIZE'])
    order_history_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
    order_history_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
    for i in range(2, 4):
        order_history_header.setSectionResizeMode(i, QHeaderView.Stretch)

    w.ui.yourOrdersTable.setColumnCount(7)
    history_book_header = w.ui.yourOrdersTable.horizontalHeader()
    w.ui.yourOrdersTable.setHorizontalHeaderLabels(['', 'PAIR', 'TYPE', 'AMOUNT', 'PRICE', 'RESERVED', 'PLACED'])
    for i in range(0, 3):
        history_book_header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
    for i in range(3, 7):
        history_book_header.setSectionResizeMode(i, QHeaderView.Stretch)

    w.ui.tickersTable_btc.setColumnCount(4)
    tickers_table_header = w.ui.tickersTable_btc.horizontalHeader()
    w.ui.tickersTable_btc.setHorizontalHeaderLabels(['COIN', 'LAST', '24HR %', 'VOL'])
    for i in range(0, 4):
        tickers_table_header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
    tickers_table_header.setSectionResizeMode(1, QHeaderView.Stretch)
    tickers_table_header.show()

    w.ui.tickersTable_eth.setColumnCount(4)
    tickers_table_header = w.ui.tickersTable_eth.horizontalHeader()
    w.ui.tickersTable_eth.setHorizontalHeaderLabels(['COIN', 'LAST', '24HR %', 'VOL'])
    for i in range(0, 4):
        tickers_table_header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
    tickers_table_header.setSectionResizeMode(1, QHeaderView.Stretch)
    tickers_table_header.show()

    w.ui.tickersTable_usdt.setColumnCount(4)
    tickers_table_header = w.ui.tickersTable_usdt.horizontalHeader()
    w.ui.tickersTable_usdt.setHorizontalHeaderLabels(['COIN', 'LAST', '24HR %', 'VOL'])
    for i in range(0, 4):
        tickers_table_header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
    tickers_table_header.setSectionResizeMode(1, QHeaderView.Stretch)
    tickers_table_header.show()

    w.ui.balancesTable.setColumnCount(4)
    balances_table_header = w.ui.balancesTable.horizontalHeader()
    w.ui.balancesTable.setHorizontalHeaderLabels(['COIN', 'AMOUNT', 'EQUALS', '24HR %'])
    for i in range(1, 3):
        balances_table_header.setSectionResizeMode(i, QHeaderView.Stretch)
    balances_table_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
    balances_table_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
# END table_init


def qt_connections_setup():
    """ALL Qt elements connections in this function"""

    pub_thread.sig_step_pub.connect(process_update_pub)
    acc_thread.sig_step_acc.connect(process_update_acc)
    st_thread.sig_step_stat.connect(process_update_stat)
    pub_thread.finished.connect(lambda: print('PubFinished'))
    acc_thread.finished.connect(lambda: print('AccFinished'))
    st_thread.finished.connect(lambda: print('StaticFinished'))

    w.ui.actionUpdate.triggered.connect(lambda: start_update(pub_thread))
    w.ui.actionStop.triggered.connect(lambda: stop_update(pub_thread))
    w.ui.actionUpdate.triggered.connect(lambda: start_update(acc_thread))
    w.ui.actionNotificationTest.triggered.connect(lambda: notification_message("textlul"))
    w.ui.actionLogin.triggered.connect(lambda: login())
    w.ui.actionLog_out.triggered.connect(lambda: log_out())
    w.ui.actionStop.triggered.connect(lambda: stop_update(acc_thread))

    w.ui.findLine.textChanged.connect(lambda: find_ticker())
    w.ui.amountLine.textEdited.connect(lambda: total_calculation())
    w.ui.priceLine.textEdited.connect(lambda: total_calculation())
    w.ui.totalLine.textEdited.connect(lambda: amount_calculation())

    w.ui.buyButton.clicked.connect(lambda: limit_order('BUY'))
    w.ui.sellButton.clicked.connect(lambda: limit_order('SELL'))

    w.ui.tickersTable_btc.cellClicked.connect(
        lambda row, column: tickers_table_clicked(row, column, w.ui.tickersTable_btc))
    w.ui.tickersTable_btc.cellClicked.connect(lambda: pub_clear())
    w.ui.tickersTable_eth.cellClicked.connect(
        lambda row, column: tickers_table_clicked(row, column, w.ui.tickersTable_eth))
    w.ui.tickersTable_eth.cellClicked.connect(lambda: pub_clear())
    w.ui.tickersTable_usdt.cellClicked.connect(
        lambda row, column: tickers_table_clicked(row, column, w.ui.tickersTable_usdt))
    w.ui.tickersTable_usdt.cellClicked.connect(lambda: pub_clear())
# END Qt_connections_setup


def set_coin_info_data(answer):
    """function sets data about coin in labels on top of left panel"""
    w.ui.nameLabel.setText(w.dialog_answer)
    w.ui.volLabel.setText(U"VOL %.3f" % answer['result']['BaseVolume'])
    w.ui.lowLabel_2.setText(U"LOW %.8f" % answer['result']['Low'])
    w.ui.priceLabel.setText(U"LAST %.8f" % answer['result']['Last'])
    w.ui.dailyChange.setText(U"%.8f (%.2f%%)" %
                             ((float(answer['result']['Last']) - float(answer['result']['PrevDay'])),
                              (float(answer['result']['Last'])
                               / float(answer['result']['PrevDay']) - 1) * 100
                              )
                             )
    w.ui.highLabel_2.setText(U"HIGH %.8f" % answer['result']['High'])
# END set_coin_info_data


def set_tab_bars_data(markets_summaries):
    """function sets data in ONE table on ALL tabs"""
    right_corner_label = QLabel(w.ui.tickersTabWidget)
    right_corner_label.setText('TICKERS')
    w.ui.tickersTabWidget.setCornerWidget(right_corner_label, QtCore.Qt.TopRightCorner)
    right_corner_label.show()
    w.ui.tickersTable_btc.setRowCount(0)
    w.ui.tickersTable_eth.setRowCount(0)
    w.ui.tickersTable_usdt.setRowCount(0)
    if markets_summaries is not None:
        w.ui.tickersTable_btc.setSortingEnabled(False)
        w.ui.tickersTable_eth.setSortingEnabled(False)
        w.ui.tickersTable_usdt.setSortingEnabled(False)
        for index in range(0, len(markets_summaries['result'])):
            if "BTC-" in markets_summaries['result'][index]['MarketName']:
                set_tab_data(markets_summaries['result'][index], w.ui.tickersTable_btc)
            if "ETH-" in markets_summaries['result'][index]['MarketName']:
                set_tab_data(markets_summaries['result'][index], w.ui.tickersTable_eth)
            if "USDT-" in markets_summaries['result'][index]['MarketName']:
                set_tab_data(markets_summaries['result'][index], w.ui.tickersTable_usdt)
        if w.ui.findLine.text != '':
            find_ticker()
        w.ui.tickersTable_btc.setSortingEnabled(True)
        w.ui.tickersTable_eth.setSortingEnabled(True)
        w.ui.tickersTable_usdt.setSortingEnabled(True)
    else:
        print('DEBUG: Markets nonetype detected in tickers_update')
# END set_tab_bars_data


def set_tab_data(result, tab_table):
    """function sets data in ONE table on ONE tab"""
    tab_table.setSortingEnabled(False)
    market, currency = result['MarketName'].split('-')
    item = QTableWidgetItem(currency)
    item.setTextAlignment(QtCore.Qt.AlignCenter)
    tab_table.insertRow(tab_table.rowCount())
    tab_table.setItem(tab_table.rowCount() - 1, 0, item)
    item = CustomTableWidgetItem(U"%.8f" %
                                 result['Last'],
                                 result['Last'])
    item.setTextAlignment(QtCore.Qt.AlignCenter)
    tab_table.setItem(tab_table.rowCount() - 1, 1, item)
    item = CustomTableWidgetItem(
        U"(%.2f%%)" %
        ((abs((((result['Last']
                 - result['PrevDay'])
                / result['PrevDay']) * 100)))),
        (((result['Last']
           - result['PrevDay'])
          / result['PrevDay']) * 100))
    if (((result['Last']
          - result['PrevDay'])
         / result['PrevDay']) * 100) < 0:
        item.setForeground(QtGui.QColor(228, 74, 94, 255))
    elif (((result['Last']
            - result['PrevDay'])
           / result['PrevDay']) * 100) > 0:
        item.setForeground(QtGui.QColor(94, 185, 137, 255))
    item.setTextAlignment(QtCore.Qt.AlignCenter)
    tab_table.setItem(tab_table.rowCount() - 1, 2, item)
    item = CustomTableWidgetItem('%.3f' % round(result['BaseVolume'], 3),
                                 result['BaseVolume'])
    item.setTextAlignment(QtCore.Qt.AlignCenter)
    tab_table.setItem(tab_table.rowCount() - 1, 3, item)
    tab_table.setSortingEnabled(True)
# END set_tab_data


def tickers_table_clicked(row, column, table):
    # print("Row %d and Column %d was clicked" % (row, column))
    item = table.item(row, column)
    if column == 0:
        table, base_market = str(table.objectName()).split('_')
        w.dialog_answer = base_market + '-' + item.text()
        w.dialog_answer = w.dialog_answer.upper()
        if st_thread.isFinished():
            st_thread.start()


def update_tabs():
    """function for update by button, button needs request in function"""
    markets_summaries = acc1.get_market_summaries()
    set_tab_bars_data(markets_summaries)
# END update_tabs


def set_balances_data(markets_summaries, balances):
    """balances table data setup"""
    # get btc price
    bitcoin_usdt_price = None
    for index in range(0, len(markets_summaries['result'])):
        if markets_summaries['result'][index]['MarketName'] == 'USDT-BTC':
            bitcoin_usdt_price = markets_summaries['result'][index]['Last']
    # add records in table
    total_balance_btc = 0
    total_balance_usdt = 0
    w.ui.balancesTable.setRowCount(0)
    for index in range(0, len(balances['result'])):
        if balances['result'][index]['Balance'] != 0:
            item = QTableWidgetItem(balances['result'][index]['Currency'])
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            w.ui.balancesTable.insertRow(w.ui.balancesTable.rowCount())
            w.ui.balancesTable.insertRow(w.ui.balancesTable.rowCount())
            w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 2, 0, item)

            w.ui.balancesTable.setSpan(w.ui.balancesTable.rowCount() - 2, 0, 2, 1)

            item = QTableWidgetItem('%.8f' % balances['result'][index]['Balance'])
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 2, 1, item)
            item = QTableWidgetItem('%.8f' % balances['result'][index]['Available'])
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 1, 1, item)

            for market_index in range(0, len(markets_summaries['result'])):
                base_currency, market_currency = markets_summaries['result'][market_index]['MarketName'].split('-')
                if base_currency == 'BTC' and market_currency == balances['result'][index]['Currency']:
                    item = QTableWidgetItem(
                        '%.8f' % (markets_summaries['result'][market_index]['Last'] *
                                  balances['result'][index]['Balance']))
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                    w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 2, 2, item)
                    item = QTableWidgetItem('%.8f' % (markets_summaries['result'][market_index]['Last']
                                                      * balances['result'][index]['Balance']
                                                      * bitcoin_usdt_price))
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                    w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 1, 2, item)
                    total_balance_btc += markets_summaries['result'][market_index]['Last'] * balances['result'][index][
                        'Balance']
                    total_balance_usdt += markets_summaries['result'][market_index]['Last'] * balances['result'][index][
                        'Balance'] * bitcoin_usdt_price
                    # change in percents
                    item = CustomTableWidgetItem(
                        U"(%.2f%%)" % ((abs((((markets_summaries['result'][market_index]['Last'] -
                                               markets_summaries['result'][market_index]['PrevDay']) /
                                              markets_summaries['result'][market_index]['PrevDay']) * 100)))),
                        (((markets_summaries['result'][market_index]['Last'] -
                           markets_summaries['result'][market_index]['PrevDay']) /
                         markets_summaries['result'][market_index]['PrevDay']) * 100))
                    if (((markets_summaries['result'][market_index]['Last']
                          - markets_summaries['result'][market_index]['PrevDay'])
                         / markets_summaries['result'][market_index]['PrevDay']) * 100) < 0:
                        item.setForeground(QtGui.QColor(228, 74, 94, 255))
                    elif (((markets_summaries['result'][market_index]['Last']
                           - markets_summaries['result'][market_index]['PrevDay'])
                          / markets_summaries['result'][market_index]['PrevDay']) * 100) > 0:
                        item.setForeground(QtGui.QColor(94, 185, 137, 255))
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                    w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 2, 3, item)
                    w.ui.balancesTable.setSpan(w.ui.balancesTable.rowCount() - 2, 3, 2, 1)
                # Next if only for BTC and USDT values in balances table
                elif balances['result'][index]['Currency'] == 'BTC' or balances['result'][index]['Currency'] == 'USDT':
                    if market_currency == 'BTC' and base_currency == 'USDT':  # USDT-BTC market
                        item = QTableWidgetItem('%.8f' % balances['result'][index]['Balance'])
                        item.setTextAlignment(QtCore.Qt.AlignCenter)
                        w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 2, 2, item)
                        item = QTableWidgetItem(
                            '%.8f' % (balances['result'][index]['Balance'] * bitcoin_usdt_price))
                        item.setTextAlignment(QtCore.Qt.AlignCenter)
                        w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 1, 2, item)
                        total_balance_btc += balances['result'][index]['Balance']
                        total_balance_usdt += balances['result'][index]['Balance'] * bitcoin_usdt_price
                        # % change
                        item = CustomTableWidgetItem(
                            U"(%.2f%%)" % ((abs((((markets_summaries['result'][market_index]['Last'] -
                                                   markets_summaries['result'][market_index]['PrevDay']) /
                                                  markets_summaries['result'][market_index]['PrevDay']) * 100)))),
                            (((markets_summaries['result'][market_index]['Last'] -
                               markets_summaries['result'][market_index]['PrevDay']) /
                              markets_summaries['result'][market_index]['PrevDay']) * 100))
                        if (((markets_summaries['result'][market_index]['Last']
                              - markets_summaries['result'][market_index]['PrevDay'])
                             / markets_summaries['result'][market_index]['PrevDay']) * 100) < 0:
                            item.setForeground(QtGui.QColor(228, 74, 94, 255))
                        elif (((markets_summaries['result'][market_index]['Last']
                                - markets_summaries['result'][market_index]['PrevDay'])
                               / markets_summaries['result'][market_index]['PrevDay']) * 100) > 0:
                            item.setForeground(QtGui.QColor(94, 185, 137, 255))
                        item.setTextAlignment(QtCore.Qt.AlignCenter)
                        w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 2, 3, item)
                        w.ui.balancesTable.setSpan(w.ui.balancesTable.rowCount() - 2, 3, 2, 1)
                    elif base_currency == 'USDT':  # USDT
                        item = QTableWidgetItem(
                            '%.8f' % (balances['result'][index]['Balance'] / bitcoin_usdt_price))
                        item.setTextAlignment(QtCore.Qt.AlignCenter)
                        w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 2, 2, item)
                        item = QTableWidgetItem('%.8f' % balances['result'][index]['Balance'])
                        item.setTextAlignment(QtCore.Qt.AlignCenter)
                        w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 1, 2, item)
                        total_balance_btc += balances['result'][index]['Balance'] / bitcoin_usdt_price
                        total_balance_usdt += balances['result'][index]['Balance']
                        # % change
                        item = CustomTableWidgetItem(
                            U"(%.2f%%)" % ((abs((((markets_summaries['result'][market_index]['Last'] -
                                                   markets_summaries['result'][market_index]['PrevDay']) /
                                                  markets_summaries['result'][market_index]['PrevDay']) * 100)))),
                            (((markets_summaries['result'][market_index]['Last'] -
                               markets_summaries['result'][market_index]['PrevDay']) /
                              markets_summaries['result'][market_index]['PrevDay']) * 100))
                        if (((markets_summaries['result'][market_index]['Last']
                              - markets_summaries['result'][market_index]['PrevDay'])
                             / markets_summaries['result'][market_index]['PrevDay']) * 100) > 0:
                            item.setForeground(QtGui.QColor(228, 74, 94, 255))
                        elif (((markets_summaries['result'][market_index]['Last']
                                - markets_summaries['result'][market_index]['PrevDay'])
                               / markets_summaries['result'][market_index]['PrevDay']) * 100) < 0:
                            item.setForeground(QtGui.QColor(94, 185, 137, 255))
                        item.setTextAlignment(QtCore.Qt.AlignCenter)
                        w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 2, 3, item)
                        w.ui.balancesTable.setSpan(w.ui.balancesTable.rowCount() - 2, 3, 2, 1)
    w.ui.totalLabel.setText('TOTAL: %.8f BTC / %.2f USDT' % (total_balance_btc, total_balance_usdt))
# END set_balances_data


def set_your_orders_data(open_orders):
    """your orders table data setup"""
    w.ui.yourOrdersTable.setRowCount(0)
    for y_ord_result in open_orders['result']:
        w.ui.yourOrdersTable.insertRow(w.ui.yourOrdersTable.rowCount())
        item = QTableWidgetItem(y_ord_result['Exchange'])
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.yourOrdersTable.setItem(w.ui.yourOrdersTable.rowCount() - 1, 1, item)
        head, sep, tail = str(y_ord_result['OrderType']).partition('_')
        item = QTableWidgetItem(head)
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.yourOrdersTable.setItem(w.ui.yourOrdersTable.rowCount() - 1, 2, item)
        widget_1 = QWidget()
        if tail == 'SELL':
            btn = QPushButton()
            btn.setText('●')
            btn.setMaximumHeight(10)
            btn.setMaximumWidth(10)
            btn.setStyleSheet("QPushButton{background: transparent; color:rgba(228, 74, 94, 255);}"
                              "QPushButton:hover{background: transparent; color:rgba(0, 0, 0, 255); border:0px;}")
            btn.clicked.connect(lambda: cancel(y_ord_result['OrderUuid']))
            hBox = QHBoxLayout(widget_1)
            hBox.addWidget(btn)
            hBox.setAlignment(QtCore.Qt.AlignCenter)
            hBox.setContentsMargins(0, 0, 0, 0)
            widget_1.setLayout(hBox)
        elif tail == 'BUY':
            btn = QPushButton()
            btn.setText('●')
            btn.setMaximumHeight(10)
            btn.setMaximumWidth(10)
            btn.setStyleSheet("QPushButton{background: transparent; color:rgba(94, 185, 137, 255);}"
                              "QPushButton:hover{background: transparent; color:rgba(0, 0, 0, 255); border:0px;}")
            btn.clicked.connect(lambda: cancel(y_ord_result['OrderUuid']))
            hBox = QHBoxLayout(widget_1)
            hBox.addWidget(btn)
            hBox.setAlignment(QtCore.Qt.AlignCenter)
            hBox.setContentsMargins(0, 0, 0, 0)
            widget_1.setLayout(hBox)
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.yourOrdersTable.setCellWidget(w.ui.yourOrdersTable.rowCount() - 1, 0, widget_1)
        if y_ord_result['QuantityRemaining'] == y_ord_result['Quantity']:
            item = QTableWidgetItem(U"%.8f" % y_ord_result['QuantityRemaining'])
        else:
            item = QTableWidgetItem(U"%.8f/%.8f" % (y_ord_result['QuantityRemaining'],
                                                    y_ord_result['Quantity']))
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.yourOrdersTable.setItem(w.ui.yourOrdersTable.rowCount() - 1, 3, item)
        item = QTableWidgetItem(U"%.8f" % y_ord_result['Limit'])
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.yourOrdersTable.setItem(w.ui.yourOrdersTable.rowCount() - 1, 4, item)
        item = QTableWidgetItem(U"≈%.8f" % (y_ord_result['Quantity'] * y_ord_result['Limit']))
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.yourOrdersTable.setItem(w.ui.yourOrdersTable.rowCount() - 1, 5, item)
        item = QTableWidgetItem(str(y_ord_result['Opened']).split("T")[0])
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.yourOrdersTable.setItem(w.ui.yourOrdersTable.rowCount() - 1, 6, item)
# END set_your_orders_data


def set_order_book_data(order_book):
    """Order book table data setup"""
    total_buy = 0.
    total_sell = 0.
    for row in range(0, 20):
        total_buy += order_book['result']['buy'][row]['Quantity']
        item = QTableWidgetItem(U"%.2f" % total_buy)
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.orderBookTable.setItem(row, 0, item)
        item = QTableWidgetItem(U"%.8f" % order_book['result']['buy'][row]['Quantity'])
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.orderBookTable.setItem(row, 1, item)
        item = QTableWidgetItem(U"%.8f" % order_book['result']['buy'][row]['Rate'])
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.orderBookTable.setItem(row, 2, item)
        item = QTableWidgetItem(U"%.8f" % order_book['result']['sell'][row]['Rate'])
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.orderBookTable.setItem(row, 3, item)
        item = QTableWidgetItem(U"%.8f" % order_book['result']['sell'][row]['Quantity'])
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.orderBookTable.setItem(row, 4, item)
        total_sell += order_book['result']['sell'][row]['Quantity']
        item = QTableWidgetItem(U"%.2f" % total_sell)
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.orderBookTable.setItem(row, 5, item)
# END set_order_book_data


def set_order_history_data(order_history):
    """Order history table data setup"""
    for row in range(0, 20):
        if order_history['result'][row]['OrderType'] == 'BUY':
            item = QTableWidgetItem('▲')
            item.setForeground(QtGui.QColor(94, 185, 137, 255))
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            w.ui.orderHistoryTable.setItem(row, 0, item)
        elif order_history['result'][row]['OrderType'] == 'SELL':
            item = QTableWidgetItem('▼')
            item.setForeground(QtGui.QColor(228, 74, 94, 255))
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            w.ui.orderHistoryTable.setItem(row, 0, item)
        item = QTableWidgetItem(str(order_history['result'][row]['TimeStamp']).split("T")[1].split('.')[0])
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.orderHistoryTable.setItem(row, 1, item)
        item = QTableWidgetItem(U"%.8f" % order_history['result'][row]['Price'])
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.orderHistoryTable.setItem(row, 2, item)
        item = QTableWidgetItem(U"%.8f" % order_history['result'][row]['Quantity'])
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.orderHistoryTable.setItem(row, 3, item)
# END set_order_history_data


def web_graph(market):
    """function for launching js script with graph from tradingview"""
    # WARN: Error spamming opengl, probably qt intelHDgraphics bug, can't fix with UseOpenGLES
    # for index in reversed((range(w.ui.webLayout.count()))):
    #     w.ui.webLayout.itemAt(index).widget().setParent(None)
    head, sep, tail = market.partition('-')
    market = tail + head
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseDesktopOpenGL, True)
    web.setHtml(
        '''
        <!-- TradingView Widget BEGIN -->
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
            new TradingView.widget({
                "autosize": true,
                "symbol": "BITTREX:''' + market + '''",
                "interval": "30",
                "timezone": "Europe/Moscow",
                "theme": "Light",
                "style": "1",
                "locale": "en",
                "toolbar_bg": "rgba(255, 255, 255, 1)",
                "enable_publishing": false,
                "withdateranges": true,
                "hide_side_toolbar": false,
                "allow_symbol_change": false,
                "hideideas": true,
                "studies": [
                    "TripleEMA@tv-basicstudies"
                ]
            });
        </script>
        <!-- TradingView Widget END -->
        ''')
# END web_graph


def notification_message(text, r=0, g=0, b=0, alpha=180):
    """calls notification with our text"""
    popup.set_popup_text(text)
    popup.set_custom_color(r, g, b, alpha)
    popup.set_window_size(w.geometry())
    popup.show()
# END notification message


def cancel(y_ord_result):
    cancel_result = acc1.cancel(y_ord_result)
    if cancel_result['success']:
        notification_message('Success of deleting order', 94, 185, 137, 255)
    else:
        notification_message('Error when deleting order: ' + cancel_result['message'], 228, 74, 94, 255)


def limit_order(order_type):
    if order_type == 'BUY':
        order_result = acc1.buy_limit(w.dialog_answer, w.ui.amountLine.text(), w.ui.priceLine.text())
    elif order_type == 'SELL':
        order_result = acc1.sell_limit(w.dialog_answer, w.ui.amountLine.text(), w.ui.priceLine.text())
    else:
        order_result = None
        print('Got error type of order')
    if order_result is not None:
        if order_result['success']:
            notification_message('Success of setting order', 94, 185, 137, 255)
        else:
            notification_message('Error when setting order: ' + order_result['message'], 228, 74, 94, 255)


def login():
    global acc1
    login = Login()
    if login.exec_() == QDialog.Accepted:
        acc1 = Bittrex(login.data['key'], login.data['secret'])
        if acc1.get_balances()['success'] is not False:
            acc_elements(True)
            start_update(acc_thread)
            notification_message('Successful login', 94, 185, 137, 255)
        else:
            notification_message('Unsuccessful login attempt', 228, 74, 94, 255)
            log_out()


def log_out():
    global acc1
    stop_update(acc_thread)
    acc_elements(False)
    w.ui.balancesTable.clearContents()
    w.ui.yourOrdersTable.clearContents()
    acc1 = Bittrex()
    w.ui.totalLabel.setText('TOTAL:')


def acc_elements(enable):
    w.ui.balancesTable.setEnabled(enable)
    w.ui.yourOrdersTable.setEnabled(enable)
    w.ui.buyButton.setEnabled(enable)
    w.ui.sellButton.setEnabled(enable)
    w.ui.priceLine.setEnabled(enable)
    w.ui.amountLine.setEnabled(enable)
    w.ui.orderTypeBox.setEnabled(enable)
    w.ui.totalLine.setEnabled(enable)


def total_calculation():
    if w.ui.priceLine.text() != '' and w.ui.amountLine.text() != '':
        w.ui.totalLine.setText('%.8f' % (float(w.ui.amountLine.text()) * float(w.ui.priceLine.text())))
    else:
        w.ui.totalLine.setText('')


def amount_calculation():
    if w.ui.priceLine.text != '' and w.ui.totalLine.text() != '':
        w.ui.amountLine.setText('%.8f' % (float(w.ui.totalLine.text()) / float(w.ui.priceLine.text())))
    else:
        w.ui.amountLine.setText('')


if __name__ == '__main__':
    # create application
    app = QApplication(sys.argv)
    app.setApplicationName('Bittrex client')

    # create widget
    w = MainWindow()
    w.setWindowTitle('Bittrex client')
    w.show()

    # Disable unused elements
    acc_elements(False)

    # Additional elements initialization
    web = QWebEngineView()
    web.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    w.ui.webLayout.addWidget(web)
    web_graph('USDT-BTC')
    popup = PopUp()
    pub_thread = PubThread()
    acc_thread = AccThread()
    st_thread = StaticThread()

    w.ui.findLine.setPlaceholderText('FIND CURRENCY')
    w.ui.totalLine.setPlaceholderText('TOTAL')
    w.ui.totalLine.setValidator(QRegExpValidator(QRegExp("^([1-9][0-9]*|0)(\\.)[0-9]{8}")))
    w.ui.priceLine.setToolTip('PRICE')
    w.ui.priceLine.setPlaceholderText('PRICE')
    w.ui.priceLine.setValidator(QRegExpValidator(QRegExp("^([1-9][0-9]*|0)(\\.)[0-9]{8}")))
    w.ui.amountLine.setPlaceholderText('AMOUNT')
    w.ui.amountLine.setValidator(QRegExpValidator(QRegExp("^([1-9][0-9]*|0)(\\.)[0-9]{8}")))

    # tables setup
    table_init()

    # qt elements connections
    qt_connections_setup()

    # app_start
    w.dialog_answer = 'USDT-BTC'
    st_thread.start()
    start_update(pub_thread)

    # execute application
    sys.exit(app.exec_())
