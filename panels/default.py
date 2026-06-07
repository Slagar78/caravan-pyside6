import rompanel
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt

class DefaultPanel(rompanel.ROMPanel):
    def init(self):
        label = QLabel("This feature is not implemented yet.")
        label.setAlignment(Qt.AlignLeft)
        self.sizer.addWidget(label, 0, 0)

class SF2EditPanel(rompanel.ROMPanel):
    def init(self):
        label1 = QLabel("This feature is not implemented yet.")
        label2 = QLabel("However, it is implemented in SF2Edit.exe.")
        label1.setAlignment(Qt.AlignLeft)
        label2.setAlignment(Qt.AlignLeft)
        self.sizer.addWidget(label1, 0, 0)
        self.sizer.addWidget(label2, 1, 0)
        # Для отступа снизу первого лейбла добавим небольшой вертикальный интервал
        self.sizer.setRowStretch(0, 0)
        self.sizer.setRowStretch(1, 1)