# basis_monitor_pyqt.py
import sys
import time
import datetime
import pyautogui
import pandas as pd
import warnings
from cryptography.utils import CryptographyDeprecationWarning
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
import paramiko
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QGridLayout, QMessageBox, QFileDialog, QFrame,
    QStatusBar, QToolBar, QAction, QMenuBar, QMenu, QTextEdit,
    QCheckBox
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush, QIcon, QPixmap
import threading
import os
import ftplib
from io import BytesIO


class SftpManager(object):
    host = '168.yibeiinv.com'
    port = 39866
    user = 'trading'
    passwd = 'Js123456!Yibei3618!'
    
    @classmethod
    def load(cls, csvfile, type_dict={'代码': str}, cols_list=None):
        csvfile = csvfile.replace("\\", "/")
        csvfile = csvfile.replace("//", "/")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(cls.host, cls.port, cls.user, cls.passwd)
        data = None
        with client.open_sftp() as sftp:
            try:
                remote_file = sftp.open(csvfile, 'r')
                if cols_list is None:
                    if type_dict is None:
                        data = pd.read_csv(remote_file)
                    else:
                        data = pd.read_csv(remote_file, dtype=type_dict)
                else:
                    if type_dict is None:
                        data = pd.read_csv(remote_file, usecols=cols_list)
                    else:
                        data = pd.read_csv(remote_file, dtype=type_dict, usecols=cols_list)
            except Exception as e:
                print(f"SFTP加载失败: {e}")
        client.close()
        return data
    
    @classmethod
    def load_from_sftp(cls, sftp, csvfile, type_dict=None):
        csvfile = csvfile.replace("\\", "/").replace("//", "/")
        try:
            remote_file = sftp.open(csvfile, 'r')
            if type_dict:
                return pd.read_csv(remote_file, dtype=type_dict)
            else:
                return pd.read_csv(remote_file)
        except Exception as e:
            print(f"SFTP加载失败 {csvfile}: {e}")
            return None
    
    @classmethod
    def open_connection(cls):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(cls.host, cls.port, cls.user, cls.passwd)
        return client


class WorkdayManager(object):
    FTP_HOST = '168.yibeiinv.com'
    FTP_PORT = 59100
    FTP_USER = 'Scripts_Only'
    FTP_PASS = 'only_186447'
    WORKDAYS_PATH = '/common_config/workdays.cfg'

    _workdays = None

    @classmethod
    def load_workdays(cls):
        if cls._workdays is not None:
            return cls._workdays
        connect_time = 0
        while connect_time <= 3:
            connect_time += 1
            try:
                ftp = ftplib.FTP()
                ftp.encoding = 'utf-8'
                ftp.connect(host=cls.FTP_HOST, port=cls.FTP_PORT, timeout=10)
                ftp.login(user=cls.FTP_USER, passwd=cls.FTP_PASS)
                data = []
                def handle_binary(more_data):
                    data.append(more_data)
                ftp.retrbinary("RETR " + cls.WORKDAYS_PATH, callback=handle_binary)
                ftp.quit()
                content = b''.join(data).decode('utf-8')
                workday_strs = content.split('\r\n')
                cls._workdays = set()
                for s in workday_strs:
                    s = s.strip()
                    if len(s) == 8 and s.isdigit():
                        try:
                            d = datetime.datetime.strptime(s, '%Y%m%d').date()
                            cls._workdays.add(d)
                        except ValueError:
                            pass
                break
            except Exception as e:
                time.sleep(1)
        if cls._workdays is None:
            cls._workdays = set()
        return cls._workdays

    @classmethod
    def get_workdays_count_in_year(cls, year):
        """获取指定年份的交易日数量"""
        if cls._workdays is None:
            cls.load_workdays()
        count = 0
        for d in cls._workdays:
            if d.year == year:
                count += 1
        return count

    @classmethod
    def count_workdays_between(cls, start_date, end_date):
        if cls._workdays is None:
            cls.load_workdays()
        count = 0
        current = start_date
        while current <= end_date:
            if current in cls._workdays:
                count += 1
            current += datetime.timedelta(days=1)
        return count


class DataFetcherThread(QThread):
    data_fetched = pyqtSignal(dict, dict, list, dict)
    error_occurred = pyqtSignal(str)
    log_message = pyqtSignal(str)
    
    SERIES_FILTER = ['IF', 'IC', 'IM', 'IH']
    SERIES_NAME = {'IF': '沪深300', 'IH': '上证50', 'IC': '中证500', 'IM': '中证1000'}
    INDEX_CODE_MAP = {'IF': 'sh000300', 'IH': 'sh000016', 'IC': 'sz399905', 'IM': 'sz399852'}
    
    def __init__(self):
        super().__init__()
        self.running = True
    
    def run(self):
        futures_data = {}
        spot_prices = {}
        contract_codes = []
        contract_dates = {}
        
        try:
            # 获取正确的交易日期（盘前回退到前一交易日）
            today = self._get_trade_date()
            ctp_base = f'/data/ctp_data/future/{today}'
            self.log_message.emit(f"正在通过SFTP获取 {today} 数据...")
            
            client = SftpManager.open_connection()
            with client.open_sftp() as sftp:
                # 1. 读取 name_map.csv 获取合约列表
                contract_codes = self._fetch_contract_list(sftp, ctp_base, futures_data, today)
                
                # 2. 读取 future_code_list.csv 获取合约日期
                contract_dates = self._fetch_contract_dates(sftp, ctp_base)
                
                # 3. 读取指数现货价格
                spot_prices = self._fetch_spot_prices(sftp, today)
            
            client.close()
            self.data_fetched.emit(futures_data, spot_prices, contract_codes, contract_dates)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
            self.data_fetched.emit(futures_data, spot_prices, contract_codes, contract_dates)

    def _get_trade_date(self):
        """获取当前应该使用的交易日期
        
        交易时间：
        - 上午：9:30 - 11:30
        - 下午：13:00 - 15:00
        
        非交易时间处理：
        - 9:30之前：使用前一个交易日的数据
        - 15:00之后：使用当天收盘数据（文件已生成）
        - 周末：使用上周五的数据
        """
        now = datetime.datetime.now()
        current_time = now.time()
        today = now.date()
        
        morning_start = datetime.time(9, 30)
        afternoon_end = datetime.time(15, 0)
        
        # 检查是否是交易日（周一到周五）
        is_trading_day = today.weekday() < 5
        
        if not is_trading_day:
            # 周末，使用周五的数据
            days_back = today.weekday() - 4
            trade_date = today - datetime.timedelta(days=days_back)
            self.log_message.emit(f"📅 周末，使用周五数据: {trade_date.strftime('%Y%m%d')}")
            return trade_date.strftime('%Y%m%d')
        
        # 9:30之前使用前一交易日
        if current_time < morning_start:
            trade_date = today - datetime.timedelta(days=1)
            # 如果前一天是周末，继续往前推
            while trade_date.weekday() >= 5:
                trade_date -= datetime.timedelta(days=1)
            self.log_message.emit(f"📅 盘前(9:30前)，使用前一交易日: {trade_date.strftime('%Y%m%d')}")
            return trade_date.strftime('%Y%m%d')
        
        # 15:00之后使用当天收盘数据
        if current_time >= afternoon_end:
            self.log_message.emit(f"📅 收盘后(15:00后)，使用当天数据: {today.strftime('%Y%m%d')}")
        
        # 交易时间内（9:30-15:00）使用当天数据
        return today.strftime('%Y%m%d')
    
    def _fetch_contract_list(self, sftp, base_path, futures_data, today):
        contract_codes = []
        try:
            self.log_message.emit("正在读取合约映射(name_map.csv)...")
            df = SftpManager.load_from_sftp(sftp, f'{base_path}/name_map.csv', type_dict={"instrument_id": str})
            
            if df is None or df.empty:
                self.log_message.emit("⚠️ name_map.csv 为空或不存在")
                return contract_codes
            
            self.log_message.emit(f"name_map.csv: {len(df)} 条记录")
            
            id_col = self._detect_col(df.columns, ['instrument_id', '代码', 'code', '合约代码'])
            if id_col is None:
                self.log_message.emit(f"❌ name_map列名检测失败, 可用列: {list(df.columns)}")
                return contract_codes
            
            pattern = '|'.join(self.SERIES_FILTER)
            mask = df[id_col].str.contains(rf'^({pattern})\d+', regex=True, na=False)
            df_filtered = df[mask].copy()
            
            self.log_message.emit(f"筛选出 {len(df_filtered)} 个股指期货合约")
            
            for _, row in df_filtered.iterrows():
                instrument_id = str(row[id_col]).strip()
                code = instrument_id.split('.')[0]
                contract_codes.append(code)
            
            self.log_message.emit(f"合约列表: {contract_codes}")
        except Exception as e:
            self.log_message.emit(f"❌ 读取name_map失败: {e}")
        
        # 从旧路径real_tik获取期货价格（tik/目录没有IF/IH/IC/IM文件）
        if contract_codes:
            try:
                self.log_message.emit("正在从real_tik获取期货价格...")
                df_fut = SftpManager.load_from_sftp(sftp, f'/data/Std_Data/idata/StdData/real_tik/{today}_fut.csv', type_dict={"代码": str})
                
                if df_fut is not None and not df_fut.empty:
                    self.log_message.emit(f"期货行情: {len(df_fut)} 条, 列: {list(df_fut.columns)[:8]}")
                    
                    code_col = self._detect_col(df_fut.columns, ['代码', 'code', 'Code', '合约代码', '合约', 'symbol'])
                    price_col = self._detect_col(df_fut.columns, ['最新价', '现价', '收盘价', 'close', 'price', '收盘', '最新', '当前价'])
                    
                    if code_col and price_col:
                        self.log_message.emit(f"代码列: {code_col}, 价格列: {price_col}")
                        
                        for code in contract_codes:
                            code_variants = [f"{code}.CFFE", code, code.lower(), f"{code}.CFE", f"{code}.CFFEX"]
                            found = False
                            for variant in code_variants:
                                rows = df_fut[df_fut[code_col] == variant]
                                if not rows.empty:
                                    price = float(rows[price_col].iloc[0])
                                    if price > 0:
                                        futures_data[code] = price
                                        self.log_message.emit(f"✅ {code}: {price}")
                                    found = True
                                    break
                            if not found:
                                self.log_message.emit(f"⚠️ {code}: 未找到匹配")
                    else:
                        self.log_message.emit(f"❌ 列名检测失败: code={code_col}, price={price_col}")
                else:
                    self.log_message.emit("⚠️ 未获取到期货行情数据")
            except Exception as e:
                self.log_message.emit(f"❌ 获取期货价格失败: {e}")
            
            self.log_message.emit(f"期货: 成功获取 {len(futures_data)}/{len(contract_codes)} 个合约")
        
        return contract_codes
    
    def _fetch_contract_dates(self, sftp, base_path):
        contract_dates = {}
        try:
            self.log_message.emit("正在读取合约日期(future_code_list.csv)...")
            df = SftpManager.load_from_sftp(sftp, f'{base_path}/future_code_list.csv', type_dict={"instrument_id": str})
            
            if df is None or df.empty:
                self.log_message.emit("⚠️ future_code_list.csv 为空或不存在")
                return contract_dates
            
            self.log_message.emit(f"future_code_list.csv: {len(df)} 条记录, 列: {list(df.columns)}")
            
            id_col = self._detect_col(df.columns, ['instrument_id', '代码', 'code', '合约代码'])
            open_col = self._detect_col(df.columns, ['open_date', '上市日', '上市日期', 'list_date'])
            expire_col = self._detect_col(df.columns, ['expire_date', '最后交易日', '到期日', 'expire_date', 'last_trade_date'])
            
            if id_col is None or open_col is None or expire_col is None:
                self.log_message.emit(f"❌ 日期列检测失败: id={id_col}, open={open_col}, expire={expire_col}")
                return contract_dates
            
            pattern = '|'.join(self.SERIES_FILTER)
            mask = df[id_col].str.contains(rf'^({pattern})\d+', regex=True, na=False)
            df_filtered = df[mask]
            
            for _, row in df_filtered.iterrows():
                instrument_id = str(row[id_col]).strip()
                code = instrument_id.split('.')[0]
                contract_month = code[-4:]
                
                if contract_month not in contract_dates:
                    try:
                        open_date = str(int(float(str(row[open_col]))))
                        expire_date = str(int(float(str(row[expire_col]))))
                        contract_dates[contract_month] = {
                            'listing_date': self._date_to_excel(open_date),
                            'expiry_date': self._date_to_excel(expire_date)
                        }
                    except Exception as e:
                        self.log_message.emit(f"⚠️ {code} 日期解析失败: {e}")
            
            self.log_message.emit(f"获取到 {len(contract_dates)} 个合约日期配置")
            for month, dates in contract_dates.items():
                self.log_message.emit(f"  {month}: 上市={dates['listing_date']}, 到期={dates['expiry_date']}")
        except Exception as e:
            self.log_message.emit(f"❌ 读取future_code_list失败: {e}")
        
        return contract_dates
    
    def _fetch_spot_prices(self, sftp, today):
        spot_prices = {}
        try:
            self.log_message.emit("正在获取指数行情数据...")
            df = SftpManager.load_from_sftp(sftp, f'/data/Std_Data/idata/StdData/real_tik/{today}_idx.csv', type_dict={"代码": str})
            
            if df is None or df.empty:
                self.log_message.emit("⚠️ 指数行情数据为空")
                return spot_prices
            
            code_col = self._detect_col(df.columns, ['代码', 'code', 'Code'])
            price_col = self._detect_col(df.columns, ['最新价', '现价', '收盘价', 'close', 'price'])
            
            if code_col is None or price_col is None:
                self.log_message.emit(f"❌ 指数列名检测失败: code={code_col}, price={price_col}")
                return spot_prices
            
            for series, idx_code in self.INDEX_CODE_MAP.items():
                rows = df[df[code_col] == idx_code]
                if not rows.empty:
                    spot_prices[series] = float(rows[price_col].iloc[0])
                    self.log_message.emit(f"✅ {series}指数: {spot_prices[series]}")
        except Exception as e:
            self.log_message.emit(f"❌ 获取指数数据失败: {e}")
        
        return spot_prices
    
    def _detect_col(self, columns, candidates):
        for col_name in candidates:
            if col_name in columns:
                return col_name
        return None
    
    def _detect_price_col(self, columns):
        for col_name in ['close', '收盘价', '最新价', '现价', 'Close', 'price', 'last_price', '当前价']:
            if col_name in columns:
                return col_name
        return None
    
    def _date_to_excel(self, date_str):
        date_str = str(date_str).split('.')[0]
        d = datetime.datetime.strptime(date_str, '%Y%m%d')
        return (d.date() - datetime.date(1899, 12, 30)).days
    
    def stop(self):
        self.running = False


class ExcelUpdaterThread(QThread):
    """Excel更新线程"""
    update_finished = pyqtSignal(bool, str)
    log_message = pyqtSignal(str)
    
    def __init__(self, data, excel_path):
        super().__init__()
        self.data = data
        self.excel_path = excel_path
        self.running = True
        
    def run(self):
        try:
            self.log_message.emit(f"正在更新Excel文件: {self.excel_path}")
            
            # 使用openpyxl引擎写入Excel
            with pd.ExcelWriter(self.excel_path, engine='openpyxl', mode='w') as writer:
                self.data.to_excel(writer, sheet_name='基差监控', index=False)
                
                # 获取工作簿和工作表
                workbook = writer.book
                worksheet = writer.sheets['基差监控']
                
                # 设置列宽
                column_widths = {
                    'A': 12, 'B': 15, 'C': 12, 'D': 12, 'E': 12,
                    'F': 12, 'G': 15, 'H': 12, 'I': 12, 'J': 15, 'K': 15, 'L': 15
                }
                
                for col, width in column_widths.items():
                    worksheet.column_dimensions[col].width = width
            
            self.log_message.emit(f"✅ Excel更新成功: {self.excel_path}")
            self.update_finished.emit(True, self.excel_path)
            
        except Exception as e:
            self.log_message.emit(f"❌ Excel更新失败: {str(e)}")
            self.update_finished.emit(False, str(e))
    
    def stop(self):
        self.running = False


class BasisMonitorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("股指期货基差实时监控系统")
        self.setGeometry(100, 100, 1600, 1000)
        
        # 数据源配置
        self.update_interval = 3000
        
        # Excel配置
        self.excel_path = os.path.join(os.path.dirname(__file__), "基差监控实时数据.xlsx")
        self.auto_save_excel = True
        
        # 合约日期配置（动态从SFTP获取）
        self.contract_dates = {}
        
        # 初始化数据
        self.init_data()
        
        # 先创建界面（确保log_text等组件先创建）
        self.create_menu()
        self.create_toolbar()
        self.create_main_layout()
        self.create_statusbar()
        
        # 测试SFTP连接
        self.test_sftp_connection()

        # 加载交易日历
        self.load_workdays()

        # 定时器 - 数据更新
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        
        # 定时器 - 检查收盘时间（15:00）
        self.market_close_timer = QTimer()
        self.market_close_timer.timeout.connect(self.check_market_close)
        self.market_close_timer.start(60000)  # 每分钟检查一次
        self.screenshot_taken_today = False  # 标记今天是否已截图
        
        # 启动后自动开始监控
        self.log_message("系统初始化完成，自动启动实时监控...")
        self.start_monitoring()
    
    SERIES_NAME = {'IF': '沪深300', 'IH': '上证50', 'IC': '中证500', 'IM': '中证1000'}
    
    def init_data(self, contract_codes=None):
        """初始化监控数据 - 合约列表动态获取"""
        if contract_codes is None:
            contract_codes = []
        
        self.contract_codes = contract_codes
        n = len(contract_codes)
        
        names = []
        for code in contract_codes:
            series = code[:2]
            month = code[2:]
            name = f"{self.SERIES_NAME.get(series, series)} {month}"
            names.append(name)
        
        # 列顺序：代码、名称、现价、现货价、价差差值、合约总天数、剩余交易日、基差(期-现)、年化(交易日)、年化(自然日)
        df = pd.DataFrame({
            '代码': contract_codes,
            '名称': names,
            '现价': [0.0]*n,
            '现货价': [0.0]*n,
            '价差差值': [0.0]*n,
            '合约总天数': [0]*n,
            '剩余交易日': [0]*n,
            '基差(期-现)': [0.0]*n,
            '年化(交易日)': [0.0]*n,
            '年化(自然日)': [0.0]*n
        })
        
        # 按照 IF、IC、IM、IH 的顺序排序
        series_order = {'IF': 0, 'IC': 1, 'IM': 2, 'IH': 3}
        df['代码'] = df['代码'].astype(str)
        df['series_order'] = df['代码'].str[:2].map(series_order)
        df['month'] = df['代码'].str[2:]
        df = df.sort_values(['series_order', 'month']).drop(['series_order', 'month'], axis=1).reset_index(drop=True)
        
        self.data = df
        
        self.spot_prices = {'IF': 0, 'IH': 0, 'IC': 0, 'IM': 0}
    
    def test_sftp_connection(self):
        """测试SFTP连接"""
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(SftpManager.host, SftpManager.port, SftpManager.user, SftpManager.passwd, timeout=5)
            client.close()
            self.log_message("✅ SFTP连接成功")
        except Exception as e:
            self.log_message(f"❌ SFTP连接失败: {str(e)}")
            QMessageBox.warning(self, "警告", f"SFTP连接失败: {str(e)}")

    def load_workdays(self):
        """加载交易日历"""
        try:
            workdays = WorkdayManager.load_workdays()
            self.log_message(f"✅ 交易日历加载成功: {len(workdays)} 个交易日")
        except Exception as e:
            self.log_message(f"⚠️ 交易日历加载失败: {str(e)}，将使用自然日近似计算")
    
    def create_menu(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        start_action = QAction('开始监控', self)
        start_action.setShortcut('Ctrl+R')
        start_action.triggered.connect(self.start_monitoring)
        file_menu.addAction(start_action)
        
        stop_action = QAction('停止监控', self)
        stop_action.setShortcut('Ctrl+T')
        stop_action.triggered.connect(self.stop_monitoring)
        file_menu.addAction(stop_action)
        
        file_menu.addSeparator()
        
        export_action = QAction('导出Excel', self)
        export_action.setShortcut('Ctrl+E')
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        screenshot_action = QAction('日终截图', self)
        screenshot_action.setShortcut('Ctrl+S')
        screenshot_action.triggered.connect(lambda: self.take_screenshot(auto=False))
        file_menu.addAction(screenshot_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu('设置')
        
        interval_action = QAction('更新频率', self)
        interval_action.triggered.connect(self.set_interval_dialog)
        settings_menu.addAction(interval_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # 开始/停止按钮
        self.start_btn = QPushButton('▶️ 开始监控')
        self.start_btn.clicked.connect(self.start_monitoring)
        toolbar.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton('⏹️ 停止监控')
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)
        toolbar.addWidget(self.stop_btn)
        
        toolbar.addSeparator()
        
        refresh_btn = QPushButton('🔄 手动刷新')
        refresh_btn.clicked.connect(self.update_data)
        toolbar.addWidget(refresh_btn)
        
        toolbar.addSeparator()
        
        screenshot_btn = QPushButton('📷 日终截图')
        screenshot_btn.clicked.connect(lambda: self.take_screenshot(auto=False))
        toolbar.addWidget(screenshot_btn)
        
        toolbar.addSeparator()
        
        export_btn = QPushButton('📊 导出Excel')
        export_btn.clicked.connect(self.export_data)
        toolbar.addWidget(export_btn)
        
        toolbar.addSeparator()
        
        # Excel自动保存选项
        self.auto_save_checkbox = QCheckBox("自动保存Excel")
        self.auto_save_checkbox.setChecked(True)
        toolbar.addWidget(self.auto_save_checkbox)
    
    def create_main_layout(self):
        """创建主布局"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)
        
        # 顶部信息面板 - 紧凑横条
        info_bar = self.create_info_panel()
        main_layout.addWidget(info_bar)
        
        # 中间区域 - 数据表格
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)
        self.table = self.create_data_table()
        table_layout.addWidget(self.table)
        main_layout.addWidget(table_widget, 1)
        
        # 底部统计面板 - 紧凑
        stats_panel = self.create_stats_panel()
        main_layout.addWidget(stats_panel)
    
    def create_info_panel(self):
        """创建顶部信息面板 - 紧凑横条"""
        bar = QFrame()
        bar.setFrameShape(QFrame.StyledPanel)
        bar.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 4px;
                padding: 2px 8px;
            }
            QLabel {
                color: #ecf0f1;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 3, 10, 3)
        layout.setSpacing(30)
        
        self.source_label = QLabel("📡 SFTP实时行情")
        layout.addWidget(self.source_label)
        
        layout.addWidget(self._sep())
        
        self.interval_label = QLabel(f"⏱️ {self.update_interval//1000}秒")
        layout.addWidget(self.interval_label)
        
        layout.addWidget(self._sep())
        
        self.time_label = QLabel("🕐 --")
        layout.addWidget(self.time_label)
        
        layout.addWidget(self._sep())
        
        contract_label = QLabel(f"📈 {len(self.contract_codes)}个合约")
        layout.addWidget(contract_label)
        
        layout.addWidget(self._sep())
        
        self.status_label = QLabel("🔴 已停止")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        return bar
    
    def _sep(self):
        """分隔符"""
        sep = QLabel("|")
        sep.setStyleSheet("color: #7f8c8d; font-size: 14px;")
        return sep
    
    def create_data_table(self):
        """创建数据表格 - 专业级展示"""
        table = QTableWidget()
        table.setColumnCount(10)
        table.setRowCount(len(self.data))

        headers = ['代码', '名称', '现价', '现货价', '价差差值', '合约总天数',
                   '剩余交易日', '基差(期-现)', '年化(交易日)', '年化(自然日)']
        table.setHorizontalHeaderLabels(headers)
        
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        table.setColumnWidth(0, 80)
        table.setColumnWidth(1, 120)
        
        table.setAlternatingRowColors(True)
        table.setShowGrid(True)
        table.verticalHeader().setVisible(True)
        table.verticalHeader().setDefaultSectionSize(28)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        
        table.setStyleSheet("""
            QTableWidget {
                font-size: 12px;
                gridline-color: #d0d0d0;
                alternate-background-color: #f5f8fc;
                selection-background-color: #4a90d9;
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #2c5f8a;
                color: white;
                padding: 6px 4px;
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #1a4a6e;
            }
            QTableWidget::item {
                padding: 4px 6px;
            }
        """)
        
        for i, row in self.data.iterrows():
            for j, col in enumerate(headers):
                item = QTableWidgetItem(str(row[col]))
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(i, j, item)
        
        return table
    
    def create_stats_panel(self):
        """创建底部统计面板 - 紧凑横向布局"""
        group = QGroupBox("统计信息")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                margin-top: 6px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        layout = QHBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(6, 2, 6, 2)
        
        self.series_labels = {}
        
        series_config = [
            ('IF', '沪深300', '#1a5276'),
            ('IH', '上证50', '#7d3c98'),
            ('IC', '中证500', '#1e8449'),
            ('IM', '中证1000', '#b9770e'),
        ]
        
        for key, name, color in series_config:
            box = QFrame()
            box.setStyleSheet(f"""
                QFrame {{
                    border: 2px solid {color};
                    border-radius: 4px;
                    padding: 2px 6px;
                }}
            """)
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(4, 2, 4, 2)
            box_layout.setSpacing(1)
            
            title = QLabel(f"<b style='color:{color};'>{name}</b>")
            title.setAlignment(Qt.AlignCenter)
            box_layout.addWidget(title)
            
            labels = {}
            for lkey, text in [('spot', '现货: --'), ('max_basis', '最大基差: --'), 
                               ('min_basis', '最小基差: --'), ('avg_basis', '平均基差: --'),
                               ('avg_annual', '平均年化: --')]:
                lbl = QLabel(text)
                lbl.setStyleSheet("font-size: 11px; padding: 0px;")
                box_layout.addWidget(lbl)
                labels[lkey] = lbl
            
            layout.addWidget(box)
            self.series_labels[key] = labels
        
        # 总体统计
        total_box = QFrame()
        total_box.setStyleSheet("""
            QFrame {
                border: 2px solid #c0392b;
                border-radius: 4px;
                padding: 2px 6px;
            }
        """)
        total_layout = QVBoxLayout(total_box)
        total_layout.setContentsMargins(4, 2, 4, 2)
        total_layout.setSpacing(1)
        
        title = QLabel("<b style='color:#c0392b;'>总体</b>")
        title.setAlignment(Qt.AlignCenter)
        total_layout.addWidget(title)
        
        self.total_labels = {}
        for lkey, text in [('max_basis', '最大基差: --'), ('min_basis', '最小基差: --'),
                           ('avg_basis', '平均基差: --'), ('avg_annual', '平均年化: --')]:
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 11px; padding: 0px;")
            total_layout.addWidget(lbl)
            self.total_labels[lkey] = lbl
        
        layout.addWidget(total_box)
        
        group.setLayout(layout)
        return group
    
    def create_statusbar(self):
        """创建状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("系统就绪 - 点击'开始监控'启动")
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        
        # 检查log_text是否已创建
        if hasattr(self, 'log_text') and self.log_text is not None:
            self.log_text.append(log_entry)
        
        print(log_entry)  # 同时输出到控制台
    
    def start_monitoring(self):
        """开始监控"""
        self.timer.start(self.update_interval)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("🟢 运行中")
        self.log_message("开始实时监控...")
        self.update_data()
    
    def stop_monitoring(self):
        """停止监控"""
        self.timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("🔴 已停止")
        self.log_message("停止实时监控")
    
    def datetime_to_excel_date(self, date):
        """日期转换"""
        return (date - datetime.date(1899, 12, 30)).days
    
    def calculate_basis(self, code, futures_price):
        """计算基差（与Excel完全一致）

        Excel公式对照:
        - 合约总天数 = 到期日 - 上市日（交易日）
        - 剩余交易日 = 到期日 - 今天（交易日）
        - 基差(期-现) = 期货价格 - 现货价格
        - 年化(交易日) = (基差 / 现货价格) / 剩余交易日 * 252 * 100
        - 年化(自然日) = (基差 / 现货价格) / 剩余天数 * 365 * 100
        """
        index_type = code[:2]
        spot_price = self.spot_prices.get(index_type, 0)

        contract_month = code[-4:]

        if spot_price == 0 or futures_price == 0:
            return 0, 0, 0.0, 0.0, 0.0

        if contract_month in self.contract_dates:
            listing_date_excel = self.contract_dates[contract_month]['listing_date']
            expiry_date_excel = self.contract_dates[contract_month]['expiry_date']
        else:
            return 0, 0, 0.0, 0.0, 0.0

        today = datetime.date.today()

        # 转换日期格式
        listing_date = datetime.date(1899, 12, 30) + datetime.timedelta(days=listing_date_excel)
        expiry_date = datetime.date(1899, 12, 30) + datetime.timedelta(days=expiry_date_excel)

        # 1. 合约总天数（交易日）
        contract_total_days = WorkdayManager.count_workdays_between(listing_date, expiry_date)
        contract_total_days = max(contract_total_days, 1)

        # 2. 剩余交易日（用于年化(交易日)计算）
        remaining_trading_days = WorkdayManager.count_workdays_between(today, expiry_date)
        remaining_trading_days = max(remaining_trading_days, 0)

        # 3. 剩余天数（自然日，用于年化(自然日)计算）
        remaining_days = (expiry_date - today).days
        remaining_days = max(remaining_days, 0)

        # 4. 基差
        basis = futures_price - spot_price

        # 5. 年化(交易日) = (基差/现货) / 剩余交易日 * 252 * 100
        annual_trading = 0
        if remaining_trading_days > 0 and spot_price > 0:
            annual_trading = (basis / spot_price) / remaining_trading_days * 252 * 100

        # 6. 年化(自然日) = (基差/现货) / 剩余天数 * 365 * 100
        annual_calendar = 0
        if remaining_days > 0 and spot_price > 0:
            annual_calendar = (basis / spot_price) / remaining_days * 365 * 100

        return contract_total_days, remaining_trading_days, remaining_days, basis, annual_trading, annual_calendar
    
    def get_trade_date(self):
        """获取当前应该使用的交易日期
        
        交易时间：
        - 上午：9:30 - 11:30
        - 下午：13:00 - 15:00
        
        非交易时间处理：
        - 9:00之前：使用前一个交易日的数据
        - 15:00之后：使用当天收盘数据（如果已收盘）
        """
        now = datetime.datetime.now()
        current_time = now.time()
        today = now.date()
        
        # 判断当前是否在交易时间内
        morning_start = datetime.time(9, 30)
        morning_end = datetime.time(11, 30)
        afternoon_start = datetime.time(13, 0)
        afternoon_end = datetime.time(15, 0)
        
        # 检查是否是交易日（周一到周五）
        is_trading_day = today.weekday() < 5
        
        if not is_trading_day:
            # 周末，使用周五的数据
            days_back = today.weekday() - 4  # 周五
            trade_date = today - datetime.timedelta(days=days_back)
            return trade_date.strftime('%Y%m%d'), True
        
        # 判断时间
        if current_time < morning_start:
            # 早上9:00之前，使用前一天的收盘数据
            trade_date = today - datetime.timedelta(days=1)
            # 如果前一天是周末，继续往前推
            while trade_date.weekday() >= 5:
                trade_date -= datetime.timedelta(days=1)
            return trade_date.strftime('%Y%m%d'), True
        
        elif morning_end < current_time < afternoon_start:
            # 午休时间，使用当天上午的数据或前一天收盘数据
            return today.strftime('%Y%m%d'), False
        
        elif current_time > afternoon_end:
            # 15:00收盘后，使用当天收盘数据
            return today.strftime('%Y%m%d'), True
        
        else:
            # 交易时间内，使用当天数据
            return today.strftime('%Y%m%d'), False

    def update_data(self):
        """更新数据"""
        self.status_label.setText("🟡 更新中...")
        self.statusbar.showMessage("正在获取数据...")
        
        self.fetcher_thread = DataFetcherThread()
        self.fetcher_thread.data_fetched.connect(self.on_data_fetched)
        self.fetcher_thread.error_occurred.connect(self.on_fetch_error)
        self.fetcher_thread.log_message.connect(self.log_message)
        self.fetcher_thread.finished.connect(self.on_fetcher_finished)
        self.fetcher_thread.start()
    
    def on_data_fetched(self, futures_data, spot_prices, contract_codes, contract_dates):
        """数据获取完成回调"""
        need_rebuild = False
        
        if contract_dates:
            self.contract_dates.update(contract_dates)
        
        if contract_codes and contract_codes != self.contract_codes:
            self.log_message(f"合约列表更新: {len(contract_codes)}个合约")
            self.rebuild_data_and_table(contract_codes)
            need_rebuild = True
        
        self.spot_prices = spot_prices
        
        # 更新数据
        success_count = 0
        for i, code in enumerate(self.data['代码']):
            if code in futures_data:
                price = futures_data[code]
                self.data.loc[i, '现价'] = price
                
                result = self.calculate_basis(code, price)
                contract_total_days, remaining_trading_days, remaining_days, basis, annual_trading, annual_calendar = result

                self.data.loc[i, '现货价'] = self.spot_prices.get(code[:2], 0)
                self.data.loc[i, '合约总天数'] = contract_total_days
                self.data.loc[i, '剩余交易日'] = remaining_trading_days
                self.data.loc[i, '基差(期-现)'] = round(basis, 2)
                self.data.loc[i, '年化(交易日)'] = round(annual_trading, 2)
                self.data.loc[i, '年化(自然日)'] = round(annual_calendar, 2)
                success_count += 1
        
        # 计算价差相关列：价差差值、到期天数差值、差值/到期天数差值
        self.calculate_spread_columns()
        
        if success_count == 0 and not need_rebuild:
            self.log_message("⚠️ 未获取到任何期货数据")
            self.status_label.setText("🟡 数据获取失败")
            self.statusbar.showMessage("数据获取失败")
        else:
            self.log_message(f"成功更新 {success_count} 个合约数据")
    
    def calculate_spread_columns(self):
        """计算价差差值列"""
        # 获取各个合约的现价（按合约类型分组）
        contract_data = {'IF': {}, 'IC': {}, 'IM': {}, 'IH': {}}
        for i, row in self.data.iterrows():
            code = str(row['代码']).split('.')[0]
            series = code[:2]
            month = code[2:]
            if series in contract_data:
                contract_data[series][month] = {
                    'price': row['现价']
                }
        
        # 计算每个合约的价差差值
        for i, row in self.data.iterrows():
            code = str(row['代码']).split('.')[0]
            series = code[:2]
            month = code[2:]
            
            # 获取前一个合约月份（支持任意月份）
            prev_month = self._get_prev_month(month, list(contract_data[series].keys()))
            
            if prev_month in contract_data[series]:
                current_price = row['现价']
                prev_price = contract_data[series][prev_month]['price']
                
                # 价差差值 = 前一个月份现价 - 当前月份现价
                spread_diff = prev_price - current_price
                self.data.loc[i, '价差差值'] = round(spread_diff, 2)
            else:
                # 没有前一个合约，显示空值
                self.data.loc[i, '价差差值'] = ''

    def _get_prev_month(self, month, available_months):
        """获取前一个合约月份（支持任意月份）"""
        # 将月份转换为数字以便比较
        month_num = int(month)
        # 找到比当前月份小的最大月份
        prev_month_num = None
        for m in available_months:
            m_num = int(m)
            if m_num < month_num:
                if prev_month_num is None or m_num > prev_month_num:
                    prev_month_num = m_num
        if prev_month_num is not None:
            return f"{prev_month_num:04d}"
        return None

    def _get_next_month(self, month):
        """获取下一个合约月份（股指期货只有3、6、9、12月合约）"""
        # 合约月份列表
        contract_months = ['03', '06', '09', '12']
        year = int(month[:2])
        mon = month[2:]
        
        if mon in contract_months:
            idx = contract_months.index(mon)
            if idx < len(contract_months) - 1:
                return f"{year:02d}{contract_months[idx + 1]}"
            else:
                # 12月的下一个是明年3月
                return f"{year + 1:02d}03"
        return None

    def rebuild_data_and_table(self, new_contract_codes):
        """根据新合约列表重建数据和表格"""
        self.init_data(new_contract_codes)
        
        # 重建表格
        old_table = self.table
        self.table = self.create_data_table()
        
        # 找到表格所在的布局并替换
        parent = old_table.parent()
        if parent:
            layout = parent.layout()
            if layout:
                idx = layout.indexOf(old_table)
                layout.removeWidget(old_table)
                old_table.deleteLater()
                layout.insertWidget(idx, self.table)
        
        self.log_message(f"表格已重建: {len(new_contract_codes)}个合约")
    
    def on_fetcher_finished(self):
        """数据获取线程结束回调"""
        # 更新表格显示
        self.update_table()
        
        # 更新统计信息
        self.update_stats()
        
        # 更新时间
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.time_label.setText(f"🕐 {current_time}")
        self.status_label.setText("🟢 运行中")
        self.statusbar.showMessage(f"数据更新成功 - {current_time}")
        
        # 自动保存到Excel
        if self.auto_save_checkbox.isChecked():
            self.save_to_excel()
    
    def on_fetch_error(self, error_msg):
        """数据获取错误回调"""
        self.status_label.setText("🔴 更新失败")
        self.statusbar.showMessage(f"更新失败: {error_msg}")
        self.log_message(f"更新失败: {error_msg}")
        QMessageBox.warning(self, "数据获取失败", f"获取数据时发生错误:\n{error_msg}")
    
    def update_table(self):
        """更新表格显示 - 带颜色标记"""
        series_colors = {
            'IF': QColor(230, 240, 255),
            'IH': QColor(245, 230, 255),
            'IC': QColor(230, 255, 240),
            'IM': QColor(255, 245, 225),
        }
        
        for i, row in self.data.iterrows():
            code = row['代码']
            series = code[:2]
            bg_color = series_colors.get(series, QColor(255, 255, 255))
            
            for j, col in enumerate(['代码', '名称', '现价', '现货价', '价差差值', '合约总天数',
                                     '剩余交易日', '基差(期-现)', '年化(交易日)', '年化(自然日)']):
                value = row[col]
                
                if col in ['现价', '现货价', '基差(期-现)', '价差差值']:
                    text = f"{value:.2f}" if value != '' else ""
                elif col in ['年化(交易日)', '年化(自然日)']:
                    text = f"{value:.2f}%" if value != '' else ""

                elif col == '代码':
                    text = f"{value}.CFE"
                else:
                    text = str(int(value)) if isinstance(value, (int, float)) and value == int(value) else str(value)
                
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(QBrush(bg_color))
                
                if col == '基差(期-现)':
                    if value > 0:
                        item.setForeground(QBrush(QColor('#c0392b')))
                    elif value < 0:
                        item.setForeground(QBrush(QColor('#2980b9')))
                
                if col in ['年化(交易日)', '年化(自然日)']:
                    if value > 0:
                        item.setForeground(QBrush(QColor('#c0392b')))
                    elif value < 0:
                        item.setForeground(QBrush(QColor('#2980b9')))
                
                self.table.setItem(i, j, item)
    
    def update_stats(self):
        """更新统计信息 - 按系列分组统计"""
        all_basis = []
        all_annual = []
        
        for series in ['IF', 'IH', 'IC', 'IM']:
            series_data = self.data[self.data['代码'].str.startswith(series)]
            series_basis = series_data['基差(期-现)'].values
            series_annual = series_data['年化(交易日)'].values
            
            valid_basis = series_basis[series_basis != 0]
            valid_annual = series_annual[series_annual != 0]
            
            labels = self.series_labels.get(series, {})
            
            spot_price = self.spot_prices.get(series, 0)
            labels.get('spot', QLabel()).setText(f"现货: {spot_price:.2f}" if spot_price > 0 else "现货: --")
            
            if len(valid_basis) > 0:
                labels.get('max_basis', QLabel()).setText(f"最大基差: {valid_basis.max():.2f}")
                labels.get('min_basis', QLabel()).setText(f"最小基差: {valid_basis.min():.2f}")
                labels.get('avg_basis', QLabel()).setText(f"平均基差: {valid_basis.mean():.2f}")
                all_basis.extend(valid_basis)
            else:
                labels.get('max_basis', QLabel()).setText("最大基差: --")
                labels.get('min_basis', QLabel()).setText("最小基差: --")
                labels.get('avg_basis', QLabel()).setText("平均基差: --")
            
            if len(valid_annual) > 0:
                labels.get('avg_annual', QLabel()).setText(f"平均年化: {valid_annual.mean():.2f}")
                all_annual.extend(valid_annual)
            else:
                labels.get('avg_annual', QLabel()).setText("平均年化: --")
        
        if len(all_basis) > 0:
            self.total_labels['max_basis'].setText(f"最大基差: {max(all_basis):.2f}")
            self.total_labels['min_basis'].setText(f"最小基差: {min(all_basis):.2f}")
            self.total_labels['avg_basis'].setText(f"平均基差: {sum(all_basis)/len(all_basis):.2f}")
        else:
            self.total_labels['max_basis'].setText("最大基差: --")
            self.total_labels['min_basis'].setText("最小基差: --")
            self.total_labels['avg_basis'].setText("平均基差: --")
        
        if len(all_annual) > 0:
            self.total_labels['avg_annual'].setText(f"平均年化: {sum(all_annual)/len(all_annual):.2f}")
        else:
            self.total_labels['avg_annual'].setText("平均年化: --")
    
    def save_to_excel(self):
        """保存数据到Excel"""
        try:
            self.excel_updater_thread = ExcelUpdaterThread(self.data, self.excel_path)
            self.excel_updater_thread.update_finished.connect(self.on_excel_saved)
            self.excel_updater_thread.log_message.connect(self.log_message)
            self.excel_updater_thread.start()
        except Exception as e:
            self.log_message(f"启动Excel保存线程失败: {str(e)}")
    
    def on_excel_saved(self, success, message):
        """Excel保存完成回调"""
        if success:
            self.statusbar.showMessage(f"Excel已更新: {message}")
        else:
            self.log_message(f"Excel保存失败: {message}")
    
    def open_excel_file(self):
        """打开Excel文件"""
        try:
            if os.path.exists(self.excel_path):
                os.startfile(self.excel_path)
                self.log_message(f"打开Excel文件: {self.excel_path}")
            else:
                QMessageBox.warning(self, "文件不存在", "Excel文件尚未生成，请先开始监控或导出数据")
        except Exception as e:
            QMessageBox.critical(self, "打开失败", f"无法打开Excel文件:\n{str(e)}")
    
    def check_market_close(self):
        """检查是否收盘（15:00），如果是则自动截图"""
        now = datetime.datetime.now()
        
        # 检查是否是交易日（周一到周五）
        if now.weekday() >= 5:  # 周六日不检查
            return
        
        # 检查是否是15:00收盘时间（允许1分钟误差）
        if now.hour == 15 and now.minute == 0 and not self.screenshot_taken_today:
            self.log_message("检测到收盘时间，正在自动截图...")
            self.take_screenshot(auto=True)
            self.screenshot_taken_today = True
        
        # 重置标记（第二天开盘前重置）
        if now.hour == 8 and now.minute == 0:
            self.screenshot_taken_today = False
    
    def take_screenshot(self, auto=False):
        """截图功能"""
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if auto:
                filename = f"基差监控收盘截图_{timestamp}.png"
                msg_title = "收盘自动截图"
                msg_text = f"收盘截图已自动保存为:\\n{filename}"
            else:
                filename = f"基差监控日终截图_{timestamp}.png"
                msg_title = "截图成功"
                msg_text = f"截图已保存为:\\n{filename}"
            
            screenshot = pyautogui.screenshot()
            screenshot.save(filename)
            
            if not auto:
                QMessageBox.information(self, msg_title, msg_text)
            
            self.log_message(f"截图已保存: {filename}")
            self.statusbar.showMessage(f"截图已保存: {filename}")
            
        except Exception as e:
            error_msg = f"截图保存失败:\\n{str(e)}"
            if not auto:
                QMessageBox.critical(self, "截图失败", error_msg)
            self.log_message(f"截图失败: {str(e)}")
    
    def export_data(self):
        """导出数据到Excel（手动选择路径）"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "保存数据", 
                f"基差数据_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
                "Excel Files (*.xlsx);;All Files (*)"
            )
            
            if filename:
                self.data.to_excel(filename, index=False, engine='openpyxl')
                QMessageBox.information(self, "导出成功", f"数据已保存到:\\n{filename}")
                self.log_message(f"数据已导出: {filename}")
                self.statusbar.showMessage(f"数据已导出: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"数据导出失败:\\n{str(e)}")
    
    def set_interval_dialog(self):
        """设置更新频率对话框"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QSpinBox, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle("设置更新频率")
        dialog.setGeometry(200, 200, 300, 150)
        
        layout = QVBoxLayout()
        
        label = QLabel("更新间隔(秒):")
        layout.addWidget(label)
        
        spinbox = QSpinBox()
        spinbox.setRange(1, 60)
        spinbox.setValue(self.update_interval // 1000)
        layout.addWidget(spinbox)
        
        btn = QPushButton("确定")
        btn.clicked.connect(lambda: self.apply_interval(spinbox.value(), dialog))
        layout.addWidget(btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def apply_interval(self, seconds, dialog):
        """应用更新频率"""
        self.update_interval = seconds * 1000
        self.interval_label.setText(f"⏱️ {seconds}秒")
        self.timer.setInterval(self.update_interval)
        self.log_message(f"更新间隔已设置为 {seconds} 秒")
        dialog.close()
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于", 
            "股指期货基差实时监控系统\\n\\n"
            "版本: 2.0\\n"
            "功能: 实时监控中金所股指期货基差数据\\n"
            "数据源: SFTP实时行情\\n"
            "更新频率: 可自定义(默认3秒)\\n"
            "特色: 实时更新Excel文件\\n\\n"
            "© 2026 版权所有"
        )
    
    def closeEvent(self, event):
        """关闭事件"""
        reply = QMessageBox.question(self, '确认退出', '确定要退出系统吗?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.timer.stop()
            self.market_close_timer.stop()
            event.accept()
        else:
            event.ignore()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f0f2f5;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 12px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QPushButton {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2980b9;
        }
        QPushButton:pressed {
            background-color: #21618c;
        }
        QPushButton:disabled {
            background-color: #bdc3c7;
        }
        QTextEdit {
            background-color: #1e1e1e;
            color: #00ff00;
            font-family: Consolas, monospace;
            font-size: 11px;
        }
    """)
    
    # 设置全局字体
    font = QFont('Microsoft YaHei', 9)
    app.setFont(font)
    
    window = BasisMonitorWindow()
    window.show()
    sys.exit(app.exec_())