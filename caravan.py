import sys
import os
import traceback

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMdiArea, QMdiSubWindow,
    QMenuBar, QMenu, QDockWidget, QFileDialog, QMessageBox,
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox,
    QWidget, QTreeWidget, QTreeWidgetItem,
    QStyleFactory, QProgressBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QFont

sys.path.append("lib")

app = QApplication(sys.argv)
app.setStyle(QStyleFactory.create('Fusion'))
icon = QIcon("caravan.ico")

import asm, settings
import rom, panellist, rompanel, changelog, window, consts, util, temp, layout

def error(etype, value, tb):
    l = traceback.format_exception(etype, value, tb)
    if 'mw' in globals():
        mw.showError("".join(l))
    else:
        print("".join(l))

def pathjoin(*args):
    s = os.path.join(*args)
    if s[2] != "\\":
        s = s[:2] + "\\" + s[2:]
    return s

sys.excepthook = error

redo = []
undo = []

class LayoutTree(QTreeWidget):
    
    def __init__(self, parent=None, id=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setMinimumWidth(200)
        self._init_structure()
        # раскрываем только корень и Resources
        self.collapseAll()
        root = self.topLevelItem(0)
        if root:
            self.expandItem(root)
            for i in range(root.childCount()):
                child = root.child(i)
                if child.text(0) == "Resources":
                    self.expandItem(child)
                    break

        self.setStyleSheet("""
            QTreeWidget {
                font-size: 11pt;
                font-family: "Segoe UI";
                background: #f0f0f0;
                border: 1px solid #ccc;
                padding: 4px;
            }
            QTreeWidget::item {
                padding: 6px 2px;
                border-bottom: 1px solid #e0e0e0;
            }
            QTreeWidget::item:has-children {
                font-weight: bold;
                color: #2c3e50;
            }
            QTreeWidget::item:!has-children {
                font-weight: normal;
                color: #34495e;
            }
            QTreeWidget::item:hover {
                background: #d0e4f7;
            }
            QTreeWidget::item:selected {
                background: #3498db;
                color: white;
            }
        """)

    def _init_structure(self):
        root = QTreeWidgetItem(self, ["Editable Content"])
        data = QTreeWidgetItem(root, ["Data"])
        QTreeWidgetItem(data, ["Characters"])
        QTreeWidgetItem(data, ["Classes"])
        QTreeWidgetItem(data, ["Promotions"])
        QTreeWidgetItem(data, ["Monsters"])
        QTreeWidgetItem(data, ["Spells"])
        QTreeWidgetItem(data, ["Items"])
        QTreeWidgetItem(data, ["Shops"])
        QTreeWidgetItem(data, ["Gameplay Values"])
        scripting = QTreeWidgetItem(root, ["Scripting"])
        QTreeWidgetItem(scripting, ["Dialogue"])
        QTreeWidgetItem(scripting, ["Battles"])
        resources = QTreeWidgetItem(root, ["Resources"])
        QTreeWidgetItem(resources, ["Palettes"])
        QTreeWidgetItem(resources, ["Sprites"])
        QTreeWidgetItem(resources, ["Battle Sprites"])
        QTreeWidgetItem(resources, ["Weapon Sprites"])
        QTreeWidgetItem(resources, ["Spell Animations"])
        QTreeWidgetItem(resources, ["Battle Backgrounds"])
        QTreeWidgetItem(resources, ["Battle Floors"])
        QTreeWidgetItem(resources, ["Item/Spell Icons"])
        QTreeWidgetItem(resources, ["Menu Icons"])
        QTreeWidgetItem(resources, ["Portraits"])
        QTreeWidgetItem(resources, ["Map Definitions"])
        QTreeWidgetItem(resources, ["Map Tiles"])
        QTreeWidgetItem(resources, ["Fonts"])
        other = QTreeWidgetItem(root, ["Other"])
        QTreeWidgetItem(other, ["ROM Viewer"])
        self.expandAll()

    def init(self):
        pass

    def clear(self):
        while self.topLevelItemCount() > 0:
            item = self.takeTopLevelItem(0)
            del item
        self._init_structure()

    @property
    def allItems(self):
        items = []
        def recurse(parent):
            for i in range(parent.childCount()):
                child = parent.child(i)
                items.append(child)
                recurse(child)
        recurse(self.invisibleRootItem())
        return items

    def modify(self, item, modified):
        pass


class MainFrame(window.CaravanParentFrame):
    def __init__(self, parent, id, app):
        window.CaravanParentFrame.__init__(self, parent, id)

        self.mdi_area = QMdiArea()
        self.setCentralWidget(self.mdi_area)

        self.app = app
        self.rom = None
        self.settings = settings.init("caravan.cfg")

        self.filename = ""
        self.dirname = ""
        self.datafilename = ""
        self.datadirname = ""

        self.dataFile = None
        self.curPanelID = None
        self.panels = {}
        self.frames = []
        self.stored = {}
        self.pendingCancel = False
        self.isErring = False

        self.headerFont = QFont("Verdana", 18, QFont.Bold)
        self.editFont = QFont("Courier New", 12, QFont.Bold)
        self.subFont = QFont("Verdana", 10)

        self.tempUndoStack = {}
        self.tempRedoStack = {}

        self.setMinimumSize(600, 450)

        # Меню
        menuBar = self.menuBar()

        projectMenu = QMenu("&Project")
        act_new_project = self._createAction("&New Project...\tCtrl+N", "Create a new project.", self.OnNewProject, "Ctrl+N")
        projectMenu.addAction(act_new_project)
        act_open_project = self._createAction("&Open Project...\tCtrl+O", "Open a project.", self.OnNewProject, "Ctrl+O")
        projectMenu.addAction(act_open_project)
        self.actSaveProject = self._createAction("&Save Project\tCtrl+S", "Save the currently loaded project.", None, "Ctrl+S")
        projectMenu.addAction(self.actSaveProject)
        self.actSaveProjectAs = self._createAction("Save Project &As...\tCtrl+Shift+S", "Save the project under a different filename.", None, "Ctrl+Shift+S")
        projectMenu.addAction(self.actSaveProjectAs)
        projectMenu.addSeparator()
        act_import_game = self._createAction("&Import Game Settings...", "Import game settings.", None)
        projectMenu.addAction(act_import_game)
        projectMenu.addSeparator()
        self.actSaveProject.setEnabled(False)
        self.actSaveProjectAs.setEnabled(False)

        fileMenu = QMenu("&File")
        act_open = self._createAction("&Open ROM...\tCtrl+O", "Open a Shining Force 2 ROM (.BIN only)", self.OnOpen, "Ctrl+O")
        fileMenu.addAction(act_open)
        self.actSave = self._createAction("&Save ROM\tCtrl+S", "Save the currently loaded ROM", self.OnSave, "Ctrl+S")
        fileMenu.addAction(self.actSave)
        self.actSaveAs = self._createAction("Save ROM &As...\tCtrl+Shift+S", "Save the ROM under a different filename", self.OnSaveAs, "Ctrl+Shift+S")
        fileMenu.addAction(self.actSaveAs)
        fileMenu.addSeparator()
        self.actClose = self._createAction("&Close ROM\tCtrl+X", "Close the currently loaded ROM", self.OnClose, "Ctrl+X")
        fileMenu.addAction(self.actClose)
        fileMenu.addSeparator()
        act_exit = self._createAction("E&xit\tCtrl+Q", "Exit The Caravan", self.OnExit, "Ctrl+Q")
        fileMenu.addAction(act_exit)
        self.actSave.setEnabled(False)
        self.actSaveAs.setEnabled(False)
        self.actClose.setEnabled(False)

        helpMenu = QMenu("&Help")
        helpMenu.addAction(self._createAction("Changelog", "View The Caravan's changelog.", self.OnChangelog))

        menuBar.addMenu(projectMenu)
        menuBar.addMenu(fileMenu)
        menuBar.addMenu(helpMenu)

        self.initLayoutTree()
        self.layoutTree.itemActivated.connect(self.OnLayoutTreeItem)
        self.closeEvent = self.OnExit

    def _createAction(self, text, statusTip=None, callback=None, shortcut=None):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        if statusTip:
            action.setStatusTip(statusTip)
        if callback:
            action.triggered.connect(callback)
        return action

    def OnLayoutTreeItem(self, item, column):
        if item.childCount() == 0:
            self.spawnPluginWindow(item)

    def OnNewProject(self):
        dlg = NewProjectDialog(self)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.romCtrl.text()
            paths = fn.split("\\")
            self.dirname = "\\".join(paths[:-1])
            self.filename = paths[-1]
            self.project = layout.Project("Untitled Project")
            if self.settings.history["ROMs"].count(fn):
                self.settings.history["ROMs"].remove(fn)
            self.settings.history["ROMs"].insert(0, fn)
            self.initNewProject(fn)

    def OnOpen(self, hack=False):
        if self.rom:
            if self.confirmClose() != QMessageBox.No:
                return

        dlg = QFileDialog(self, "Open Shining Force 2 ROM (.BIN)", "", "*.bin")
        dlg.setFileMode(QFileDialog.ExistingFile)
        datadlg = QFileDialog(self, "Open External Data File", "", "*.txt;*.dat")
        datadlg.setFileMode(QFileDialog.ExistingFile)

        validROM = False
        validDF = False

        while not validROM:
            if dlg.exec() != QDialog.Accepted:
                break

            self.filename = dlg.selectedFiles()[0].split('/')[-1]
            self.dirname = os.path.dirname(dlg.selectedFiles()[0])
            fn = pathjoin(self.dirname, self.filename)

            with open(fn, 'rb') as file:
                file.seek(0x150)
                verify = file.read(15).decode('ascii')

            if verify != "SHINING FORCE 2":
                QMessageBox.warning(self, self.baseTitle, "The file you selected is not a valid Shining Force 2 ROM in .BIN format.")
                continue

            validROM = True
            self.project = layout.Project("Untitled Project")

            if self.settings.history["ROMs"].count(fn):
                self.settings.history["ROMs"].remove(fn)
            self.settings.history["ROMs"].insert(0, fn)

            # Запрос внешнего data-файла
            datafile = None
            if not self.dataFile:
                decision = None
                while not validDF and decision != QDialog.Rejected:
                    decision = datadlg.exec()
                    if decision == QDialog.Accepted:
                        self.datadirname = os.path.dirname(datadlg.selectedFiles()[0])
                        self.datafilename = datadlg.selectedFiles()[0].split('/')[-1]
                        datafile = open(pathjoin(self.datadirname, self.datafilename), 'r')
                        success, result = self.parseDataFile(datafile)
                        if success:
                            validDF = True
                        else:
                            datafile.close()
                            QMessageBox.critical(self, self.baseTitle, "The file you selected is not a valid external data file.")
            else:
                datafile = open(pathjoin(self.datadirname, self.datafilename), 'r')

            self.dataFile = datafile

            # Проверка на 2MB ROM
            romSize = os.path.getsize(fn)
            if romSize == 0x200000:
                warn = QMessageBox(self)
                warn.setWindowTitle(self.baseTitle)
                warn.setText("You have opened a 2MB SF2 ROM. Create a 4MB expanded ROM now?")
                warn.setIcon(QMessageBox.Warning)
                warn.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                if warn.exec() != QMessageBox.Yes:
                    return

                saveDlg = QFileDialog(self, "Save Shining Force 2 ROM (.BIN) As", "", "*.bin")
                saveDlg.setAcceptMode(QFileDialog.AcceptSave)
                if saveDlg.exec() != QDialog.Accepted:
                    return
                path = saveDlg.selectedFiles()[0]

                QMessageBox.information(self, self.baseTitle, "Creating 4MB expanded ROM. This may take a while...")
                with open(fn, 'rb') as file:
                    r = rom.ROM(file)
                r.expandROM(path)
                QMessageBox.information(self, self.baseTitle, "4MB ROM created. Now open it for editing.")
                self.initNewProject(path)   # здесь datafile не передаётся, будет None
                return
            else:
                self.initNewProject(fn, datafile)
            break

        dlg.deleteLater()
        datadlg.deleteLater()

    def OnSave(self):
        self.saveFile()

    def OnSaveAs(self):
        dlg = QFileDialog(self, "Save Shining Force 2 ROM (.BIN) As", "", "*.bin")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        if dlg.exec() == QDialog.Accepted:
            fn = dlg.selectedFiles()[0].split('/')[-1]
            dn = os.path.dirname(dlg.selectedFiles()[0])
            path = pathjoin(dn, fn)
            if self.saveFile(path):
                self.filename = fn
                self.dirname = dn
                self.setWindowTitle(self.baseTitle + " - [ " + self.dirname + "\\" + self.filename + " ]")
                self.rom.file.close()
                self.rom.file = open(pathjoin(self.dirname, self.filename), 'rb')

    def OnClose(self):
        if self.confirmClose() == QMessageBox.No:
            if self.rom.dataFile:
                dlg = QMessageBox(self)
                dlg.setWindowTitle(self.baseTitle)
                dlg.setText("Close external data file '%s' as well?" % pathjoin(self.datadirname, self.datafilename))
                dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
                dlg.setIcon(QMessageBox.Question)
                res = dlg.exec()
                if res == QMessageBox.Yes:
                    self.dataFile.close()
                    self.dataFile = None
                    self.datadirname = ""
                    self.datafilename = ""
                elif res == QMessageBox.Cancel:
                    return
            self.closeROM()
            self.actSave.setEnabled(False)
            self.actSaveAs.setEnabled(False)

    def OnExit(self, event=None):
        if event:
            event.ignore()
        if self.confirmClose() == QMessageBox.No:
            if self.rom:
                self.closeROM()
            self.settings.save()
            self.app.quit()

    def OnChangelog(self):
        dlg = QMessageBox(self)
        dlg.setWindowTitle(self.baseTitle + " - Changelog")
        dlg.setText(changelog.changeLog)
        dlg.exec()

    def initNewProject(self, romfn, datafile=None):
        self.loadROM(romfn, datafile)
        self.layoutTree.init()
        self.updateTitle()

    def loadROM(self, romfn, datafile=None):
        f = open(romfn, "rb")
        self.rom = rom.ROM(f)
        dlg = self.createLoadingDialog("Loading ROM...")
        if datafile:
            self.dataFile = datafile
            self.rom.dataFile = datafile
            self.rom.names = self.parseDataFile(datafile)[1]
        self.rom.initData()
        dlg.close()
        self.actSaveProjectAs.setEnabled(True)
        self.actClose.setEnabled(True)

    def initLayoutTree(self):
        dock = QDockWidget("Layout Tree", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.layoutTree = LayoutTree(self, -1)
        dock.setWidget(self.layoutTree)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    def saveFile(self, path=""):
        gen = self.rom.writeAllData()
        texts, pieces = next(gen)

        dlg = QDialog(self)
        dlg.setWindowTitle("Saving...")
        dlg.setFixedSize(350, 280)
        dlg.setWindowIcon(icon)
        dlg.setWindowModality(Qt.ApplicationModal)

        dlgSizer = QVBoxLayout(dlg)
        dlgMainSizer = QVBoxLayout()
        dlgText1Sizer = QHBoxLayout()
        dlgText2Sizer = QHBoxLayout()

        dlgSubSavingText = QLabel("Saving...")
        dlgSubSavingText.setFont(self.subFont)
        dlgSubPercentText = QLabel("0%")
        dlgSubPercentText.setFont(self.headerFont)
        dlgSubPercentText.setAlignment(Qt.AlignRight)

        dlgText1Sizer.addWidget(dlgSubSavingText)
        dlgText1Sizer.addStretch()
        dlgText1Sizer.addWidget(dlgSubPercentText)

        dlgSubGauge = QProgressBar()
        dlgSubGauge.setRange(0, 100)

        dlgActionText = QLabel("")
        dlgActionText.setFont(self.subFont)
        dlgActionText.setAlignment(Qt.AlignCenter)

        dlgSavingText = QLabel("")
        dlgSavingText.setFont(self.subFont)
        dlgPercentText = QLabel("0%")
        dlgPercentText.setFont(self.headerFont)
        dlgPercentText.setAlignment(Qt.AlignRight)

        dlgText2Sizer.addWidget(dlgSavingText)
        dlgText2Sizer.addStretch()
        dlgText2Sizer.addWidget(dlgPercentText)

        dlgGauge = QProgressBar()
        dlgGauge.setRange(0, 100)

        dlgCancelButton = QPushButton("Cancel")
        dlgCancelButton.setFont(self.subFont)
        dlgCancelButton.clicked.connect(self.cancelSaving)

        dlgMainSizer.addLayout(dlgText2Sizer)
        dlgMainSizer.addWidget(dlgGauge)
        dlgMainSizer.addLayout(dlgText1Sizer)
        dlgMainSizer.addWidget(dlgSubGauge)
        dlgMainSizer.addWidget(dlgActionText)
        dlgMainSizer.addWidget(dlgCancelButton, 0, Qt.AlignCenter)

        dlgSizer.addLayout(dlgMainSizer)

        dlgSubSavingText.setText("Saving %s..." % texts[0])
        dlgSavingText.setText("Section %i of %i..." % (1, len(pieces)))
        dlg.show()

        sectionsToUpdate = list(filter(lambda a: a > 0, pieces))
        if len(sectionsToUpdate) == 0:
            percentPerPiece = 100.0
        else:
            percentPerPiece = 100.0 / len(sectionsToUpdate)

        succeeded = True
        allPieces = 0
        result = next(gen)

        for cur in range(len(pieces)):
            curPiece = 0
            pieceProgress = 0
            dlgSubSavingText.setText("Saving %s..." % texts[cur])
            dlgSavingText.setText("Section %i of %i..." % (cur+1, len(pieces)))
            QApplication.processEvents()
            if pieces[cur]:
                percentPerEntry = 100.0 / pieces[cur]
                while result is not None:
                    if self.pendingCancel:
                        break
                    if result == "Moving on...":
                        curPiece += 1
                        allPieces += 1
                        pieceProgress = 0
                    elif isinstance(result, (float, int)):
                        pieceProgress = result
                    else:
                        dlgActionText.setText(result)
                    progressSub = percentPerEntry * curPiece + percentPerEntry * pieceProgress / 100
                    progress = percentPerPiece * allPieces / 100.0 + progressSub * percentPerPiece / 100.0
                    dlgSubGauge.setValue(int(progressSub))
                    dlgSubPercentText.setText("%i%%" % int(progressSub))
                    dlgGauge.setValue(int(progress))
                    dlgPercentText.setText("%i%%" % int(progress))
                    QApplication.processEvents()
                    result = next(gen)
            if self.pendingCancel:
                break

        dlg.setWindowModality(Qt.NonModal)
        if not self.pendingCancel:
            fileStr = next(gen)
            dlgSubGauge.setValue(100)
            dlgSubPercentText.setText("100%")
            dlgGauge.setValue(100)
            dlgPercentText.setText("100%")
            dlgSubSavingText.setText("Done!")
            dlgSavingText.setText("%i of %i sections saved properly." % (len(sectionsToUpdate), len(sectionsToUpdate)))
            dlgActionText.setText("")
            dlgCancelButton.setText("OK")

            if path:
                outfile = open(path, 'wb')
            else:
                outfile = open(pathjoin(self.dirname, self.filename), 'wb')
            outfile.write(fileStr)
            outfile.flush()
            outfile.close()

            self.modify(False)
            self.rom.massModify(False)
            QMessageBox.information(self, self.baseTitle, "File saved successfully.")
            for i in self.layoutTree.allItems:
                self.layoutTree.modify(i, False)
        else:
            succeeded = False
            QMessageBox.warning(self, self.baseTitle, "Saving cancelled.")

        self.pendingCancel = False
        dlg.accept()
        dlg.deleteLater()
        return succeeded

    def cancelSaving(self):
        self.pendingCancel = True
        dlg = self.sender().parentWidget()
        if dlg and isinstance(dlg, QDialog):
            dlg.reject()

    def confirmClose(self):
        success = QMessageBox.No
        if self.rom and self.rom.modified:
            dlg = QMessageBox(self)
            dlg.setWindowTitle(self.baseTitle)
            dlg.setText("Save changes to '%s'?" % pathjoin(self.dirname, self.filename))
            dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            dlg.setIcon(QMessageBox.Question)
            success = dlg.exec()
            if success == QMessageBox.Yes:
                self.saveFile()
                success = QMessageBox.No
        return success

    def closeROM(self):
        self.rom.close()
        del self.rom
        self.rom = None
        self.filename = ""
        self.dirname = ""
        self.setWindowTitle(self.baseTitle)
        self.layoutTree.clear()
        for f in self.frames:
            f.close()
            del f
        self.frames = []
        for v in self.panels.values():
            v.close()
            del v
        self.panels = {}
        self.actSaveProject.setEnabled(False)
        self.actSaveProjectAs.setEnabled(False)
        self.actClose.setEnabled(False)

    def modify(self, modified=True):
        if self.rom.modified is not modified:
            self.rom.modified = modified
            self.updateTitle(modified)
            self.actSaveProject.setEnabled(modified)
            self.actSave.setEnabled(modified)
            self.actSaveAs.setEnabled(modified)

    def updateTitle(self, modified=False):
        modifiedStr = ["", "* "][modified]
        self.setWindowTitle(self.baseTitle + " - [ " + modifiedStr + self.dirname + "\\" + self.filename + " ]")

    def spawnPluginWindow(self, item):
        name = item.text(0)
        pc = panellist.getPanelClass(name)
        dlg = self.createLoadingDialog(f"Loading {name} Section...")
        frame = rompanel.ROMFrame(self, -1, pc)
        frame.setWindowIcon(icon)
        if self.mdi_area:
            self.mdi_area.addSubWindow(frame)
        frame.show()
        dlg.close()

    def createLoadingDialog(self, name):
        dlg = QDialog(self)
        dlg.setWindowTitle(self.baseTitle)
        dlg.setFixedSize(400, 110)
        dlgSizer = QVBoxLayout(dlg)
        dlgText = QLabel(name)
        dlgText.setFont(self.editFont)
        dlgText.setAlignment(Qt.AlignCenter)
        dlgSizer.addWidget(dlgText)
        dlg.show()
        QApplication.processEvents()
        return dlg

    def showError(self, text):
        if not self.isErring:
            self.isErring = True
            dlg = QMessageBox(self)
            dlg.setWindowTitle(self.baseTitle)
            dlg.setText(text + "\nCopy the error to the clipboard?")
            dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            dlg.setIcon(QMessageBox.Critical)
            if dlg.exec() == QMessageBox.Yes:
                QApplication.clipboard().setText(text)
            self.isErring = False

    def parseDataFile(self, datafile):
        valid = True
        data = {}
        curSection = ""
        datafile.seek(0)
        for line in datafile:
            if line.strip(" ") == "\n":
                continue
            segments = line.split("=")
            if len(segments) < 2:
                valid = False
                break
            key = segments[0].strip()
            value = "=".join(segments[1:]).lstrip().rstrip()
            if key == "section":
                curSection = value
                if curSection not in data:
                    data[curSection] = {}
            elif key.isdigit():
                if not curSection:
                    valid = False
                    break
                data[curSection][int(key)] = value
            elif key.find(",") != -1:
                args = key.replace(" ", "").split(",")
                key_int = int(args[0])
                subkey = int(args[1])
                if curSection not in data:
                    data[curSection] = {}
                if key_int not in data[curSection]:
                    data[curSection][key_int] = {}
                if len(args) == 3:
                    subkey2 = int(args[2])
                    if subkey not in data[curSection][key_int]:
                        data[curSection][key_int][subkey] = {}
                    data[curSection][key_int][subkey][subkey2] = value
                else:
                    data[curSection][key_int][subkey] = value
            else:
                valid = False
                break
        return valid, data


class NewProjectDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Create New Project")
        self.parent = parent
        sizer = QVBoxLayout(self)
        st1 = QWidget()
        st1_layout = QVBoxLayout(st1)
        st1_label = QLabel("ROM Info")
        st1_label.setStyleSheet("border: 1px solid black;")
        st1_layout.addWidget(st1_label)
        self.romCtrl = QLineEdit()
        st1_layout.addWidget(QLabel("ROM File:"))
        st1_layout.addWidget(self.romCtrl)
        st1platformSizer = QHBoxLayout()
        platformText = QLabel("Platform: ")
        self.platformCtrl = QComboBox()
        st1platformSizer.addWidget(platformText)
        st1platformSizer.addWidget(self.platformCtrl)
        st1_layout.addLayout(st1platformSizer)
        sizer.addWidget(st1)
        self.okBtn = QPushButton("OK")
        self.cancelBtn = QPushButton("Cancel")
        btnSizer = QHBoxLayout()
        btnSizer.addWidget(self.okBtn)
        btnSizer.addWidget(self.cancelBtn)
        sizer.addLayout(btnSizer)
        self.okBtn.clicked.connect(self.OnConfirm)
        self.cancelBtn.clicked.connect(self.OnClose)
        self.platformCtrl.addItems(["Sega Genesis"])
        self.platformCtrl.setCurrentIndex(0)
        self.platformCtrl.setEnabled(False)

    def OnConfirm(self):
        try:
            with open(self.romCtrl.text(), "rb"):
                pass
        except IOError:
            QMessageBox.warning(self, self.parent.baseTitle + " -- Error", "Invalid ROM file.")
            return
        self.accept()

    def OnClose(self):
        self.reject()


mw = MainFrame(None, -1, app)
mw.show()
app.exec()