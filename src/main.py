from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qtagg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib import pyplot as plt
# TODO
# display bal after hypothetical buying thing
# edit transactions

from PyQt5 import QtCore, Qt, QtGui
import numpy as np
import sys
import json
import traceback
import os
import datetime
import re
import requests
import time # DEBUG
sys.path.append("src")
from typing import Union
from building import *
from constants import *
from data import *
from transaction import Transaction, TransactionType
from building_list import BuildingList, BuildingEntry

MY_VERSION = "1.3.0"

# really bad idea tbh
# try to guess the location of economy.json
# by looking at our cwd. if we're still in src
# then it's in ..
# else, assume it's in .
if os.path.basename(os.getcwd()) == "src":
    BACKUP_DIR = os.path.join("..", "backups")
    ECONOMY_FILE = os.path.join("..", "economy.json")
else:
    BACKUP_DIR = "backups"
    ECONOMY_FILE = "economy.json"

data = {
    "regions": {},
    "transactions": [Transaction(TransactionType.MANUAL, datetime.date(2022, 10, 10).isoformat(), amount=40000, comment="Initial balance")],
    "current_day": datetime.date(2022, 10, 10),
    "loans": [],
}


# hack to make json serialise my types properly lmao
def wrapped_default(self, obj):
    return getattr(obj.__class__, "serialise", wrapped_default.default)(obj)
wrapped_default.default = json.JSONEncoder().default
json.JSONEncoder.default = wrapped_default

def deserialise_all(raw_data):
    data = {"regions": {}, "current_day": datetime.date.fromisoformat(raw_data["current_day"])}
    for reg in raw_data["regions"]:
        data["regions"][reg] = {"buildings": []}
        for b in raw_data["regions"][reg]["buildings"]:
            data["regions"][reg]["buildings"].append(Building.deserialise(b, data["current_day"]))
            
    data["transactions"] = [Transaction.deserialise(t, data["current_day"]) for t in raw_data["transactions"]]
    data["loans"] = raw_data.get("loans", [])
    return data

if os.path.exists(ECONOMY_FILE):
    with open(ECONOMY_FILE, "r") as f:
        raw_data = json.load(f)
        
    data = deserialise_all(raw_data)
    


def serialise_all():
    ddata = data.copy()
    ddata["current_day"] = data["current_day"].isoformat()
    file_data = json.dumps(ddata, indent=None)
    return file_data

def save():
    file_data = serialise_all()
    with open(ECONOMY_FILE, "w") as f:
        f.write(file_data)

def get_historical_datas():
    if not os.path.isdir(BACKUP_DIR):
        return []
    
    datas = []
    for fname in os.listdir(BACKUP_DIR):
        with open(os.path.join(BACKUP_DIR, fname), "r") as f:
            raw_data = json.load(f)
        
        datas.append(deserialise_all(raw_data))
    
    datas.append(data)
    return datas

def send_info_popup(txt):
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Information)
    msg.setText(txt)
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg.exec_()


eco_cache = calc_income(data)[0]

    
class BuildingsTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        
        self.region_select = QtWidgets.QComboBox(self)
        self.e_newregion = QtWidgets.QLineEdit(self)
        self.b_newregion = QtWidgets.QPushButton("New region", self)
        self.b_delregion = QtWidgets.QPushButton("Delete region", self)
        
        self.region_select.addItem("Total")
        for region in data["regions"].keys():
            self.region_select.addItem(region)

        self.buildings = []
        self.building_list = BuildingList(self)
        
        self.layout = QtWidgets.QGridLayout(self)
        
        self.type_selector = QtWidgets.QComboBox(self)
        for btype, binfo in sorted(BUILDING_INFO.items(), key=lambda n: n[1].name):
            self.type_selector.addItem(binfo.name, userData=btype)
        self.type_selector.setMaxVisibleItems(len(BUILDING_INFO))
        
        self.e_count = QtWidgets.QSpinBox(self)
        self.e_count.setValue(1)
        self.e_count.setMaximum(99999)
        self.e_size  = QtWidgets.QSpinBox(self)
        self.e_size.setMaximum(999)
        self.e_size.hide()
        self.b_add   = QtWidgets.QPushButton("Add", self)
        self.l_compcost = QtWidgets.QLabel(self)
        self.l_compincome = QtWidgets.QLabel(self)
        self.l_compemployees=QtWidgets.QLabel(self)
        
        self.l_btype = QtWidgets.QLabel("Building type")
        self.l_count = QtWidgets.QLabel("Count")
        self.l_cost  = QtWidgets.QLabel("Cost")
        self.l_income= QtWidgets.QLabel("Income")
        self.l_employees=QtWidgets.QLabel("Employees")
        self.l_size  = QtWidgets.QLabel("Size")
        
        self.l_proj_bal = QtWidgets.QLabel(self)
        self.l_proj_income = QtWidgets.QLabel(self)
        self.l_proj_employ = QtWidgets.QLabel(self)
        
        self.spacer = QtWidgets.QLabel("", self)
        
        self.layout.addWidget(self.region_select, 0, 0)
        self.layout.addWidget(self.e_newregion,   0, 1)
        self.layout.addWidget(self.b_newregion,   0, 2)
        self.layout.addWidget(self.b_delregion,   0, 3)
        self.layout.addWidget(self.l_btype,       1, 0)
        self.layout.addWidget(self.l_count,       1, 1)
        self.layout.addWidget(self.l_income,      1, 2)
        self.layout.addWidget(self.l_cost,        1, 3)
        self.layout.addWidget(self.l_employees,   1, 4)
        self.layout.addWidget(self.l_size,        1, 5)
        self.layout.addWidget(self.type_selector, 2, 0)
        self.layout.addWidget(self.e_count,       2, 1)
        self.layout.addWidget(self.l_compincome,  2, 2)
        self.layout.addWidget(self.l_compcost,    2, 3)
        self.layout.addWidget(self.l_compemployees, 2, 4)
        self.layout.addWidget(self.e_size,        2, 5)
        self.layout.addWidget(self.b_add,         2, 6)
        
        self.layout.addWidget(self.l_proj_bal,    3, 0)
        self.layout.addWidget(self.l_proj_income, 3, 1)
        self.layout.addWidget(self.l_proj_employ, 3, 2)
        
        self.layout.addWidget(self.building_list, 4, 0, 1, 7)
        self.layout.addWidget(self.spacer,        5, 0, 1, 7)
        self.layout.setRowStretch(5, 1)
        self.setLayout(self.layout)
        
        self.type_selector.activated[str].connect(lambda t: self.recalc_preview())
        self.e_count.valueChanged[int].connect(lambda n: self.recalc_preview())
        self.e_size.valueChanged[int].connect(lambda s: self.recalc_preview())
        self.b_add.clicked.connect(self.add_building)
        self.b_newregion.clicked.connect(self.add_region)
        self.b_delregion.clicked.connect(self.del_region)
        self.region_select.activated[str].connect(lambda r: self.region_change())
        self.building_list.building_count_decrease[BuildingEntry].connect(self.remove_building)
        self.region_change()
        self.recalc_preview()
        
    def add_region(self):
        region = self.e_newregion.text()
        if len(region.strip()) == 0:
            send_info_popup("Enter a region name first")
            return
        if region in data["regions"]:
            send_info_popup("Enter a unique region name")
            return
            
        self.e_newregion.setText("")

        self.region_select.addItem(region)
        data["regions"][region] = {"buildings": []}
        save()
    
    def del_region(self):
        if not self.check_real_region():
            return

        region = self.region_select.currentText()
        reply = QtWidgets.QMessageBox.question(self, f"Delete region", "Really delete region '{region}'? The buildings won't be transferred.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.No:
            return
            
        del data["regions"][region]
        save()
        self.region_select.removeItem(self.region_select.currentIndex())

    def region_change(self):
        self.curr_region = self.region_select.currentText()

        self.building_list.clear()
        self.buildings = []
        if self.curr_region == "Total":
            for region in data["regions"].values():
                for building in region["buildings"]:
                    self.buildings.append(building)
        else:
            self.buildings = data["regions"][self.curr_region]["buildings"]
        
        building_nums = []
        for building in self.buildings:
            bid = (building.btype, building.size)
            if not (building.btype, building.size) in [(b[0].btype, b[0].size) for b in building_nums]:
                building_nums.append([building, 0])
                idx = len(building_nums) - 1
            else:
                idx = [i for i, b in enumerate(building_nums) if b[0].is_roughly(building)][0]
            building_nums[idx][1] += 1
        
        for building, count in building_nums:
            self.building_list.add_building(building, count)
        
        self.recalc_preview()

        self.parent.recalc_regional_stats(self)
        
    def recalc_preview(self):
        btype = self.type_selector.currentData()
        count = self.e_count.value()
        if btype == BType.HOUSE or btype == BType.AIRPORT:
            self.e_size.show()
            self.l_size.show()
            size = self.e_size.value()
            building = Building(btype, data["current_day"], Building.get_lorentz(eco_cache), size)
            if btype == BType.HOUSE and not size in [1, 2, 4, 6]: # perhaps the size is not valid yet, let's just ignore that
                self.l_compcost.setText("Invalid size")
                self.l_compincome.setText("Invalid size")
                return
        else:
            self.e_size.hide()
            self.l_size.hide()
            building = Building(btype, data["current_day"], Building.get_lorentz(eco_cache))
 
        income = building.income() * count
        self.l_compcost.setText(format_money(building.cost(l=Building.get_lorentz(eco_cache)) * count))
        self.l_compincome.setText(format_money(income))
        self.l_compemployees.setText(str(round(building.employees() * count, 3)))
        
        if self.curr_region == "Total":
            self.l_proj_bal.hide()
            self.l_proj_income.hide()
            self.l_proj_employ.hide()
            return
            
        self.l_proj_bal.show()
        self.l_proj_income.show()
        self.l_proj_employ.show()
        for i in range(count):
            data["regions"][self.curr_region]["buildings"].append(building)
                
        self.l_proj_bal.setText("Projected bal: " + format_money(calc_bal(data) - building.cost(l=Building.get_lorentz(eco_cache)) * count))
        self.l_proj_income.setText("Projected income: " + format_money(calc_income(data)[0]))
        self.l_proj_employ.setText("Projected employment: " + str(round(calc_employment(data) * 100, 1)) + "%")
        
        for i in range(count):
            data["regions"][self.curr_region]["buildings"].pop()
    
    def check_real_region(self):
        """check the current region is not 'Total'. If it is, warn the user
        returns whether a real region was selected"""
        if self.curr_region == "Total":
            send_info_popup("Select a region first")
            return False
        return True

    def add_building(self):
        if not self.check_real_region():
            return

        btype = self.type_selector.currentData()
        if btype == BType.AIRPORT or btype == BType.HOUSE:
            building = Building(btype, data["current_day"], Building.get_lorentz(eco_cache), self.e_size.value())
        else:
            building = Building(btype, data["current_day"], Building.get_lorentz(eco_cache))

        count = self.e_count.value()
        if not (building.btype, building.size) in [(b.btype, b.size) for b in self.buildings]:
            self.building_list.add_building(building, 0)
        
        for i in range(count): # hack, just like clicking it multiple times lol
            self.buildings.append(building)

        self.building_list.update_building(building, len([1 for b in self.buildings if b.is_roughly(building)]))
        data["regions"][self.curr_region]["buildings"] = self.buildings
        save()
        
        self.parent.transactions_tab.add_transaction(Transaction(
            TransactionType.BUY,
            data["current_day"].isoformat(),
            buildings=[building] * count,
        ))
        
    def remove_building(self, entry: BuildingEntry):
        if not self.check_real_region():
            return

        count, ok = QtWidgets.QInputDialog.getInt(self, "Sell building", "How many " + entry.building.name() + "s do you want to sell?", 1, 1, entry.count)
        if not ok:
            return

        correct_types = [b for b in self.buildings if b.btype == entry.building.btype and b.size == entry.building.size]
        correct_types = sorted(correct_types, key=lambda b: -b.lorentz)
        buildings = []
        for b in correct_types[:count]:
            self.buildings.remove(b)
            buildings.append(b)
        
        if entry.count <= count:
            self.building_list.remove_building(buildings[0])
        else:
            self.building_list.update_building(buildings[0], len([1 for b in self.buildings if b.is_roughly(buildings[0])]))

        last_t = data["transactions"][-1]
        if False and last_t.trans_type == TransactionType.BUY and last_t.building == building and last_t.count >= count:
            # update/cancel out last transaction instead
            if last_t.count == count:
                # get rid entirely
                data["transactions"].pop(-1)
                self.parent.transactions_tab.table.removeRow(len(data["transactions"]))
            else:
                last_t.count -= count
                self.parent.transactions_tab.set_row_to(len(data["transactions"]) - 1, last_t)

        else:
            self.parent.transactions_tab.add_transaction(Transaction(
                TransactionType.SELL,
                data["current_day"].isoformat(),
                buildings=buildings,
            ))
        
        data["regions"][self.curr_region]["buildings"] = self.buildings
        save()
        self.recalc_preview()

class KeybindTable(QtWidgets.QTableWidget):
    keyPressed = Qt.pyqtSignal(QtGui.QKeyEvent)
    def keyPressEvent(self, event):    
        if type(event) == QtGui.QKeyEvent:
            self.keyPressed.emit(event)

class TransactionsTab(QtWidgets.QWidget):
    recalculate = Qt.pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.layout = QtWidgets.QGridLayout(self)
        self.bottom_layout = QtWidgets.QHBoxLayout()
        
        self.table = KeybindTable(self)
        self.table.setColumnCount(3)
        self.table.setRowCount(0)
        self.table.setHorizontalHeaderLabels(["Amount", "Date", "Comment"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        
        self.e_amount = QtWidgets.QLineEdit(self)
        self.e_comment= QtWidgets.QLineEdit(self)
        self.b_add    = QtWidgets.QPushButton("Add", self)

        self.e_amount.setPlaceholderText("Amount")
        self.e_comment.setPlaceholderText("Comment")
        
        self.layout.addWidget(self.table, 1, 0, 1, 3)
        self.layout.addWidget(self.e_amount, 0, 0)
        self.layout.addWidget(self.e_comment, 0, 1)
        self.layout.addWidget(self.b_add, 0, 2)
        self.layout.setColumnStretch(1, 1)
        self.setLayout(self.layout)
        
        self.b_add.clicked.connect(self._add_transaction_button)
        self.table.keyPressed[QtGui.QKeyEvent].connect(self._table_keypress)
        
        self.transaction_widgets = []
        
        for t in data["transactions"]:
            self._add_transaction_to_table(t)
        self.recalculate.emit()
        
    def _table_keypress(self, event):
        if event.key() == QtCore.Qt.Key_Delete and self.table.rowCount() > 0:
            row = self.table.currentRow()
            t = data["transactions"][row]
            if t.trans_type != TransactionType.MANUAL:
                pass#return

            cont = QtWidgets.QMessageBox.question(self, "Really delete transaction?", "Really delete transaction?")
            if cont == QtWidgets.QMessageBox.No:
                return
            data["transactions"].pop(row)
            self.table.removeRow(row)
            save()
            self.recalculate.emit()

    def _add_transaction_button(self):
        try:
            amount = round(float(self.e_amount.text()), 2)
        except ValueError:
            send_info_popup("Enter a valid number for the amount (without any $)")
            return
        
        date = data["current_day"].isoformat()
        comment = self.e_comment.text()
        self.add_transaction(Transaction(TransactionType.MANUAL, date, comment=comment, amount=amount))
        self.e_comment.setText("")
        self.e_amount.setText("")
    
    def add_transaction(self, transaction: Transaction):
        data["transactions"].append(transaction)
        save()

        self._add_transaction_to_table(transaction)
        self.recalculate.emit()
        
    def _add_transaction_to_table(self, transaction: Transaction):
        row = self.table.rowCount()
        self.table.setRowCount(row + 1)
        self.set_row_to(row, transaction)
    
    def set_row_to(self, row, transaction):
        self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(format_money(transaction.compute_amount())))
        self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(format_date(transaction.timestamp)))
        self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(transaction.compute_comment()))

def calc_series(datas, series):
    if series == "Balance":
        return [calc_bal(d) for d in datas]
    elif series == "Population":
        return [calc_population(d)[0] for d in datas]
    elif series == "Income":
        return [calc_income(d)[0] for d in datas]
    elif series == "Expenditure":
        vals = []
        for d in datas:
            vals.append(0)
            for trans in d["transactions"]:
                if trans.timestamp == d["current_day"].isoformat() and trans.compute_amount() < 0:
                    vals[-1] -= trans.compute_amount()
        return vals
    elif series == "Employment":
        return [calc_employment(d) * 100 for d in datas]
    
    elif series == "Time":
        return [i for i, d in enumerate(datas)]
    
class GraphControls(QtWidgets.QWidget):
    def __init__(self, figure, parent=None):
        super().__init__(parent)
        self.figure = figure
        self.ax = figure.subplots()

        self.layout = QtWidgets.QVBoxLayout(self)
        self.graph_type = QtWidgets.QComboBox(self)
        self.x_axis = QtWidgets.QComboBox(self)
        self.y_axis = QtWidgets.QComboBox(self)
        
        self.l_gtype = QtWidgets.QLabel("Graph type", self)
        self.l_xaxis = QtWidgets.QLabel("Plot...", self)
        self.l_yaxis = QtWidgets.QLabel("Against...", self)
        
        self.b_plot = QtWidgets.QPushButton("Plot", self)
        self.b_clear = QtWidgets.QPushButton("Clear", self)
        
        self.graph_type.addItems(["Line graph", "Scatter graph", "Pie chart"])
        
        self.layout.addWidget(self.l_gtype)
        self.layout.addWidget(self.graph_type)
        self.layout.addWidget(self.l_xaxis)
        self.layout.addWidget(self.x_axis)
        self.layout.addWidget(self.l_yaxis)
        self.layout.addWidget(self.y_axis)
        self.layout.addWidget(self.b_plot)
        self.layout.addWidget(self.b_clear)
        
        self.setLayout(self.layout)
        
        self.graph_type.activated[str].connect(lambda x: self.update())
        self.x_axis.activated[str].connect(lambda x: self.update())
        self.y_axis.activated[str].connect(lambda x: self.update())
        self.b_plot.clicked.connect(self.plot)
        self.b_clear.clicked.connect(self.clear)
        
        self.update()
        
    def clear(self):
        self.figure.clear()
        self.ax = self.figure.subplots()
        # self.ax.clear()
        self.figure.canvas.draw()
        
    def update(self):
        ty = self.graph_type.currentText()
        itemx = self.x_axis.currentIndex()
        itemy = self.y_axis.currentIndex()
        self.x_axis.clear()
        self.y_axis.clear()
        # TODO graph something of just one region
        if ty == "Line graph" or ty == "Scatter graph":
            self.x_axis.addItems(["Balance", "Income", "Expenditure", "Employment", "Population"])
            self.y_axis.addItems(["Time"])
            
        if ty == "Scatter graph":
            self.y_axis.addItems(["Balance", "Income", "Expenditure", "Employment", "Population"])
            
        if ty == "Pie chart":
            self.x_axis.addItems(["Income", "Population"])
            self.y_axis.addItems(["Region", "Industry"])
            
        # elif ty == "Bar chart":
            # self.x_axis.addItems(["Employment"])
            # self.y_axis.addItems(["Region"])
        
        if itemx < self.x_axis.count():
            self.x_axis.setCurrentIndex(itemx)
            
        if itemy < self.y_axis.count():
            self.y_axis.setCurrentIndex(itemy)
    
    def plot(self):
        # TODO do it
        gtype = self.graph_type.currentText()
        xaxis = self.x_axis.currentText()
        yaxis = self.y_axis.currentText()
        if len(xaxis) < 1 or len(yaxis) < 1:
            return
            
        if gtype == "Pie chart":
            if xaxis == "Income" and yaxis == "Region":
                _, regional_income = calc_income(data)
                values, labels = regional_income.values(), regional_income.keys()
            elif xaxis == "Population" and yaxis == "Region":
                _, regional_pop = calc_population(data)
                values, labels = regional_pop.values(), regional_pop.keys()
            elif xaxis == "Income" and yaxis == "Industry":
                ind = calc_industry_income(data)
                values, labels = ind.values(), ind.keys()
            else:
                return # invalid configuration

            values, labels = zip(*sorted(zip(values, labels), key=lambda i: i[0]))
            cm = plt.get_cmap("plasma")
            colours = [cm(i) for i in np.linspace(0, 1, len(values))]

            self.ax.pie(values, labels=labels, autopct='%1.1f%%', shadow=True, startangle=90, colors=colours)
            self.ax.axis('equal')
        
        elif gtype == "Line graph" or gtype == "Scatter graph":
            datas = sorted(get_historical_datas(), key=lambda d: d["current_day"])
            xvals = calc_series(datas, xaxis)
            yvals = calc_series(datas, yaxis)
            if gtype == "Line graph":
                self.ax.plot(yvals, xvals)
            else:
                self.ax.scatter(yvals, xvals)
        
        # elif gtype == "Bar chart":
            # if xaxis == "Employment" and yaxis == "Region":
                # _, regional_employment = calc_employment(data)
                # self.ax.bar(regional_employment.keys(), list(map(lambda n: n * 100, regional_employment.values())))
            
        self.figure.canvas.draw()

class MoronException(Exception):
    pass

class StatsTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.layout = QtWidgets.QGridLayout(self)
        
        self.graph_layout = QtWidgets.QVBoxLayout()
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        self.graph_layout.addWidget(self.toolbar)
        self.graph_layout.addWidget(self.canvas)

        self.graph_controls = GraphControls(self.figure, self)

        self.layout.addWidget(self.graph_controls, 0, 0, 1, 1)
        self.layout.addLayout(self.graph_layout, 0, 1, 3, 1)
        self.layout.setColumnStretch(1, 1)
        self.setLayout(self.layout)

class LoansTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.layout = QtWidgets.QGridLayout(self)
        
        self.e_amount = QtWidgets.QSpinBox(self)
        self.e_amount.setMaximum(999999999)
        self.l_amount = QtWidgets.QLabel("Amount", self)
        self.b_un = QtWidgets.QCheckBox("UN loan", self)
        self.e_interest_rate = QtWidgets.QDoubleSpinBox(self)
        self.l_interest_rate = QtWidgets.QLabel("Interest Rate (%)", self)
        self.e_name = QtWidgets.QLineEdit(self)
        self.l_name = QtWidgets.QLabel("Name", self)
        self.b_get_loan = QtWidgets.QPushButton("Add loan", self)

        self.ongoing_loans = QtWidgets.QGridLayout()
        self.spacer = QtWidgets.QLabel("")

        self.layout.addWidget(self.l_amount, 0, 0)
        self.layout.addWidget(self.e_amount, 1, 0)
        self.layout.addWidget(self.b_un,     1, 1)
        self.layout.addWidget(self.l_interest_rate, 0, 2)
        self.layout.addWidget(self.e_interest_rate, 1, 2)
        self.layout.addWidget(self.l_name, 0, 3)
        self.layout.addWidget(self.e_name, 1, 3)
        self.layout.addWidget(self.b_get_loan, 1, 4)
        self.layout.addLayout(self.ongoing_loans, 4, 0, 1, 5)
        self.layout.addWidget(self.spacer, 5, 0, 1, 5)
        self.layout.setRowStretch(5, 1)

        self.setLayout(self.layout)

        self.b_un.clicked.connect(self.un_loan)
        self.b_get_loan.clicked.connect(self.get_loan)
        self.loans = []
        self.ongoing_loans.addWidget(QtWidgets.QLabel("Amount due for payback"), 0, 0)
        self.ongoing_loans.addWidget(QtWidgets.QLabel("Interest rate"), 0, 1)
        self.ongoing_loans.addWidget(QtWidgets.QLabel("Lender name"), 0, 2)
        self.curr_row = 1

        self.update_loan_widgets()

    def un_loan(self):
        if self.b_un.isChecked():
            self.e_interest_rate.setEnabled(False)
            self.e_interest_rate.setValue(UN_LOAN_INTEREST * 100)
            self.e_name.setEnabled(False)
            self.e_name.setText("UN")
        else:
            self.e_interest_rate.setEnabled(True)
            self.e_name.setEnabled(True)

    def get_loan(self):
        data["loans"].append([self.e_amount.value(), self.e_interest_rate.value(), self.e_name.text(), 0])
        self.add_loan_widgets(data["loans"][-1])
        self.parent.transactions_tab.add_transaction(Transaction(
            TransactionType.MANUAL,
            data["current_day"].isoformat(),
            comment="Loan from " + self.e_name.text(),
            amount=self.e_amount.value(),
        ))
        save()

    def make_payment(self, pos, loan):
        amount, ok = QtWidgets.QInputDialog.getDouble(self, "Make loan payment", "How much would you like to pay?", 0, 1, loan[0], 2)
        if not ok:
            return

        self.parent.transactions_tab.add_transaction(Transaction(
            TransactionType.MANUAL,
            data["current_day"].isoformat(),
            comment="Loan payment to " + loan[2],
            amount=-amount
        ))

        # this is stupid
        idx = -1
        for i, l in enumerate(data["loans"]):
            if l[1] == loan[1] and l[2] == loan[2]:
                idx = i
                break
        if idx == -1:
            raise MoronException("For some reason the loan you tried to pay off wasn't found in your total loan list. big but report to jams plz")
        data["loans"][idx][3] += amount
        data["loans"][idx][0] -= amount
        if data["loans"][idx][0] < 0.01:
            if data["loans"][idx][2] != "UN":
                to_pay_other = data["loans"][idx][3]
                send_info_popup("You paid a total of " + format_money(to_pay_other) + " to " + data["loans"][idx][2])
            data["loans"].pop(idx)
            self.update_loan_widgets()
        else:
            self.loans[pos][0].setText(format_money(data["loans"][idx][0]))
        save()

    def add_loan_widgets(self, loan):
        self.loans.append((
            QtWidgets.QLabel(format_money(loan[0])),
            QtWidgets.QLabel(str(round(loan[1], 2)) + "%"),
            QtWidgets.QLabel(loan[2]),
            QtWidgets.QPushButton("Make payment")
        ))
        l = len(self.loans)
        self.loans[-1][3].clicked.connect(lambda: self.make_payment(l - 1, loan))

        for col, w in enumerate(self.loans[-1]):
            self.ongoing_loans.addWidget(w, self.curr_row, col)

        self.curr_row += 1

    def update_loan_widgets(self):
        for row in self.loans:
            for w in row:
                self.ongoing_loans.removeWidget(w)
        self.loans.clear()

        self.curr_row = 1

        for loan in data["loans"]:
            self.add_loan_widgets(loan)

class Main(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.init_gui()

        self.show()
        
    def init_gui(self):
        self.layout = QtWidgets.QVBoxLayout(self)

       
        
        self.local_stats_layout = QtWidgets.QHBoxLayout()
        self.global_stats_layout = QtWidgets.QHBoxLayout()
        self.date_layout = QtWidgets.QHBoxLayout()
        
        self.b_update_day = QtWidgets.QPushButton("Update day to today's date", self)
        self.b_next_day = QtWidgets.QPushButton("Next day", self)
        self.b_update_day.clicked.connect(lambda: self.update_day())
        self.b_next_day.clicked.connect(lambda: self.update_day(delta=1))

        self.l_bal = QtWidgets.QLabel(self)
        self.l_income = QtWidgets.QLabel(self)
        self.l_employment = QtWidgets.QLabel(self)
        self.l_pop = QtWidgets.QLabel(self)
        self.l_jobs = QtWidgets.QLabel(self)
        self.l_lorentz = QtWidgets.QLabel(self)
        self.l_date = QtWidgets.QLabel(self)

        self.l_regincome = QtWidgets.QLabel(self)
        self.l_regpop = QtWidgets.QLabel(self)
        self.l_regjobs = QtWidgets.QLabel(self)
        self.l_regemploy = QtWidgets.QLabel(self)

        self.local_stats_layout.addWidget(self.l_regincome)
        self.local_stats_layout.addWidget(self.l_regemploy)
        self.local_stats_layout.addWidget(self.l_regpop)
        self.local_stats_layout.addWidget(self.l_regjobs)

        self.global_stats_layout.addWidget(self.l_bal)
        self.global_stats_layout.addWidget(self.l_income)
        self.global_stats_layout.addWidget(self.l_employment)
        self.global_stats_layout.addWidget(self.l_pop)
        self.global_stats_layout.addWidget(self.l_jobs)
        self.global_stats_layout.addWidget(self.l_lorentz)
        
        self.date_layout.addWidget(self.l_date)
        self.date_layout.addWidget(self.b_next_day)
        self.date_layout.addWidget(self.b_update_day)
        
        self.stats_tab = StatsTab(self)
        self.transactions_tab = TransactionsTab(self)
        self.buildings_tab = BuildingsTab(self)
        self.loans_tab = LoansTab(self)
        
        self.tab_widget = QtWidgets.QTabWidget(self)
        self.tab_widget.addTab(self.buildings_tab, "Buildings")
        self.tab_widget.addTab(self.transactions_tab, "Transactions")
        self.tab_widget.addTab(self.stats_tab, "Stats")
        self.tab_widget.addTab(self.loans_tab, "Loans")
        self.layout.addWidget(self.tab_widget)
        self.layout.addLayout(self.local_stats_layout)
        self.layout.addLayout(self.global_stats_layout)
        self.layout.addLayout(self.date_layout)
        
        self.setLayout(self.layout)
        self.recalculate()
        self.transactions_tab.recalculate.connect(self.recalculate)

    def recalculate(self):
        self.recalc_balance()
        self.recalc_income()
        self.l_date.setText("Current date: " + format_date(data["current_day"].isoformat()))
        self.l_pop.setText("Population: " + str(calc_population(data)[0]))
        self.l_jobs.setText("Jobs: " + str(round(calc_jobs(data)[0], 2)))
        self.buildings_tab.recalc_preview()
        self.l_lorentz.setText("L: " + str(round(Building.get_lorentz(eco_cache), 4)))
        self.recalc_regional_stats(self.buildings_tab)
        
    def recalc_regional_stats(self, buildings_tab):
        if buildings_tab.curr_region == "Total":
            # no regional stats
            self.l_regincome.hide()
            self.l_regemploy.hide()
            self.l_regpop.hide()
            self.l_regjobs.hide()
        else:
            _, reg_pop = calc_population(data)
            _, reg_jobs = calc_jobs(data)
            pop = reg_pop[buildings_tab.curr_region]
            jobs = reg_jobs[buildings_tab.curr_region]
            
            if pop != 0:
                employ_percent = jobs / pop * 100
            else:
                employ_percent = 0

            _, regional_income = calc_income(data)
            inc = regional_income[buildings_tab.curr_region]
            
            self.l_regincome.show()
            self.l_regemploy.show()
            self.l_regpop.show()
            self.l_regjobs.show()
            self.l_regincome.setText("Income (region): " + str(format_money(inc)))
            self.l_regemploy.setText("Employment (region): " + str(round(employ_percent, 1)) + "%")
            self.l_regpop.setText("Population (region): " + str(pop))
            self.l_regjobs.setText("Jobs (region): " + str(round(jobs, 2)))
            
    def recalc_balance(self):
        bal = calc_bal(data)
        self.l_bal.setText("Balance: " + format_money(bal))
        
    def recalc_income(self):
        global eco_cache
        employment = calc_employment(data)
        income, regional_income = calc_income(data)
        eco_cache = income
        
        self.l_income.setText("Income: " + format_money(income))
        self.l_employment.setText("Employment: " + str(round(employment * 100, 2)) + "%")
        
    def get_paid(self):
        # this check is currently redundant but I left it in for the lulz
        for n in data["transactions"][::-1]:
            if n.comment == "Income" and n.timestamp == data["current_day"].isoformat():
                send_info_popup("YE CANNAE FOCKEN DAE THAT M8\n(you can only get paid once per day)")
                return
        income, regional_income = calc_income(data)
        self.transactions_tab.add_transaction(Transaction(
            TransactionType.MANUAL,
            data["current_day"].isoformat(),
            comment="Income",
            amount=income,
        ))
        bal = calc_bal(data)
        if bal < 0:
            self.transactions_tab.add_transaction(Transaction(
                TransactionType.MANUAL,
                data["current_day"].isoformat(),
                comment="Overdraft interest",
                amount=bal * OVERDRAFT_INTEREST,
            ))

    def calc_loans(self):
        for loan in data["loans"]:
            loan[0] *= loan[1] / 100 + 1
        self.loans_tab.update_loan_widgets()

    def update_day(self, delta=None):
        if delta is not None:
            now = datetime.date.today()
            next_day = data["current_day"] + datetime.timedelta(days=delta)
            if next_day > now:
                send_info_popup("Woah there buddy you aren't goint 88mph\n(you're trying to go into the future!)")
                return

        save()
        if os.path.exists(BACKUP_DIR) and os.path.isfile(BACKUP_DIR):
            raise MoronException("You absolute idiot, you made a file called 'backups', that's where I want to store my backups! Please delete or rename it")
        if not os.path.exists(BACKUP_DIR):
            os.mkdir(BACKUP_DIR)
        
        # Yes, this is a race condition or TOC/TOU bug
        # The truth is, I do not care, for it is exceedingly unlikely that anything could happen in between
        # also it wouldn't even matter that much it would just crash and save the progress anyway lmao
        
        text_data = serialise_all()
        with open(os.path.join(BACKUP_DIR, data["current_day"].isoformat() + ".json"), "w") as f:
            f.write(text_data)
            
        if delta is None:
            data["current_day"] = datetime.date.today()
        else:
            data["current_day"] += datetime.timedelta(days=delta)
        self.get_paid()
        self.calc_loans()
        self.recalculate()
        save()

def exception_hook(exctype, value, tb):
    traceback_formated = traceback.format_exception(exctype, value, tb)
    traceback_string = "".join(traceback_formated)
    print("Excepthook called, saving and quiteing...")
    # TODO maybe save data in ram data["regions"][btab.curr_region]["buildings"] = btab.buildings
    save()
    print(traceback_string, file=sys.stderr)
    
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Critical)
    msg.setText("An error occurred in the main process. Your data should be safe (in theory). Please send the following report to me(james):\n" + traceback_string)
    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg.exec_()
    sys.exit(1)

class Updater(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.layout = QtWidgets.QVBoxLayout(self)
        self.doing = QtWidgets.QLabel(self)
        self.progress = QtWidgets.QProgressBar(self)
        self.layout.addWidget(self.doing)
        self.layout.addWidget(self.progress)
        self.setLayout(self.layout)

    def update(self):
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)
        self.uworker = UpdateWorker()

        self.uworker.progress_changed.connect(lambda prog: self.progress.setValue(prog))
        self.uworker.progress_max.connect(lambda m: self.progress.setMaximum(m))
        self.uworker.update_status.connect(lambda s: self.doing.setText(s))
        self.uworker.result.connect(lambda res: self.update_done(res[0], res[1]))
        self.uworker.start()

    def update_done(self, updated, msg):
        if updated:
            send_info_popup(msg)
        elif msg is not None:
            choice = QtWidgets.QMessageBox.warning(self, "Update Failed",
                                   "Error updating: " + msg,
                                   QtWidgets.QMessageBox.Retry | QtWidgets.QMessageBox.Ignore,
                                   QtWidgets.QMessageBox.Retry)

            if choice == QtWidgets.QMessageBox.Retry:
                self.update()
                return
        self.done(updated)

class UpdateWorker(QtCore.QThread):
    progress_changed = Qt.pyqtSignal(int)
    progress_max = Qt.pyqtSignal(int)
    result = Qt.pyqtSignal(object)
    update_status = Qt.pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def run(self):
        res = self.autoupdate()
        self.result.emit(res)
    
    def autoupdate(self):
        self.update_status.emit("Checking for updates...")
        try:
            vers_r = requests.get("http://cospox.com/eco/version")
        except Exception as e:
            return False, "Getting version, other error " + str(e)
        if vers_r.status_code != 200:
            return False, "Getting version, status " + str(vers_r.status_code)
        if vers_r.text.strip() == MY_VERSION:
            # already up to date
            return False, None

        self.update_status.emit("Fetching file list...")
        
        try:
            flist = requests.get("http://cospox.com/eco/files")
        except Exception as e:
            return False, "Getting file list, other error " + str(e)

        if flist.status_code != 200:
            return False, "Getting file list, status " + str(flist.status_code)

        num_files = len(flist.text.strip().split(","))
        self.progress_max.emit(num_files + 1)
        val = 1
        self.progress_changed.emit(val)

        for fname in flist.text.strip().split(","):
            self.update_status.emit("Downloading " + fname + " (" + str(val) + "/" + str(num_files - 1) + ")")
            try:
                r = requests.get("http://cospox.com/eco/" + fname)
            except Exception as e:
                return False, "Getting file " + fname + ", other error " + str(e)
 
            if r.status_code != 200:
                return False, "Getting update file " + fname + ", status " + str(r.status_code)
            with open(os.path.join("src", fname), "w", newline="") as f:
                f.write(r.text)

            val += 1
            self.progress_changed.emit(val)

        return True, "Downloaded version " + vers_r.text + ". Restart program to update."

if __name__ == '__main__':
    import threading
    sys.excepthook = exception_hook
    app = QtWidgets.QApplication(sys.argv)
    updater = Updater()
    updater.update()
    if updater.exec():
        sys.exit(0)

    ex = Main()
    if os.path.isfile("stylesheets.qss"):
        with open("stylesheets.qss", "r") as f:
            ex.setStyleSheet(f.read())
    if os.path.isfile("appearance.json"):
        with open("appearance.json", "r") as f:
            ap = json.load(f)
        
        app.setStyle(ap["style"])

    sys.exit(app.exec_())
