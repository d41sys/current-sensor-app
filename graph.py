from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PySide6.QtCore import QTimer
import pyqtgraph as pg
import random
import sys
from PySide6.QtCore import Qt

class AdvancedChartWidget(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Control buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.clear_btn = QPushButton("Clear")
        self.export_btn = QPushButton("Export")
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.export_btn)
        main_layout.addLayout(btn_layout)
        
        # Chart
        self.plot_widget = pg.PlotWidget()
        main_layout.addWidget(self.plot_widget)
        
        # Styling
        self.plot_widget.setBackground('w')
        self.plot_widget.setTitle("Real-time Data Monitor", color="k", size="16pt")
        self.plot_widget.setLabel('left', 'Value', units='A', color='k')
        self.plot_widget.setLabel('bottom', 'Time', units='s', color='k')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend()
        
        # Data
        self.data1 = []
        self.data2 = []
        self.max_points = 50
        
        # Curves
        self.curve1 = self.plot_widget.plot(
            pen=pg.mkPen(color=(75, 192, 192), width=2),
            symbol='o',
            symbolSize=5,
            name="Sensor 1"
        )
        # self.curve2 = self.plot_widget.plot(
        #     pen=pg.mkPen(color=(255, 99, 132), width=2, style=Qt.PenStyle.DashLine),
        #     name="Sensor 2"
        # )
        
        # Connect buttons
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        self.clear_btn.clicked.connect(self.clear)
        self.export_btn.clicked.connect(self.export)
        
        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
    
    def start(self):
        self.timer.start(100)
    
    def stop(self):
        self.timer.stop()
    
    def clear(self):
        self.data1.clear()
        self.data2.clear()
        self.curve1.setData([], [])
        self.curve2.setData([], [])
    
    def export(self):
        exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
        exporter.export('chart.png')
        print("Exported to chart.png")
    
    def update_plot(self):
        self.data1.append(random.random() * 100)
        self.data2.append(random.random() * 80 + 20)
        
        if len(self.data1) > self.max_points:
            self.data1.pop(0)
            self.data2.pop(0)
        
        x = list(range(len(self.data1)))
        self.curve1.setData(x, self.data1)
        self.curve2.setData(x, self.data2)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Advanced PyQtGraph Example")
    window.setGeometry(100, 100, 1000, 600)
    
    chart = AdvancedChartWidget()
    window.setCentralWidget(chart)
    window.show()
    
    sys.exit(app.exec())