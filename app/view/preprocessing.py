# coding: utf-8
import os
import pandas as pd
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                                QTextEdit, QFileDialog, QTableWidget, QTableWidgetItem,
                                QHeaderView, QSplitter, QDialog, QGridLayout,
                                QSizePolicy, QStackedWidget, QFrame, QMenu,
                                QListView, QTreeView, QAbstractItemView)
from PySide6.QtGui import QAction
from qfluentwidgets import (ScrollArea, PushButton, ComboBox, PrimaryPushButton, 
                            CheckBox, SpinBox, DoubleSpinBox, CardWidget, 
                            StrongBodyLabel, BodyLabel, InfoBar, InfoBarPosition,
                            TabWidget, FluentIcon, PrimaryDropDownPushButton, 
                            RoundMenu, Action, DropDownPushButton)
import pyqtgraph as pg
from pyqtgraph.exporters import ImageExporter

# Import visualization functions
from visualization import (load_signals_from_folder, get_temporal_windows, 
                           apply_filter_to_df, compute_stats, 
                           compute_h2_from_current, compute_o2_from_current)


class VisualizationPopup(QDialog):
    """Popup window for data visualization with multiple tabs"""
    
    def __init__(self, folder_path, dfs_raw, time_mask, window_index, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.dfs_raw = dfs_raw
        self.time_mask = time_mask
        self.window_index = window_index
        self.dfs_filtered = []
        self.stats = []
        self.h2_data = []
        self.o2_data = []
        
        self.setWindowTitle(f"Visualization - {os.path.basename(folder_path)} (Window {window_index})")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Set background color
        self.setStyleSheet("QDialog { background-color: #f8fafc; }")
        
        self.__initUI()
        self.__applyFilters()
    
    def __initUI(self):
        """Initialize the popup UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # === Filter Controls Section ===
        filter_card = CardWidget(self)
        filter_card.setStyleSheet("CardWidget { border: 1px solid #dcdcdc; border-radius: 6px; }")
        filter_layout = QHBoxLayout(filter_card)
        
        filter_layout.addWidget(StrongBodyLabel("Filter Settings:"))
        
        # Filter Type
        filter_layout.addWidget(BodyLabel("Type:"))
        self.filter_type_combo = ComboBox()
        self.filter_type_combo.addItems(["low", "high", "bandpass"])
        self.filter_type_combo.setFixedWidth(100)
        filter_layout.addWidget(self.filter_type_combo)
        
        # Cutoff Frequency
        filter_layout.addWidget(BodyLabel("Cutoff (Hz):"))
        self.cutoff_spin = DoubleSpinBox()
        self.cutoff_spin.setRange(0.001, 100.0)
        self.cutoff_spin.setValue(0.05)
        self.cutoff_spin.setDecimals(3)
        self.cutoff_spin.setSingleStep(0.001)
        self.cutoff_spin.setFixedWidth(150)
        filter_layout.addWidget(self.cutoff_spin)
        
        # Filter Order
        filter_layout.addWidget(BodyLabel("Order:"))
        self.filter_order_spin = SpinBox()
        self.filter_order_spin.setRange(1, 10)
        self.filter_order_spin.setValue(4)
        self.filter_order_spin.setFixedWidth(150)
        filter_layout.addWidget(self.filter_order_spin)
        
        # Apply Filter Button
        self.apply_filter_btn = PrimaryPushButton("Apply Filter")
        self.apply_filter_btn.clicked.connect(self.__applyFilters)
        filter_layout.addWidget(self.apply_filter_btn)
        
        filter_layout.addStretch()
        
        # Export Button with dropdown menu
        self.export_menu = RoundMenu(parent=self)
        self.export_menu.addAction(Action(FluentIcon.DOCUMENT, 'Export as 1 File (11 columns)', triggered=self.__exportSingleFile))
        self.export_menu.addAction(Action(FluentIcon.FOLDER, 'Export as 9 Files (separate segments)', triggered=self.__exportMultipleFiles))
        
        self.export_btn = DropDownPushButton(FluentIcon.SHARE, 'Export Data')
        self.export_btn.setMenu(self.export_menu)
        filter_layout.addWidget(self.export_btn)
        
        # Export Charts Button
        self.export_charts_menu = RoundMenu(parent=self)
        self.export_charts_menu.addAction(Action(FluentIcon.PHOTO, 'Export Current Tab Chart', triggered=self.__exportCurrentTabChart))
        self.export_charts_menu.addAction(Action(FluentIcon.ALBUM, 'Export All Charts', triggered=self.__exportAllCharts))
        
        self.export_charts_btn = DropDownPushButton(FluentIcon.SAVE, 'Export Charts')
        self.export_charts_btn.setMenu(self.export_charts_menu)
        filter_layout.addWidget(self.export_charts_btn)
        
        main_layout.addWidget(filter_card)
        
        # === TabWidget for Tabs ===
        self.tab_widget = TabWidget(self)
        self.tab_widget.setMovable(False)
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.setScrollable(False)
        self.tab_widget.tabBar.setAddButtonVisible(False)
        self.tab_widget.setTabMaximumWidth(500)  # Increase tab width to fit window
        
        # Tab 1: Current Signals (3x3 grid)
        self.signals_tab = QWidget()
        self.__initSignalsTab()
        
        # Tab 2: H2 Production
        self.h2_tab = QWidget()
        self.__initH2Tab()
        
        # Tab 3: O2 Production
        self.o2_tab = QWidget()
        self.__initO2Tab()
        
        # Tab 4: Heatmap
        self.heatmap_tab = QWidget()
        self.__initHeatmapTab()
        
        # Tab 5: Statistics
        self.stats_tab = QWidget()
        self.__initStatsTab()
        
        # Add tabs to TabWidget
        self.tab_widget.addPage(self.signals_tab, 'Current Signals', FluentIcon.IOT)
        self.tab_widget.addPage(self.h2_tab, 'H2 Production', FluentIcon.CALORIES)
        self.tab_widget.addPage(self.o2_tab, 'O2 Production', FluentIcon.CLOUD)
        self.tab_widget.addPage(self.heatmap_tab, 'Heatmap', FluentIcon.TILES)
        self.tab_widget.addPage(self.stats_tab, 'Statistics', FluentIcon.MARKET)
        
        main_layout.addWidget(self.tab_widget)
    
    def __initSignalsTab(self):
        """Initialize the 3x3 signals grid tab"""
        layout = QGridLayout(self.signals_tab)
        layout.setSpacing(5)
        
        self.signal_plots = []
        for i in range(9):
            row = i // 3
            col = i % 3
            
            plot_widget = pg.PlotWidget()
            plot_widget.setBackground('w')
            plot_widget.showGrid(x=True, y=True, alpha=0.3)
            plot_widget.setTitle(f"Segment {i+1}", size="10pt")
            plot_widget.setLabel('bottom', 'Time (s)', size="8pt")
            plot_widget.setLabel('left', 'Current (A)', size="8pt")
            
            self.signal_plots.append(plot_widget)
            layout.addWidget(plot_widget, row, col)
    
    def __initH2Tab(self):
        """Initialize H2 production tab"""
        layout = QVBoxLayout(self.h2_tab)
        
        # H2 cumulative plot
        self.h2_plot = pg.PlotWidget()
        self.h2_plot.setBackground('w')
        self.h2_plot.showGrid(x=True, y=True, alpha=0.3)
        self.h2_plot.setTitle("H2 Cumulative Production - All Segments")
        self.h2_plot.setLabel('bottom', 'Time (s)')
        self.h2_plot.setLabel('left', 'H2 Volume (L)')
        self.h2_plot.addLegend()
        layout.addWidget(self.h2_plot)
        
        # H2 bar chart
        self.h2_bar_plot = pg.PlotWidget()
        self.h2_bar_plot.setBackground('w')
        self.h2_bar_plot.showGrid(x=True, y=True, alpha=0.3)
        self.h2_bar_plot.setTitle("Total H2 Production per Segment")
        self.h2_bar_plot.setLabel('bottom', 'Segment')
        self.h2_bar_plot.setLabel('left', 'H2 Volume (L)')
        layout.addWidget(self.h2_bar_plot)
    
    def __initO2Tab(self):
        """Initialize O2 production tab"""
        layout = QVBoxLayout(self.o2_tab)
        
        # O2 cumulative plot
        self.o2_plot = pg.PlotWidget()
        self.o2_plot.setBackground('w')
        self.o2_plot.showGrid(x=True, y=True, alpha=0.3)
        self.o2_plot.setTitle("O2 Cumulative Production - All Segments")
        self.o2_plot.setLabel('bottom', 'Time (s)')
        self.o2_plot.setLabel('left', 'O2 Volume (L)')
        self.o2_plot.addLegend()
        layout.addWidget(self.o2_plot)
        
        # O2 bar chart
        self.o2_bar_plot = pg.PlotWidget()
        self.o2_bar_plot.setBackground('w')
        self.o2_bar_plot.showGrid(x=True, y=True, alpha=0.3)
        self.o2_bar_plot.setTitle("Total O2 Production per Segment")
        self.o2_bar_plot.setLabel('bottom', 'Segment')
        self.o2_bar_plot.setLabel('left', 'O2 Volume (L)')
        layout.addWidget(self.o2_bar_plot)
    
    def __initHeatmapTab(self):
        """Initialize heatmap tab"""
        layout = QGridLayout(self.heatmap_tab)
        
        # H2 Heatmap
        h2_container = QWidget()
        h2_layout = QVBoxLayout(h2_container)
        h2_layout.addWidget(StrongBodyLabel("H2 Production Heatmap (3×3)"))
        
        self.h2_heatmap = pg.PlotWidget()
        self.h2_heatmap.setBackground('w')
        self.h2_heatmap.setAspectLocked(True)
        h2_layout.addWidget(self.h2_heatmap)
        layout.addWidget(h2_container, 0, 0)
        
        # O2 Heatmap
        o2_container = QWidget()
        o2_layout = QVBoxLayout(o2_container)
        o2_layout.addWidget(StrongBodyLabel("O2 Production Heatmap (3×3)"))
        
        self.o2_heatmap = pg.PlotWidget()
        self.o2_heatmap.setBackground('w')
        self.o2_heatmap.setAspectLocked(True)
        o2_layout.addWidget(self.o2_heatmap)
        layout.addWidget(o2_container, 0, 1)
        
        # Mean Current Heatmap
        current_container = QWidget()
        current_layout = QVBoxLayout(current_container)
        current_layout.addWidget(StrongBodyLabel("Mean Current Heatmap (3×3)"))
        
        self.current_heatmap = pg.PlotWidget()
        self.current_heatmap.setBackground('w')
        self.current_heatmap.setAspectLocked(True)
        current_layout.addWidget(self.current_heatmap)
        layout.addWidget(current_container, 1, 0)
        
        # Std Heatmap
        var_container = QWidget()
        var_layout = QVBoxLayout(var_container)
        var_layout.addWidget(StrongBodyLabel("Current Std Heatmap (3×3)"))
        
        self.var_heatmap = pg.PlotWidget()
        self.var_heatmap.setBackground('w')
        self.var_heatmap.setAspectLocked(True)
        var_layout.addWidget(self.var_heatmap)
        layout.addWidget(var_container, 1, 1)
    
    def __initStatsTab(self):
        """Initialize statistics tab"""
        layout = QVBoxLayout(self.stats_tab)
        
        layout.addWidget(StrongBodyLabel("Summary Statistics"))
        
        self.stats_table = QTableWidget()
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.stats_table)
        
        # Bar charts for mean and variance
        charts_layout = QHBoxLayout()
        
        self.mean_bar_plot = pg.PlotWidget()
        self.mean_bar_plot.setBackground('w')
        self.mean_bar_plot.showGrid(x=True, y=True, alpha=0.3)
        self.mean_bar_plot.setTitle("Mean Current per Segment")
        self.mean_bar_plot.setLabel('bottom', 'Segment')
        self.mean_bar_plot.setLabel('left', 'Mean Current (A)')
        charts_layout.addWidget(self.mean_bar_plot)
        
        self.var_bar_plot = pg.PlotWidget()
        self.var_bar_plot.setBackground('w')
        self.var_bar_plot.showGrid(x=True, y=True, alpha=0.3)
        self.var_bar_plot.setTitle("Current Variance per Segment")
        self.var_bar_plot.setLabel('bottom', 'Segment')
        self.var_bar_plot.setLabel('left', 'Variance (A²)')
        charts_layout.addWidget(self.var_bar_plot)
        
        layout.addLayout(charts_layout)
    
    def __applyFilters(self):
        """Apply filters and update all visualizations"""
        filter_type = self.filter_type_combo.currentText()
        cutoff_hz = self.cutoff_spin.value()
        filter_order = self.filter_order_spin.value()
        
        self.dfs_filtered = []
        self.stats = []
        self.h2_data = []
        self.o2_data = []
        
        for i, df in enumerate(self.dfs_raw):
            # Extract window
            df_win = df.loc[self.time_mask].copy()
            
            # Apply filter
            if filter_type == "bandpass":
                cutoff_band = [cutoff_hz / 2, cutoff_hz * 2]
            else:
                cutoff_band = cutoff_hz
            
            df_filt = apply_filter_to_df(df_win, filter_type, cutoff_band, filter_order)
            self.dfs_filtered.append(df_filt)
            
            # Compute statistics
            mean_val, std_val = compute_stats(df_filt)
            self.stats.append((mean_val, std_val))
            
            # Compute H2 production
            t_rel, h2 = compute_h2_from_current(df_filt)
            # Use actual time instead of relative
            t_actual = df_filt["time"].values
            self.h2_data.append((t_actual, h2))
            
            # Compute O2 production
            t_rel_o, o2 = compute_o2_from_current(df_filt)
            # Use actual time instead of relative
            t_actual = df_filt["time"].values
            self.o2_data.append((t_actual, o2))
        
        # Update all plots
        self.__updateSignalsPlots()
        self.__updateH2Plots()
        self.__updateO2Plots()
        self.__updateHeatmaps()
        self.__updateStatsTab()
    
    def __updateSignalsPlots(self):
        """Update the 3x3 signal plots"""
        colors = [
            (255, 0, 0), (0, 200, 0), (0, 0, 255),
            (255, 165, 0), (128, 0, 128), (0, 200, 200),
            (200, 0, 100), (100, 200, 0), (100, 0, 200)
        ]
        
        for i, plot_widget in enumerate(self.signal_plots):
            plot_widget.clear()
            
            if i < len(self.dfs_filtered):
                df_filt = self.dfs_filtered[i]
                t_actual = df_filt["time"].values
                
                # Raw signal
                plot_widget.plot(t_actual, df_filt["current"].values,
                               pen=pg.mkPen(color=(200, 200, 200), width=1),
                               name='Raw')
                
                # Filtered signal
                if "current_filt" in df_filt.columns:
                    plot_widget.plot(t_actual, df_filt["current_filt"].values,
                                   pen=pg.mkPen(color=colors[i], width=2),
                                   name='Filtered')
                
                # Mean line
                mean_val, std_val = self.stats[i]
                plot_widget.addLine(y=mean_val, pen=pg.mkPen('g', width=1, style=Qt.DashLine))
                
                plot_widget.setTitle(f"Seg {i+1}: μ={mean_val:.4f}A ± {std_val:.4f}A", size="9pt")
    
    def __updateH2Plots(self):
        """Update H2 production plots"""
        self.h2_plot.clear()
        self.h2_bar_plot.clear()
        
        colors = [
            (255, 0, 0), (0, 200, 0), (0, 0, 255),
            (255, 165, 0), (128, 0, 128), (0, 200, 200),
            (200, 0, 100), (100, 200, 0), (100, 0, 200)
        ]
        
        h2_totals = []
        for i, (t_rel, h2) in enumerate(self.h2_data):
            self.h2_plot.plot(t_rel, h2, pen=pg.mkPen(color=colors[i], width=2),
                            name=f'Seg {i+1}')
            h2_totals.append(h2[-1] if len(h2) > 0 else 0)
        
        # Bar chart
        x = np.arange(1, 10)
        bar_item = pg.BarGraphItem(x=x, height=h2_totals, width=0.6, brush=(75, 192, 192))
        self.h2_bar_plot.addItem(bar_item)
        # Set integer ticks
        self.h2_bar_plot.getAxis('bottom').setTicks([[(i, str(i)) for i in range(1, 10)]])
    
    def __updateO2Plots(self):
        """Update O2 production plots"""
        self.o2_plot.clear()
        self.o2_bar_plot.clear()
        
        colors = [
            (255, 0, 0), (0, 200, 0), (0, 0, 255),
            (255, 165, 0), (128, 0, 128), (0, 200, 200),
            (200, 0, 100), (100, 200, 0), (100, 0, 200)
        ]
        
        o2_totals = []
        for i, (t_rel, o2) in enumerate(self.o2_data):
            self.o2_plot.plot(t_rel, o2, pen=pg.mkPen(color=colors[i], width=2),
                            name=f'Seg {i+1}')
            o2_totals.append(o2[-1] if len(o2) > 0 else 0)
        
        # Bar chart
        x = np.arange(1, 10)
        bar_item = pg.BarGraphItem(x=x, height=o2_totals, width=0.6, brush=(255, 127, 80))
        self.o2_bar_plot.addItem(bar_item)
        # Set integer ticks
        self.o2_bar_plot.getAxis('bottom').setTicks([[(i, str(i)) for i in range(1, 10)]])
    
    def __updateHeatmaps(self):
        """Update heatmap visualizations"""
        # Prepare data
        h2_totals = [self.h2_data[i][1][-1] if len(self.h2_data[i][1]) > 0 else 0 for i in range(9)]
        o2_totals = [self.o2_data[i][1][-1] if len(self.o2_data[i][1]) > 0 else 0 for i in range(9)]
        mean_currents = [self.stats[i][0] for i in range(9)]
        std_currents = [self.stats[i][1] for i in range(9)]
        
        # Create 3x3 matrices
        h2_matrix = np.array(h2_totals).reshape(3, 3)
        o2_matrix = np.array(o2_totals).reshape(3, 3)
        current_matrix = np.array(mean_currents).reshape(3, 3)
        std_matrix = np.array(std_currents).reshape(3, 3)
        
        # Update heatmaps
        self.__drawHeatmap(self.h2_heatmap, h2_matrix, 'hot')
        self.__drawHeatmap(self.o2_heatmap, o2_matrix, 'hot')
        self.__drawHeatmap(self.current_heatmap, current_matrix, 'viridis')
        self.__drawHeatmap(self.var_heatmap, std_matrix, 'plasma')
    
    def __drawHeatmap(self, plot_widget, data, colormap='hot'):
        """Draw a heatmap on a plot widget"""
        plot_widget.clear()
        
        # Create ImageItem
        img = pg.ImageItem()
        img.setImage(data.T)  # Transpose for correct orientation
        
        # Set colormap
        if colormap == 'hot':
            colors = [(20, 20, 60), (180, 30, 30), (220, 120, 20), (255, 200, 50)]
        elif colormap == 'viridis':
            colors = [(68, 1, 84), (59, 82, 139), (33, 145, 140), (94, 201, 98), (253, 231, 37)]
        else:  # plasma
            colors = [(13, 8, 135), (126, 3, 168), (204, 71, 120), (248, 149, 64), (240, 249, 33)]
        
        cmap = pg.ColorMap(pos=np.linspace(0, 1, len(colors)), color=colors)
        img.setLookupTable(cmap.getLookupTable())
        
        plot_widget.addItem(img)
        plot_widget.setRange(xRange=[0, 3], yRange=[0, 3])
        
        # Set integer ticks for axes (segments 1-3 on both axes)
        plot_widget.getAxis('bottom').setTicks([[(i + 0.5, str(i + 1)) for i in range(3)]])
        plot_widget.getAxis('left').setTicks([[(i + 0.5, str(i + 1)) for i in range(3)]])
        
        # Add text labels with contrasting color
        for i in range(3):
            for j in range(3):
                text = pg.TextItem(f'{data[i, j]:.4f}', color='black', anchor=(0.5, 0.5))
                text.setPos(j + 0.5, i + 0.5)
                plot_widget.addItem(text)
    
    def __updateStatsTab(self):
        """Update statistics table and charts"""
        # Update table
        headers = ['Segment', 'Mean (A)', 'Std (A)', 'Variance (A²)', 'H2 (L)', 'O2 (L)']
        self.stats_table.setColumnCount(len(headers))
        self.stats_table.setRowCount(9)
        self.stats_table.setHorizontalHeaderLabels(headers)
        
        means = []
        variances = []
        
        for i in range(9):
            mean_val, std_val = self.stats[i]
            var_val = std_val ** 2
            h2_total = self.h2_data[i][1][-1] if len(self.h2_data[i][1]) > 0 else 0
            o2_total = self.o2_data[i][1][-1] if len(self.o2_data[i][1]) > 0 else 0
            
            means.append(mean_val)
            variances.append(var_val)
            
            self.stats_table.setItem(i, 0, QTableWidgetItem(f'{i + 1}'))
            self.stats_table.setItem(i, 1, QTableWidgetItem(f'{mean_val:.6f}'))
            self.stats_table.setItem(i, 2, QTableWidgetItem(f'{std_val:.6f}'))
            self.stats_table.setItem(i, 3, QTableWidgetItem(f'{var_val:.6f}'))
            self.stats_table.setItem(i, 4, QTableWidgetItem(f'{h2_total:.6f}'))
            self.stats_table.setItem(i, 5, QTableWidgetItem(f'{o2_total:.6f}'))
        
        # Update bar charts
        self.mean_bar_plot.clear()
        self.var_bar_plot.clear()
        
        x = np.arange(1, 10)
        mean_bar = pg.BarGraphItem(x=x, height=means, width=0.6, brush=(70, 130, 180))
        self.mean_bar_plot.addItem(mean_bar)
        # Set integer ticks
        self.mean_bar_plot.getAxis('bottom').setTicks([[(i, str(i)) for i in range(1, 10)]])
        
        var_bar = pg.BarGraphItem(x=x, height=variances, width=0.6, brush=(255, 165, 0))
        self.var_bar_plot.addItem(var_bar)
        # Set integer ticks
        self.var_bar_plot.getAxis('bottom').setTicks([[(i, str(i)) for i in range(1, 10)]])
    
    def __exportSingleFile(self):
        """Export all data as a single CSV file with 11 columns (timestamp, 9x current, voltage)"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Single CSV File", f"combined_window_{self.window_index}.csv", "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                combined_data = []
                
                for idx in range(len(self.dfs_filtered[0])):
                    row = [self.dfs_filtered[0].iloc[idx]['time']]
                    
                    for i in range(9):
                        if 'current_filt' in self.dfs_filtered[i].columns:
                            row.append(self.dfs_filtered[i].iloc[idx]['current_filt'])
                        else:
                            row.append(self.dfs_filtered[i].iloc[idx]['current'])
                    
                    if 'voltage' in self.dfs_filtered[0].columns:
                        row.append(self.dfs_filtered[0].iloc[idx]['voltage'])
                    else:
                        row.append(0.0)
                    
                    combined_data.append(row)
                
                columns = ['timestamp'] + [f'i{i+1}' for i in range(9)] + ['voltage']
                df_export = pd.DataFrame(combined_data, columns=columns)
                df_export.to_csv(file_path, index=False)
                
                InfoBar.success(
                    title="Export Complete",
                    content=f"Saved as {os.path.basename(file_path)} ({len(df_export)} rows, 11 columns)",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
            except Exception as e:
                InfoBar.error(
                    title="Export Error",
                    content=str(e),
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=5000
                )
    
    def __exportMultipleFiles(self):
        """Export data as 9 separate CSV files (one per segment)"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Export Folder", "")
        
        if folder_path:
            try:
                for i, df_filt in enumerate(self.dfs_filtered):
                    file_path = os.path.join(folder_path, f'segment_{i+1}_window_{self.window_index}.csv')
                    df_filt.to_csv(file_path, index=False)
                
                stats_data = []
                for i in range(9):
                    mean_val, std_val = self.stats[i]
                    h2_total = self.h2_data[i][1][-1] if len(self.h2_data[i][1]) > 0 else 0
                    o2_total = self.o2_data[i][1][-1] if len(self.o2_data[i][1]) > 0 else 0
                    stats_data.append({
                        'Segment': i + 1,
                        'Mean_A': mean_val,
                        'Std_A': std_val,
                        'Variance_A2': std_val ** 2,
                        'H2_L': h2_total,
                        'O2_L': o2_total
                    })
                
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_csv(os.path.join(folder_path, f'statistics_window_{self.window_index}.csv'), index=False)
                
                InfoBar.success(
                    title="Export Complete",
                    content=f"Saved 9 segment files + statistics to {os.path.basename(folder_path)}",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
            except Exception as e:
                InfoBar.error(
                    title="Export Error",
                    content=str(e),
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=5000
                )
    
    def __exportData(self):
        """Export processed data"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Export Folder", "")
        
        if folder_path:
            try:
                # Export each segment
                for i, df_filt in enumerate(self.dfs_filtered):
                    file_path = os.path.join(folder_path, f'segment_{i+1}_window_{self.window_index}.csv')
                    df_filt.to_csv(file_path, index=False)
                
                # Export statistics
                stats_data = []
                for i in range(9):
                    mean_val, std_val = self.stats[i]
                    h2_total = self.h2_data[i][1][-1] if len(self.h2_data[i][1]) > 0 else 0
                    o2_total = self.o2_data[i][1][-1] if len(self.o2_data[i][1]) > 0 else 0
                    stats_data.append({
                        'Segment': i + 1,
                        'Mean_A': mean_val,
                        'Std_A': std_val,
                        'Variance_A2': std_val ** 2,
                        'H2_L': h2_total,
                        'O2_L': o2_total
                    })
                
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_csv(os.path.join(folder_path, f'statistics_window_{self.window_index}.csv'), index=False)
                
                InfoBar.success(
                    title="Export Complete",
                    content=f"Data saved to {os.path.basename(folder_path)}",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
            except Exception as e:
                InfoBar.error(
                    title="Export Error",
                    content=str(e),
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=5000
                )
    
    def __exportCurrentTabChart(self):
        """Export the current tab's charts as PNG"""
        try:
            current_index = self.tab_widget.currentIndex()
            tab_names = ['signals', 'h2_production', 'o2_production', 'heatmaps', 'statistics']
            tab_name = tab_names[current_index] if current_index < len(tab_names) else 'chart'
            
            folder = QFileDialog.getExistingDirectory(
                self,
                "Select Folder to Save Charts",
                ""
            )
            if not folder:
                return
            
            timestamp = f"window{self.window_index}_{tab_name}"
            exported_count = 0
            
            if current_index == 0:  # Signals tab - 9 plots
                for i, plot_widget in enumerate(self.signal_plots):
                    exporter = ImageExporter(plot_widget.plotItem)
                    exporter.parameters()['width'] = int(plot_widget.width() * 3)
                    exporter.parameters()['height'] = int(plot_widget.height() * 3)
                    exporter.parameters()['antialias'] = True
                    filename = os.path.join(folder, f"signal_seg{i+1}_{timestamp}.png")
                    exporter.export(filename)
                    exported_count += 1
            elif current_index == 1:  # H2 tab
                for plot_widget, name in [(self.h2_plot, "h2_cumulative"), (self.h2_bar_plot, "h2_bar")]:
                    exporter = ImageExporter(plot_widget.plotItem)
                    exporter.parameters()['width'] = int(plot_widget.width() * 3)
                    exporter.parameters()['height'] = int(plot_widget.height() * 3)
                    exporter.parameters()['antialias'] = True
                    filename = os.path.join(folder, f"{name}_{timestamp}.png")
                    exporter.export(filename)
                    exported_count += 1
            elif current_index == 2:  # O2 tab
                for plot_widget, name in [(self.o2_plot, "o2_cumulative"), (self.o2_bar_plot, "o2_bar")]:
                    exporter = ImageExporter(plot_widget.plotItem)
                    exporter.parameters()['width'] = int(plot_widget.width() * 3)
                    exporter.parameters()['height'] = int(plot_widget.height() * 3)
                    exporter.parameters()['antialias'] = True
                    filename = os.path.join(folder, f"{name}_{timestamp}.png")
                    exporter.export(filename)
                    exported_count += 1
            elif current_index == 3:  # Heatmap tab
                for plot_widget, name in [(self.h2_heatmap, "heatmap_h2"), (self.o2_heatmap, "heatmap_o2"),
                                           (self.current_heatmap, "heatmap_current"), (self.var_heatmap, "heatmap_variance")]:
                    exporter = ImageExporter(plot_widget.plotItem)
                    exporter.parameters()['width'] = int(plot_widget.width() * 3)
                    exporter.parameters()['height'] = int(plot_widget.height() * 3)
                    exporter.parameters()['antialias'] = True
                    filename = os.path.join(folder, f"{name}_{timestamp}.png")
                    exporter.export(filename)
                    exported_count += 1
            elif current_index == 4:  # Statistics tab
                for plot_widget, name in [(self.mean_bar_plot, "mean_bar"), (self.var_bar_plot, "variance_bar")]:
                    exporter = ImageExporter(plot_widget.plotItem)
                    exporter.parameters()['width'] = int(plot_widget.width() * 3)
                    exporter.parameters()['height'] = int(plot_widget.height() * 3)
                    exporter.parameters()['antialias'] = True
                    filename = os.path.join(folder, f"{name}_{timestamp}.png")
                    exporter.export(filename)
                    exported_count += 1
            
            InfoBar.success(
                title="Export Complete",
                content=f"Saved {exported_count} charts to {os.path.basename(folder)}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
        except Exception as e:
            InfoBar.error(
                title="Export Error",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )
    
    def __exportAllCharts(self):
        """Export all charts from all tabs as PNG"""
        try:
            folder = QFileDialog.getExistingDirectory(
                self,
                "Select Folder to Save All Charts",
                ""
            )
            if not folder:
                return
            
            timestamp = f"window{self.window_index}"
            exported_count = 0
            
            # Signal plots (9)
            for i, plot_widget in enumerate(self.signal_plots):
                exporter = ImageExporter(plot_widget.plotItem)
                exporter.parameters()['width'] = int(plot_widget.width() * 3)
                exporter.parameters()['height'] = int(plot_widget.height() * 3)
                exporter.parameters()['antialias'] = True
                filename = os.path.join(folder, f"signal_seg{i+1}_{timestamp}.png")
                exporter.export(filename)
                exported_count += 1
            
            # H2 plots
            for plot_widget, name in [(self.h2_plot, "h2_cumulative"), (self.h2_bar_plot, "h2_bar")]:
                exporter = ImageExporter(plot_widget.plotItem)
                exporter.parameters()['width'] = int(plot_widget.width() * 3)
                exporter.parameters()['height'] = int(plot_widget.height() * 3)
                exporter.parameters()['antialias'] = True
                filename = os.path.join(folder, f"{name}_{timestamp}.png")
                exporter.export(filename)
                exported_count += 1
            
            # O2 plots
            for plot_widget, name in [(self.o2_plot, "o2_cumulative"), (self.o2_bar_plot, "o2_bar")]:
                exporter = ImageExporter(plot_widget.plotItem)
                exporter.parameters()['width'] = int(plot_widget.width() * 3)
                exporter.parameters()['height'] = int(plot_widget.height() * 3)
                exporter.parameters()['antialias'] = True
                filename = os.path.join(folder, f"{name}_{timestamp}.png")
                exporter.export(filename)
                exported_count += 1
            
            # Heatmaps
            for plot_widget, name in [(self.h2_heatmap, "heatmap_h2"), (self.o2_heatmap, "heatmap_o2"),
                                       (self.current_heatmap, "heatmap_current"), (self.var_heatmap, "heatmap_variance")]:
                exporter = ImageExporter(plot_widget.plotItem)
                exporter.parameters()['width'] = int(plot_widget.width() * 3)
                exporter.parameters()['height'] = int(plot_widget.height() * 3)
                exporter.parameters()['antialias'] = True
                filename = os.path.join(folder, f"{name}_{timestamp}.png")
                exporter.export(filename)
                exported_count += 1
            
            # Statistics bar charts
            for plot_widget, name in [(self.mean_bar_plot, "mean_bar"), (self.var_bar_plot, "variance_bar")]:
                exporter = ImageExporter(plot_widget.plotItem)
                exporter.parameters()['width'] = int(plot_widget.width() * 3)
                exporter.parameters()['height'] = int(plot_widget.height() * 3)
                exporter.parameters()['antialias'] = True
                filename = os.path.join(folder, f"{name}_{timestamp}.png")
                exporter.export(filename)
                exported_count += 1
            
            InfoBar.success(
                title="Export Complete",
                content=f"Saved {exported_count} charts to {os.path.basename(folder)}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
        except Exception as e:
            InfoBar.error(
                title="Export Error",
                content=str(e),
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )


class PreprocessingInterface(ScrollArea):
    """Data Preprocessing Interface"""
    
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('preprocessingInterface')
        
        self.dfs_raw = None  # List of raw DataFrames (9 segments)
        self.time_windows = []  # Time windows
        self.time_mask = []  # Time masks
        self.folder_path = None
        self.popup_windows = []  # Keep track of open popup windows
        
        self.view = QWidget(self)
        self.view.setObjectName('preprocessingView')
        self.setStyleSheet("""
            ScrollArea {
                background: transparent;
                border: none;
                border-top-left-radius: 10px;
            }
            #preprocessingView {
                background: transparent;
                border-top-left-radius: 10px;
            }
        """)
        self.vBoxLayout = QVBoxLayout(self.view)
        self.vBoxLayout.setSpacing(15)
        self.vBoxLayout.setContentsMargins(20, 20, 20, 20)
        
        self.__initWidget()
        
        self.setWidget(self.view)
        self.setWidgetResizable(True)
    
    def __initWidget(self):
        """Initialize widgets"""
        
        # === File Upload Section ===
        self.file_card = CardWidget(self.view)
        self.file_card.setStyleSheet("CardWidget { border: 1px solid #dcdcdc; border-radius: 6px; }")
        file_layout = QVBoxLayout(self.file_card)
        file_layout.setSpacing(12)
        
        file_header = StrongBodyLabel("1. Load Data")
        file_layout.addWidget(file_header)
        
        # Load button row
        load_row = QHBoxLayout()
        load_row.setSpacing(15)
        
        # Dropdown button with menu
        self.load_menu = RoundMenu(parent=self)
        self.load_menu.addAction(Action(FluentIcon.FOLDER, 'Load Folder', triggered=self._select_folder))
        self.load_menu.addAction(Action(FluentIcon.DOCUMENT, 'Load File', triggered=self._select_file))
        
        self.load_btn = PrimaryDropDownPushButton(FluentIcon.ADD, 'Load Data')
        self.load_btn.setMenu(self.load_menu)
        self.load_btn.setFixedWidth(160)
        load_row.addWidget(self.load_btn)
        
        # Status label
        self.file_label = BodyLabel("No data loaded")
        self.file_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        load_row.addWidget(self.file_label)
        
        load_row.addStretch()
        file_layout.addLayout(load_row)
        
        self.vBoxLayout.addWidget(self.file_card)
        
        # === Data Preview Section ===
        self.preview_card = CardWidget(self.view)
        self.preview_card.setStyleSheet("CardWidget { border: 1px solid #dcdcdc; border-radius: 6px; }")
        preview_layout = QVBoxLayout(self.preview_card)
        
        # Header row with controls
        preview_header_row = QHBoxLayout()
        preview_header_row.addWidget(StrongBodyLabel("2. Data Preview"))
        preview_header_row.addStretch()
        
        # View mode selector
        preview_header_row.addWidget(BodyLabel("View:"))
        self.preview_mode_combo = ComboBox()
        self.preview_mode_combo.addItems(["All Columns (Combined)", "Single Segment"])
        self.preview_mode_combo.setFixedWidth(250)
        self.preview_mode_combo.currentIndexChanged.connect(self._on_preview_mode_changed)
        preview_header_row.addWidget(self.preview_mode_combo)
        
        # Segment selector (hidden by default)
        self.segment_label = BodyLabel("Segment:")
        self.segment_combo = ComboBox()
        self.segment_combo.addItems([f"Segment {i+1}" for i in range(9)])
        self.segment_combo.setFixedWidth(120)
        self.segment_combo.currentIndexChanged.connect(self.update_preview)
        self.segment_label.setVisible(False)
        self.segment_combo.setVisible(False)
        preview_header_row.addWidget(self.segment_label)
        preview_header_row.addWidget(self.segment_combo)
        
        preview_layout.addLayout(preview_header_row)
        
        self.data_table = QTableWidget()
        self.data_table.setMaximumHeight(250)
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        preview_layout.addWidget(self.data_table)
        
        self.data_info_label = BodyLabel("Select a folder or file to see data preview")
        preview_layout.addWidget(self.data_info_label)
        
        self.vBoxLayout.addWidget(self.preview_card)
        
        # === Window Settings Section ===
        self.window_card = CardWidget(self.view)
        self.window_card.setStyleSheet("CardWidget { border: 1px solid #dcdcdc; border-radius: 6px; }")
        window_layout = QVBoxLayout(self.window_card)
        
        window_header = StrongBodyLabel("3. Window Settings")
        window_layout.addWidget(window_header)
        
        window_options_layout = QHBoxLayout()
        
        # Window Length
        col_win = QVBoxLayout()
        col_win.addWidget(BodyLabel("Window Length (s):"))
        self.window_length_spin = SpinBox()
        self.window_length_spin.setRange(1, 600)
        self.window_length_spin.setValue(60)  # Default value, updated when data is loaded
        col_win.addWidget(self.window_length_spin)
        window_options_layout.addLayout(col_win)
        
        # Overlap
        col_overlap = QVBoxLayout()
        col_overlap.addWidget(BodyLabel("Overlap (s):"))
        self.overlap_spin = SpinBox()
        self.overlap_spin.setRange(0, 300)
        self.overlap_spin.setValue(30)
        col_overlap.addWidget(self.overlap_spin)
        window_options_layout.addLayout(col_overlap)
        
        window_options_layout.addStretch()
        window_layout.addLayout(window_options_layout)
        
        # Apply Windows Button
        self.apply_windows_btn = PrimaryPushButton("Calculate Windows")
        self.apply_windows_btn.clicked.connect(self.calculate_windows)
        window_layout.addWidget(self.apply_windows_btn)
        
        self.vBoxLayout.addWidget(self.window_card)
        
        # === Window Selection & Visualization Section ===
        self.viz_card = CardWidget(self.view)
        self.viz_card.setStyleSheet("CardWidget { border: 1px solid #dcdcdc; border-radius: 6px; }")
        viz_layout = QVBoxLayout(self.viz_card)
        
        viz_header = StrongBodyLabel("4. Open Visualization Window")
        viz_layout.addWidget(viz_header)
        
        viz_info = BodyLabel("Select a window index and click 'Open Visualization' to see detailed analysis.\n"
                            "You can open multiple windows to compare different folders or window indices.")
        viz_layout.addWidget(viz_info)
        
        # Window Index Selection
        viz_ctrl_layout = QHBoxLayout()
        viz_ctrl_layout.addWidget(BodyLabel("Window Index:"))
        self.window_index_spin = SpinBox()
        self.window_index_spin.setRange(0, 0)
        self.window_index_spin.setValue(0)
        viz_ctrl_layout.addWidget(self.window_index_spin)
        
        self.window_info_label = BodyLabel("No windows available - Calculate windows first")
        viz_ctrl_layout.addWidget(self.window_info_label)
        
        viz_ctrl_layout.addStretch()
        viz_layout.addLayout(viz_ctrl_layout)
        
        # Open Visualization Button
        btn_layout = QHBoxLayout()
        self.open_viz_btn = PrimaryPushButton("Open Visualization Window")
        self.open_viz_btn.clicked.connect(self.open_visualization_popup)
        btn_layout.addWidget(self.open_viz_btn)
        
        btn_layout.addStretch()
        viz_layout.addLayout(btn_layout)
        
        self.vBoxLayout.addWidget(self.viz_card)
        
        self.vBoxLayout.addStretch()
    
    def _select_folder(self):
        """Open folder dialog to select folder with 9 CSV files"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder with 9 CSV Files", ""
        )
        if folder_path:
            try:
                self._load_folder(folder_path)
            except Exception as e:
                InfoBar.error(
                    title="Error",
                    content=f"Failed to load folder: {str(e)}",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=5000
                )
    
    def _select_file(self):
        """Open file dialog to select single CSV file with 11 columns"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File (11 columns)", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            try:
                df = pd.read_csv(file_path)
                self._load_single_file(file_path, df)
            except Exception as e:
                InfoBar.error(
                    title="Error",
                    content=f"Failed to load file: {str(e)}",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=5000
                )
    
    def _load_single_file(self, file_path, df):
        """Load single CSV file with 11 columns"""
        # Expected format: timestamp (col 0), i1-i9 (cols 1-9), voltage (col 10)
        self.dfs_raw = []
        for i in range(9):
            df_segment = pd.DataFrame({
                'time': df.iloc[:, 0],
                'current': df.iloc[:, i + 1],
                'voltage': df.iloc[:, 10] if len(df.columns) > 10 else 0.0
            })
            self.dfs_raw.append(df_segment)
        
        self.folder_path = os.path.dirname(file_path)
        self.file_label.setText(f"Loaded: {os.path.basename(file_path)} ({len(df)} rows, 11 cols)")
        self.file_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        self.update_preview()
        self._reset_windows()
        
        InfoBar.success(
            title="File Loaded",
            content=f"Loaded {len(df)} samples from single file",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000
        )
    
    def _load_folder(self, folder_path):
        """Load folder with 9 CSV files"""
        self.dfs_raw = load_signals_from_folder(folder_path, n_segments=9)
        self.folder_path = folder_path
        self.file_label.setText(f"Loaded: {os.path.basename(folder_path)}/ (9 files)")
        self.file_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        self.update_preview()
        self._reset_windows()
        
        InfoBar.success(
            title="Folder Loaded",
            content=f"Loaded 9 CSV files with {len(self.dfs_raw[0])} samples each",
            parent=self,
            position=InfoBarPosition.TOP,
            duration=3000
        )
    
    def _reset_windows(self):
        """Reset window settings after loading new data"""
        self.time_windows = []
        self.time_mask = []
        self.window_index_spin.setRange(0, 0)
        self.window_info_label.setText("No windows available - Calculate windows first")
        
        # Update window length spinbox with total duration of loaded data
        if self.dfs_raw and len(self.dfs_raw) > 0:
            df_first = self.dfs_raw[0]
            if 'time' in df_first.columns and len(df_first) > 0:
                total_duration = int(df_first['time'].max() - df_first['time'].min())
                if total_duration > 0:
                    self.window_length_spin.setValue(min(total_duration, 600))
    
    def upload_folder(self):
        """Select folder containing 9 CSV files (Option A)"""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder with 9 CSV Files", ""
        )
        
        if folder_path:
            try:
                self.dfs_raw = load_signals_from_folder(folder_path, n_segments=9)
                self.folder_path = folder_path
                self.file_label.setText(f"Loaded folder: {os.path.basename(folder_path)} (9 segments)")
                self.file_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                self.update_preview()
                
                # Reset windows
                self.time_windows = []
                self.time_mask = []
                self.window_index_spin.setRange(0, 0)
                self.window_info_label.setText("No windows available - Calculate windows first")
                
                InfoBar.success(
                    title="Folder Loaded",
                    content=f"Loaded 9 CSV files with {len(self.dfs_raw[0])} samples each",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
            except Exception as e:
                InfoBar.error(
                    title="Error",
                    content=f"Failed to load folder: {str(e)}",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=5000
                )
    
    def upload_single_file(self):
        """Select single CSV file with 11 columns (Option B: timestamp, 9 currents, voltage)"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File (11 columns)", "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                # Load single file and split into 9 segments
                df = pd.read_csv(file_path, header=None)
                
                # Validate columns
                if len(df.columns) < 11:
                    raise ValueError(f"File has {len(df.columns)} columns, expected at least 11")
                
                # Expected format: timestamp (col 0), i1-i9 (cols 1-9), voltage (col 10)
                # Create 9 separate DataFrames for each current sensor
                self.dfs_raw = []
                for i in range(9):
                    df_segment = pd.DataFrame({
                        'time': df.iloc[:, 0],  # timestamp
                        'current': df.iloc[:, i + 1],  # current i1-i9
                        'voltage': df.iloc[:, 10]  # voltage
                    })
                    self.dfs_raw.append(df_segment)
                
                self.folder_path = os.path.dirname(file_path)
                self.file_label.setText(f"Loaded file: {os.path.basename(file_path)} (11 cols -> 9 segments)")
                self.file_label.setStyleSheet("color: #27ae60; font-weight: bold;")
                self.update_preview()
                
                # Reset windows
                self.time_windows = []
                self.time_mask = []
                self.window_index_spin.setRange(0, 0)
                self.window_info_label.setText("No windows available - Calculate windows first")
                
                InfoBar.success(
                    title="File Loaded",
                    content=f"Loaded {len(df)} samples from {os.path.basename(file_path)}",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
            except Exception as e:
                InfoBar.error(
                    title="Error",
                    content=f"Failed to load file: {str(e)}",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=5000
                )
    
    def _on_preview_mode_changed(self, index):
        """Handle preview mode change"""
        is_single_segment = (index == 1)
        self.segment_label.setVisible(is_single_segment)
        self.segment_combo.setVisible(is_single_segment)
        self.update_preview()
    
    def update_preview(self):
        """Update data preview table based on selected view mode"""
        if self.dfs_raw is None or len(self.dfs_raw) == 0:
            return
        
        view_mode = self.preview_mode_combo.currentIndex()
        
        if view_mode == 0:
            # All Columns (Combined) - show all 9 currents + time + voltage in one view
            self._show_combined_preview()
        else:
            # Single Segment - show selected segment
            segment_idx = self.segment_combo.currentIndex()
            self._show_segment_preview(segment_idx)
    
    def _show_combined_preview(self):
        """Show combined preview with all columns"""
        if self.dfs_raw is None or len(self.dfs_raw) == 0:
            return
        
        # Build combined dataframe
        df_first = self.dfs_raw[0]
        n_rows = min(10, len(df_first))
        
        # Create columns: time, i1-i9, voltage
        columns = ['time'] + [f'i{i+1}' for i in range(9)] + ['voltage']
        
        combined_data = []
        for idx in range(n_rows):
            row = [self.dfs_raw[0].iloc[idx]['time']]
            for i in range(9):
                row.append(self.dfs_raw[i].iloc[idx]['current'])
            if 'voltage' in self.dfs_raw[0].columns:
                row.append(self.dfs_raw[0].iloc[idx]['voltage'])
            else:
                row.append(0.0)
            combined_data.append(row)
        
        self.data_table.setRowCount(n_rows)
        self.data_table.setColumnCount(len(columns))
        self.data_table.setHorizontalHeaderLabels(columns)
        
        for i, row in enumerate(combined_data):
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(round(value, 6) if isinstance(value, (int, float)) else value))
                self.data_table.setItem(i, j, item)
        
        # Update info label
        total_samples = len(self.dfs_raw[0])
        self.data_info_label.setText(
            f"Combined view: 9 segments | {total_samples} samples | 11 columns (time, i1-i9, voltage)"
        )
    
    def _show_segment_preview(self, segment_idx):
        """Show preview for a single segment"""
        if self.dfs_raw is None or segment_idx >= len(self.dfs_raw):
            return
        
        df_preview = self.dfs_raw[segment_idx]
        preview = df_preview.head(10)
        
        self.data_table.setRowCount(len(preview))
        self.data_table.setColumnCount(len(preview.columns))
        self.data_table.setHorizontalHeaderLabels(preview.columns.tolist())
        
        for i, (idx, row) in enumerate(preview.iterrows()):
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(round(value, 6) if isinstance(value, float) else value))
                self.data_table.setItem(i, j, item)
        
        # Update info label
        self.data_info_label.setText(
            f"Segment {segment_idx + 1}: {len(df_preview)} samples | "
            f"Columns: {', '.join(df_preview.columns.tolist())}"
        )

    def calculate_windows(self):
        """Calculate time windows based on settings"""
        if self.dfs_raw is None:
            InfoBar.warning(
                title="No Data",
                content="Please select a folder first",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return
        
        try:
            # Get parameters
            window_duration = self.window_length_spin.value()
            overlap = self.overlap_spin.value()
            
            # Validate overlap
            if overlap >= window_duration:
                InfoBar.warning(
                    title="Invalid Parameters",
                    content="Overlap must be smaller than window length",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
                return
            
            # Get time windows from first segment (assuming all have same timing)
            df = self.dfs_raw[0]
            self.time_windows, self.time_mask = get_temporal_windows(df, window_duration, overlap)
            
            if len(self.time_windows) == 0:
                InfoBar.warning(
                    title="No Windows",
                    content="No time windows could be created with current settings",
                    parent=self,
                    position=InfoBarPosition.TOP,
                    duration=3000
                )
                return
            
            # Update window index spinner
            self.window_index_spin.setRange(0, len(self.time_windows) - 1)
            self.window_index_spin.setValue(0)
            self.window_info_label.setText(f"Total windows: {len(self.time_windows)}")
            
            InfoBar.success(
                title="Windows Calculated",
                content=f"Created {len(self.time_windows)} windows",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            
        except Exception as e:
            InfoBar.error(
                title="Error",
                content=f"Window calculation failed: {str(e)}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )
    
    def open_visualization_popup(self):
        """Open visualization popup window for current folder and window index"""
        if self.dfs_raw is None:
            InfoBar.warning(
                title="No Data",
                content="Please select a folder first",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return
        
        if len(self.time_windows) == 0:
            InfoBar.warning(
                title="No Windows",
                content="Please calculate windows first",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=3000
            )
            return
        
        try:
            window_index = self.window_index_spin.value()
            time_mask = self.time_mask[window_index]
            
            # Create and show popup window
            popup = VisualizationPopup(
                folder_path=self.folder_path,
                dfs_raw=self.dfs_raw,
                time_mask=time_mask,
                window_index=window_index,
                parent=None  # None so it can be an independent window
            )
            popup.show()
            
            # Keep reference to prevent garbage collection
            self.popup_windows.append(popup)
            
            InfoBar.success(
                title="Visualization Opened",
                content=f"Opened window {window_index} for {os.path.basename(self.folder_path)}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=2000
            )
            
        except Exception as e:
            InfoBar.error(
                title="Error",
                content=f"Failed to open visualization: {str(e)}",
                parent=self,
                position=InfoBarPosition.TOP,
                duration=5000
            )