#!-*-coding:utf-8-*-
import json
import sys
import time
import urllib.error
import urllib.request

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import uic
from PyQt5.QtCore import QPropertyAnimation, QRect, pyqtProperty, QThread, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter
from PyQt5.QtWebEngineWidgets import *
from PyQt5.QtWidgets import QApplication, QLineEdit, QInputDialog, QWidget, QLabel
from PyQt5.QtWidgets import QHeaderView, QTableWidgetItem, QGridLayout

from bittrex.API.bittrexV2 import BittrexV2

(Ui_MainWindow, QMainWindow) = uic.loadUiType('window2.ui')


class MainWindow(QMainWindow):
    """MainWindow inherits QMainWindow"""
    dialog_answer = ''

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._dialog = None

    def __del__(self):
        self.ui = None

    def dialog_btc(self):
        w.dialog_answer = ''
        text, ok_pressed = QInputDialog.getText(self, "BTC market", "Input currency:", QLineEdit.Normal, "")
        if ok_pressed and text != '':
            self.dialog_answer = "BTC-" + text

    def dialog_eth(self):
        w.dialog_answer = ''
        text, ok_pressed = QInputDialog.getText(self, "ETH market", "Input currency:", QLineEdit.Normal, "")
        if ok_pressed and text != '':
            self.dialog_answer = "ETH-" + text

    def dialog_usdt(self):
        w.dialog_answer = ''
        text, ok_pressed = QInputDialog.getText(self, "USDT market", "Input currency:", QLineEdit.Normal, "")
        if ok_pressed and text != '':
            self.dialog_answer = "USDT-" + text

    @staticmethod
    def is_checked(btn):
        return btn.isChecked()
# END of MainWindow class

class PopUp(QWidget):
    """This class realize popup notifications with animation"""
    def __init__(self, parent=None):
        super(PopUp, self).__init__(parent)
        self.label = QLabel()
        self.layout = QGridLayout()
        self.animation = QPropertyAnimation()
        self.popupOpacity = 1.0
        self.popup_timer = QtCore.QTimer()
        self.mainwindow_size = QRect()

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
        painter.setBrush(QtGui.QColor(0, 0, 0, 180))
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


class AThread(QThread):

    sig_step = pyqtSignal(dict, dict, dict, dict, dict, dict)

    def __init__(self):
        super(AThread, self).__init__()
        self.abort = False

    def run(self):
        self.abort = False
        while not self.abort and w.dialog_answer != '':
            print('Thread running')
            try:
                answer = acc2.get_market_summary(w.dialog_answer)
                print('Dialog(server_ask): ' + w.dialog_answer + ' Answer: ' + answer['result']['MarketName'])
                order_book = acc2.get_market_order_book(w.dialog_answer)
                order_history = acc2.get_market_history(w.dialog_answer)
                markets_summaries = acc2.get_market_summaries()
                balances = acc2.get_balances()
                open_orders = acc2.get_open_orders()
                self.sig_step.emit(answer, order_book, order_history, markets_summaries, balances, open_orders)
                time.sleep(1)
            except ConnectionError:
                notification_message('Order book update error!')
            except Exception as e:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(e).__name__, e.args)
                print(message)
# END AThread


@pyqtSlot(AThread)
def start_update(thread):
    thread.start()


@pyqtSlot(AThread)
def stop_update(thread):
    thread.abort = True


@pyqtSlot(dict, dict, dict, dict, dict, dict)
def process_update(answer, order_book, order_history, markets_summaries, balances, open_orders):
    update_all(answer, order_book, order_history, markets_summaries, balances, open_orders)


def update_all(answer, order_book, order_history, markets_summaries, balances, open_orders):
    set_coin_info_data(answer)
    set_order_book_data(order_book)
    set_order_history_data(order_history)
    set_tab_bars_data(markets_summaries)
    set_balances_data(markets_summaries, balances)
    set_your_orders_data(open_orders)


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
    thread.sig_step.connect(process_update)

    w.ui.actionBTC.triggered.connect(lambda: w.dialog_btc())
    w.ui.actionBTC.triggered.connect(lambda: get_answer())
    w.ui.actionBTC.triggered.connect(lambda: get_static_answer())
    w.ui.actionETH.triggered.connect(lambda: w.dialog_eth())
    w.ui.actionETH.triggered.connect(lambda: get_answer())
    w.ui.actionETH.triggered.connect(lambda: get_static_answer())
    w.ui.actionUSDT.triggered.connect(lambda: w.dialog_usdt())
    w.ui.actionUSDT.triggered.connect(lambda: get_answer())
    w.ui.actionUSDT.triggered.connect(lambda: get_static_answer())
    # w.ui.actionUpdate.triggered.connect(lambda: timer.start(5000))
    # w.ui.actionStop.triggered.connect(lambda: timer.stop())
    w.ui.actionUpdate.triggered.connect(lambda: start_update(thread))
    w.ui.actionStop.triggered.connect(lambda: stop_update(thread))
    w.ui.updateButton.clicked.connect(lambda: update_tabs())
    w.ui.actionNotificationTest.triggered.connect(lambda: notification_message("textlul"))
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
                               / float(answer['result']['PrevDay']) - 1)
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
    print(type(w.ui.tickersTabWidget.cornerWidget()))
    w.ui.tickersTable_btc.setRowCount(0)
    w.ui.tickersTable_eth.setRowCount(0)
    w.ui.tickersTable_usdt.setRowCount(0)
    if markets_summaries is not None:
        w.ui.tickersTable_btc.setSortingEnabled(False)
        for result in markets_summaries['result']:
            if "BTC-" in result['Market']['MarketName']:
                set_tab_data(result, w.ui.tickersTable_btc)
            if "ETH-" in result['Market']['MarketName']:
                set_tab_data(result, w.ui.tickersTable_eth)
            if "USDT-" in result['Market']['MarketName']:
                set_tab_data(result, w.ui.tickersTable_usdt)
        w.ui.tickersTable_btc.setSortingEnabled(True)
    else:
        print('DEBUG: Markets nonetype detected in tickers_update')
# END set_tab_bars_data


def set_tab_data(result, tab_table):
    """function sets data in ONE table on ONE tab"""
    tab_table.setSortingEnabled(False)
    item = QTableWidgetItem(result['Market']['MarketCurrency'])
    item.setTextAlignment(QtCore.Qt.AlignCenter)
    tab_table.insertRow(tab_table.rowCount())
    tab_table.setItem(tab_table.rowCount() - 1, 0, item)
    item = CustomTableWidgetItem(U"%.8f" %
                                 result['Summary']['Last'],
                                 result['Summary']['Last'])
    item.setTextAlignment(QtCore.Qt.AlignCenter)
    tab_table.setItem(tab_table.rowCount() - 1, 1, item)
    item = CustomTableWidgetItem(
        U"(%.2f%%)" %
        ((abs((((result['Summary']['Last']
                 - result['Summary']['PrevDay'])
                / result['Summary']['PrevDay']) * 100)))),
        (((result['Summary']['Last']
           - result['Summary']['PrevDay'])
          / result['Summary']['PrevDay']) * 100))
    if (((result['Summary']['Last']
          - result['Summary']['PrevDay'])
         / result['Summary']['PrevDay']) * 100) < 0:
        item.setForeground(QtGui.QColor(228, 74, 94, 255))
    elif (((result['Summary']['Last']
            - result['Summary']['PrevDay'])
           / result['Summary']['PrevDay']) * 100) > 0:
        item.setForeground(QtGui.QColor(94, 185, 137, 255))
    item.setTextAlignment(QtCore.Qt.AlignCenter)
    tab_table.setItem(tab_table.rowCount() - 1, 2, item)
    item = CustomTableWidgetItem('%.3f' % round(result['Summary']['BaseVolume'], 3),
                                 result['Summary']['BaseVolume'])
    item.setTextAlignment(QtCore.Qt.AlignCenter)
    tab_table.setItem(tab_table.rowCount() - 1, 3, item)
    tab_table.setSortingEnabled(True)
# END set_tab_data


def update_tabs():
    """function for update by button, button needs request in function"""
    markets_summaries = acc2.get_market_summaries()
    set_tab_bars_data(markets_summaries)
# END update_tabs


def set_balances_data(markets_summaries, balances):
    """balances table data setup"""
    # get btc price
    bitcoin_usdt_price = None
    for bitcoin_only in markets_summaries['result']:
        if bitcoin_only['Market']['MarketName'] == 'USDT-BTC':
            bitcoin_usdt_price = bitcoin_only['Summary']['Last']
    # add records in table
    total_balance_btc = 0
    total_balance_usdt = 0
    w.ui.balancesTable.setRowCount(0)
    for balances_result in balances['result']:
        if balances_result['Balance']['Balance'] != 0:
            print(balances_result['Balance']['Balance'])
            item = QTableWidgetItem(balances_result['Balance']['Currency'])
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            w.ui.balancesTable.insertRow(w.ui.balancesTable.rowCount())
            w.ui.balancesTable.insertRow(w.ui.balancesTable.rowCount())
            w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 2, 0, item)

            w.ui.balancesTable.setSpan(w.ui.balancesTable.rowCount() - 2, 0, 2, 1)

            item = QTableWidgetItem('%.8f' % balances_result['Balance']['Balance'])
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 2, 1, item)
            item = QTableWidgetItem('%.8f' % balances_result['Balance']['Available'])
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 1, 1, item)

            for markets_sum_result in markets_summaries['result']:
                if markets_sum_result['Market']['BaseCurrency'] == 'BTC' \
                        and markets_sum_result['Market']['MarketCurrency'] == balances_result['Balance']['Currency']:
                    print(balances_result['Balance']['Currency'] + ' ' + markets_sum_result['Market']['MarketName'])
                    item = QTableWidgetItem(
                        '%.8f' % (markets_sum_result['Summary']['Last'] * balances_result['Balance']['Balance']))
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                    w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 2, 2, item)
                    item = QTableWidgetItem('%.8f' % (markets_sum_result['Summary']['Last']
                                                      * balances_result['Balance']['Balance']
                                                      * bitcoin_usdt_price))
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                    w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 1, 2, item)
                    total_balance_btc += markets_sum_result['Summary']['Last'] * balances_result['Balance'][
                        'Balance']
                    total_balance_usdt += markets_sum_result['Summary']['Last'] * balances_result['Balance'][
                        'Balance'] * bitcoin_usdt_price
                    # change in percents
                    item = CustomTableWidgetItem(U"(%.2f%%)" % ((abs((((markets_sum_result['Summary']['Last']
                                                                - markets_sum_result['Summary']['PrevDay'])
                                                                / markets_sum_result['Summary']['PrevDay'])
                                                                      * 100)))),
                                                 (((markets_sum_result['Summary']['Last']
                                                    - markets_sum_result['Summary']['PrevDay'])
                                                  / markets_sum_result['Summary']['PrevDay']) * 100))
                    if (((markets_sum_result['Summary']['Last']
                          - markets_sum_result['Summary']['PrevDay'])
                         / markets_sum_result['Summary']['PrevDay']) * 100) < 0:
                        item.setForeground(QtGui.QColor(228, 74, 94, 255))
                    elif (((markets_sum_result['Summary']['Last']
                           - markets_sum_result['Summary']['PrevDay'])
                          / markets_sum_result['Summary']['PrevDay']) * 100) > 0:
                        item.setForeground(QtGui.QColor(94, 185, 137, 255))
                    item.setTextAlignment(QtCore.Qt.AlignCenter)
                    w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 2, 3, item)
                    w.ui.balancesTable.setSpan(w.ui.balancesTable.rowCount() - 2, 3, 2, 1)
                elif balances_result['Balance']['Currency'] == 'BTC'\
                        or balances_result['Balance']['Currency'] == 'USDT':
                    # only btc correct
                    if markets_sum_result['Market']['MarketCurrency'] == balances_result['Balance']['Currency']:
                        print(balances_result['Balance']['Currency'] + ' ' + markets_sum_result['Market'][
                            'MarketName'])
                        item = QTableWidgetItem('%.8f' % balances_result['Balance']['Balance'])
                        item.setTextAlignment(QtCore.Qt.AlignCenter)
                        w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 2, 2, item)
                        item = QTableWidgetItem(
                            '%.8f' % (balances_result['Balance']['Balance'] * bitcoin_usdt_price))
                        item.setTextAlignment(QtCore.Qt.AlignCenter)
                        w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 1, 2, item)
                        total_balance_btc += balances_result['Balance']['Balance']
                        total_balance_usdt += balances_result['Balance']['Balance'] * bitcoin_usdt_price
                        # % change
                        item = CustomTableWidgetItem(U"(%.2f%%)" % ((abs((((markets_sum_result['Summary']['Last']
                                                                    - markets_sum_result['Summary']['PrevDay'])
                                                                    / markets_sum_result['Summary']['PrevDay'])
                                                                          * 100)))),
                                                     (((markets_sum_result['Summary']['Last']
                                                        - markets_sum_result['Summary']['PrevDay'])
                                                       / markets_sum_result['Summary']['PrevDay']) * 100))
                        if (((markets_sum_result['Summary']['Last']
                              - markets_sum_result['Summary']['PrevDay'])
                             / markets_sum_result['Summary']['PrevDay']) * 100) < 0:
                            item.setForeground(QtGui.QColor(228, 74, 94, 255))
                        elif (((markets_sum_result['Summary']['Last']
                                - markets_sum_result['Summary']['PrevDay'])
                               / markets_sum_result['Summary']['PrevDay']) * 100) > 0:
                            item.setForeground(QtGui.QColor(94, 185, 137, 255))
                        item.setTextAlignment(QtCore.Qt.AlignCenter)
                        w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 2, 3, item)
                        w.ui.balancesTable.setSpan(w.ui.balancesTable.rowCount() - 2, 3, 2, 1)
                    # usdt same
                    elif markets_sum_result['Market']['MarketCurrency'] == 'BTC'\
                            and markets_sum_result['Market']['BaseCurrency'] == balances_result['Balance']['Currency']:
                        print(balances_result['Balance']['Currency'] + ' ' + markets_sum_result['Market']['MarketName'])
                        item = QTableWidgetItem(
                            '%.8f' % (balances_result['Balance']['Balance'] / bitcoin_usdt_price))
                        item.setTextAlignment(QtCore.Qt.AlignCenter)
                        w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 2, 2, item)
                        item = QTableWidgetItem('%.8f' % balances_result['Balance']['Balance'])
                        item.setTextAlignment(QtCore.Qt.AlignCenter)
                        w.ui.balancesTable.setItem(w.ui.balancesTable.rowCount() - 1, 2, item)
                        total_balance_btc += balances_result['Balance']['Balance'] / bitcoin_usdt_price
                        total_balance_usdt += balances_result['Balance']['Balance']
                        # % change
                        item = CustomTableWidgetItem(U"(%.2f%%)" % ((abs((((markets_sum_result['Summary']['Last']
                                                                    - markets_sum_result['Summary']['PrevDay'])
                                                                    / markets_sum_result['Summary']['PrevDay'])
                                                                          * 100)))),
                                                     (((markets_sum_result['Summary']['Last']
                                                        - markets_sum_result['Summary']['PrevDay'])
                                                       / markets_sum_result['Summary']['PrevDay']) * 100))
                        if (((markets_sum_result['Summary']['Last']
                              - markets_sum_result['Summary']['PrevDay'])
                             / markets_sum_result['Summary']['PrevDay']) * 100) > 0:
                            item.setForeground(QtGui.QColor(228, 74, 94, 255))
                        elif (((markets_sum_result['Summary']['Last']
                                - markets_sum_result['Summary']['PrevDay'])
                               / markets_sum_result['Summary']['PrevDay']) * 100) < 0:
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
        if tail == 'SELL':
            item = QTableWidgetItem('●')
            item.setForeground(QtGui.QColor(228, 74, 94, 255))
        elif tail == 'BUY':
            item = QTableWidgetItem('●')
            item.setForeground(QtGui.QColor(94, 185, 137, 255))
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        w.ui.yourOrdersTable.setItem(w.ui.yourOrdersTable.rowCount() - 1, 0, item)
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


def get_answer():
    """Update function"""
    if w.dialog_answer != '':
        try:
            answer = acc2.get_market_summary(w.dialog_answer)
            print('Dialog(server_ask): ' + w.dialog_answer + ' Answer: ' + answer['result']['MarketName'])
            order_book = acc2.get_market_order_book(w.dialog_answer)
            order_history = acc2.get_market_history(w.dialog_answer)
            markets_summaries = acc2.get_market_summaries()
            balances = acc2.get_balances()
            open_orders = acc2.get_open_orders()
            print(open_orders)
            # while answer['result']['MarketName'] != w.dialog_answer:
            #     answer = acc2.get_market_summary(w.dialog_answer)
            #     order_book = acc2.get_market_order_book(w.dialog_answer)
            #     order_history = acc2.get_market_history(w.dialog_answer)
            #     markets_summaries = acc2.get_market_summaries()
            #     balances = acc2.get_balances()
            # check connection
            if answer is not None and order_book is not None and order_history \
                    is not None and balances is not None and markets_summaries is not None:
                # check if response is correct
                if answer['result'] != 'null' or order_book['result'] != 'null' \
                        or order_history['result'] != 'null' or balances['result'] != 'null':
                    update_all(answer, order_book, order_history, markets_summaries, balances, open_orders)
                else:
                    notification_message('Incorrect currency!')

            else:
                print('DEBUG: None_type detected in get_answer func')

        except ConnectionError:
            notification_message('Order book update error!')
        except Exception as e:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(e).__name__, e.args)
            print(message)
# END get_answer


def get_static_answer():
    """Function calls 1 time when currency init or changed"""
    if w.dialog_answer != '':
        try:
            markets = acc2.get_markets()
            img_file = b'\xff'
            if markets is not None and markets['success'] is True:
                for markets_result in markets['result']:
                    if markets_result['MarketName'] == w.dialog_answer:
                        if markets_result['LogoUrl'] is not None:
                            img_file = urllib.request.urlopen(markets_result['LogoUrl']).read()
                        else:
                            img_file = urllib.request.urlopen(
                                'https://upload.wikimedia.org/wikipedia/commons/5/59/Empty.png'
                            ).read()
                pixmap = QPixmap()
                pixmap.fill(QtCore.Qt.transparent)
                pixmap.loadFromData(img_file)
                w.ui.imageLabel.setPixmap(pixmap.scaled(64, 64, QtCore.Qt.IgnoreAspectRatio,
                                                        QtCore.Qt.FastTransformation))
                web_graph(w.dialog_answer)
            else:
                print('DEBUG: Nonetype detected in get_static_answer')

        except ConnectionError:
            notification_message('Currency info update error!')
        except Exception as e:
            # Except for unknown exeptions
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(e).__name__, e.args)
            print(message)
# END get_static_answer


def web_graph(market):
    """function for launching js script with graph from tradingview"""
    # WARN: Error spamming opengl, probably qt intelHDgraphics bug, can't fix with UseOpenGLES
    for index in reversed((range(w.ui.webLayout.count()))):
        w.ui.webLayout.itemAt(index).widget().setParent(None)
    head, sep, tail = market.partition('-')
    market = tail + head
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseDesktopOpenGL, True)
    web = QWebEngineView()
    web.setHtml(
        '''
        <!-- TradingView Widget BEGIN -->
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
            new TradingView.widget({
                "autosize": true,
                "symbol": "BITTREX:''' + market + '''",
                "interval": "D",
                "timezone": "Etc/UTC",
                "theme": "Light",
                "style": "1",
                "locale": "en",
                "toolbar_bg": "#f1f3f6",
                "enable_publishing": false,
                "allow_symbol_change": false,
                "hideideas": true
            });
        </script>
        <!-- TradingView Widget END -->
        ''')
    w.ui.webLayout.addWidget(web)
# END web_graph


def notification_message(text):
    """calls notification with our text"""
    popup.set_popup_text(text)
    popup.set_window_size(w.geometry())
    popup.show()
    print(text)
# END notification message


if __name__ == '__main__':
    # create application
    app = QApplication(sys.argv)
    app.setApplicationName('Bittrex client')

    # create widget
    w = MainWindow()
    w.setWindowTitle('Bittrex client')
    w.show()

    # # Additional elements initialization
    with open("secrets.json") as secrets_file:
        secrets = json.load(secrets_file)
        secrets_file.close()
    popup = PopUp()
    acc2 = BittrexV2(secrets['key'], secrets['secret'])
    thread = AThread()

    # tables setup
    table_init()

    # qt elements connections
    qt_connections_setup()

    # app_start
    w.dialog_answer = 'USDT-BTC'
    get_answer()
    get_static_answer()

    # execute application
    sys.exit(app.exec_())
