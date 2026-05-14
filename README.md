# 股指期货基差实时监控系统

## 项目安装依赖项

```bash
pip install PyQt5 pandas openpyxl pyautogui paramiko
```

## 项目说明

本项目是一个专业的股指期货基差实时监控工具，基于PyQt5开发，数据源通过SFTP和FTP获取公司内部实时行情，适合给领导展示使用。

## 文件说明

| 文件 | 说明 | 用途 |
| --- | --- | --- |
| `basis_monitor_pyqt.py` | **主程序（推荐使用）** | PyQt5版本，界面专业，功能完善，内嵌SFTP和FTP数据源 |
| `python_2_ftp_demo.py` | FTP数据源参考 | 提供FTP连接参数和交易日历读取示例，主程序已内嵌此功能 |
| `python_3_sftp_1.py` | SFTP数据源参考 | 提供SFTP连接参数和数据读取示例，主程序已内嵌此功能 |
| `shujujiankong.py` | 备用程序 | tkinter版本，轻量级（已弃用） |

## 推荐使用方案

**建议使用 `basis_monitor_pyqt.py`**，原因：

1. 界面更专业，适合给领导展示
2. 功能更完善（菜单栏、工具栏、状态栏）
3. 支持收盘自动截图
4. 支持数据导出Excel
5. 支持自定义更新频率
6. 内嵌SFTP和FTP数据源，无需额外配置
7. 盘前自动回退到前一交易日数据

## 数据源说明

### SFTP连接配置

- **主机**: `168.yibeiinv.com`
- **端口**: `39866`
- **用户名**: `trading`

> SFTP连接参数已内嵌在 `basis_monitor_pyqt.py` 的 `SftpManager` 类中，无需额外配置。

### FTP连接配置（交易日历）

- **主机**: `168.yibeiinv.com`
- **端口**: `59100`
- **用户名**: `Scripts_Only`
- **文件路径**: `/common_config/workdays.cfg`

> FTP连接参数已内嵌在 `basis_monitor_pyqt.py` 的 `WorkdayManager` 类中，用于获取交易日历数据。

### 数据源架构（混合方案）

系统采用混合数据源方案，从SFTP和FTP分别获取不同数据：

| 数据类型 | 协议 | 路径 | 说明 |
| --- | --- | --- | --- |
| 合约列表 | SFTP | `/data/ctp_data/future/{日期}/name_map.csv` | 动态获取当前可用的IF/IH/IC/IM合约 |
| 合约日期 | SFTP | `/data/ctp_data/future/{日期}/future_code_list.csv` | 获取上市日(open_date)和到期日(expire_date) |
| 期货价格 | SFTP | `/data/Std_Data/idata/StdData/real_tik/{日期}_fut.csv` | 获取期货实时/收盘价格 |
| 指数现货 | SFTP | `/data/Std_Data/idata/StdData/real_tik/{日期}_idx.csv` | 获取指数现货价格 |
| 交易日历 | FTP | `/common_config/workdays.cfg` | 获取全年交易日历，用于准确计算剩余交易日 |

### 数据获取流程

```
1. 读取交易日历(workdays.cfg) → 加载全年交易日列表
2. 读取 name_map.csv → 筛选 instrument_id 包含 IF/IH/IC/IM 的合约 → 得到合约列表
3. 读取 future_code_list.csv → 提取上市日和到期日 → 转换为日期对象
4. 读取 real_tik/{日期}_fut.csv → 按合约代码匹配价格 → 得到期货价格
5. 读取 real_tik/{日期}_idx.csv → 按指数代码匹配价格 → 得到现货价格
6. 使用交易日历计算合约总交易日、剩余交易日 → 计算基差、年化等指标
7. 更新界面和Excel
```

### 指数代码映射

| 品种 | 对应指数 | SFTP代码 |
| --- | --- | --- |
| IF | 沪深300 | `sh000300` |
| IH | 上证50 | `sh000016` |
| IC | 中证500 | `sz399905` |
| IM | 中证1000 | `sz399852` |

### 期货代码格式

在 `real_tik/{日期}_fut.csv` 中，期货代码格式为 `{合约}.CFFE`，如 `IF2606.CFFE`、`IC2609.CFFE`。系统会自动尝试多种格式匹配。

## 功能特性

### 实时监控

- 通过SFTP获取公司内部实时行情数据
- 通过FTP获取交易日历数据，确保计算准确性
- 合约列表动态获取（从 `name_map.csv` 自动筛选），无需手动维护
- 合约日期动态获取（从 `future_code_list.csv` 自动解析），无需手动配置
- 默认3秒更新频率，可自定义调整
- **盘前自动回退**：9:30前自动使用前一交易日数据
- **收盘后处理**：15:00后使用当天收盘数据

### 数据展示

- 专业表格展示所有合约数据
- 基差为负时自动标红提醒
- 顶部深色信息栏显示系统状态（数据源、更新间隔、时间、合约数、运行状态）
- 底部统计面板按品种分组显示最大/最小/平均基差及年化数据
- 新增「剩余交易日」列，与Excel保持一致

### 收盘截图

- **自动截图**：每天15:00收盘时自动截图保存
- **手动截图**：支持快捷键Ctrl+S或点击按钮截图
- 截图文件名带时间戳，便于归档

### 数据导出

- 支持导出Excel文件（自动保存到 `基差监控实时数据.xlsx`）
- 快捷键Ctrl+E快速导出
- 合约列表变化时自动重建表格

## 安装依赖

```bash
pip install PyQt5 pandas openpyxl pyautogui paramiko
```

## 运行方式

```bash
cd e:\stock-index-futures-basis-monitor
python basis_monitor_pyqt.py
```

程序启动后会自动测试SFTP和FTP连接并开始实时监控。

## 使用指南

### 首次运行

1. 确保已安装所有依赖（特别是 `paramiko`）
2. 确保网络可访问SFTP服务器 `168.yibeiinv.com:39866` 和FTP服务器 `168.yibeiinv.com:59100`
3. 运行程序，系统自动测试连接并开始监控

### 日常使用

1. **开盘前(9:30前)**：启动程序，系统自动使用前一交易日数据
2. **交易时间(9:30-15:00)**：实时查看基差变化，基差为负的合约会标红显示
3. **收盘时(15:00)**：系统自动截图保存
4. **收盘后(15:00后)**：使用当天收盘数据
5. **日终**：可手动导出Excel数据或截图

### 快捷键

| 快捷键 | 功能 |
| --- | --- |
| Ctrl+R | 开始监控 |
| Ctrl+T | 停止监控 |
| Ctrl+S | 日终截图 |
| Ctrl+E | 导出Excel |
| Ctrl+Q | 退出程序 |

## 数据说明

### 监控合约（动态获取）

合约列表从 `/data/ctp_data/future/{日期}/name_map.csv` 动态获取，自动筛选 `instrument_id` 包含 IF/IH/IC/IM 的合约。当前通常包含以下合约：

| 品种 | 对应指数 | 指数代码 | 期货合约 |
| --- | --- | --- | --- |
| IF | 沪深300 | 000300.SH | IF2605.CFE, IF2606.CFE, IF2609.CFE, IF2612.CFE |
| IH | 上证50 | 000016.SH | IH2605.CFE, IH2606.CFE, IH2609.CFE, IH2612.CFE |
| IC | 中证500 | 399905.SZ | IC2605.CFE, IC2606.CFE, IC2609.CFE, IC2612.CFE |
| IM | 中证1000 | 000852.SH | IM2605.CFE, IM2606.CFE, IM2609.CFE, IM2612.CFE |

> 合约列表随 `name_map.csv` 内容自动变化，无需手动更新代码。

### 计算公式（严格按照Excel公式，使用交易日计算）

- **合约总天数** = 上市日到到期日之间的交易日数
- **剩余交易日** = 今天到到期日之间的交易日数
- **基差(期-现)** = 期货价格 - 现货价格
- **年化(交易日)** = 基差 / 剩余交易日 × 252
- **年化(自然日)** = 基差 / 剩余自然日 × 365
- **价差差值** = 前一个合约现价 - 当前合约现价（如：IF2605现价 - IF2606现价）
- **到期天数差值** = 前一个合约剩余交易日 - 当前合约剩余交易日
- **差值/到期天数差值** = 价差差值 / 到期天数差值

> 交易日历从FTP服务器 `/common_config/workdays.cfg` 获取，确保计算准确性。

### 合约日期配置（动态获取）

合约日期从 `/data/ctp_data/future/{日期}/future_code_list.csv` 动态获取，自动解析 `open_date`（上市日）和 `expire_date`（到期日）。

> 日期配置随 `future_code_list.csv` 内容自动变化，无需手动更新代码。

## 注意事项

1. **网络连接**：需要能访问公司SFTP服务器 `168.yibeiinv.com:39866` 和FTP服务器 `168.yibeiinv.com:59100`
2. **收盘截图**：仅在交易日（周一到周五）15:00自动截图
3. **截图保存**：截图保存在程序运行目录，文件名包含时间戳
4. **非交易时间**：
   - 9:30前：自动使用前一交易日数据
   - 15:00后：使用当天收盘数据
   - 周末：自动使用上周五数据
5. **合约自动更新**：合约列表和日期从SFTP动态获取，合约到期换月后自动适配
6. **交易日历**：从FTP获取全年交易日历，确保天数计算准确

## 故障排除

### 无法获取数据

- 检查网络是否能访问SFTP和FTP服务器
- 检查SFTP和FTP账号密码是否正确（已内嵌在代码中）
- 查看运行日志中的详细错误信息
- 确认 `name_map.csv`、`future_code_list.csv` 和 `workdays.cfg` 是否存在

### SFTP/FTP连接失败

- 检查网络连接
- 确认服务器地址和端口是否正确
- 确认账号密码是否有效

### 界面显示异常

- 确保已安装PyQt5
- 尝试更换字体（代码中设置为Microsoft YaHei）

### 截图失败

- 检查是否有写入权限
- 检查磁盘空间是否充足
- 确保已安装 `pyautogui`

### 天数计算错误

- 检查交易日历是否加载成功（日志显示"交易日历加载成功: XXX个交易日"）
- 确认FTP服务器上的 `workdays.cfg` 文件存在且格式正确

## 技术支持

如有问题，请检查：

1. Python版本 >= 3.7
2. 所有依赖包已正确安装（`PyQt5`, `pandas`, `openpyxl`, `pyautogui`, `paramiko`）
3. SFTP和FTP服务器可正常访问
4. 运行日志中的错误提示信息

---

## 应用程序打包指南

### 打包工具

使用 **PyInstaller** 将 Python 脚本打包为独立的 Windows 可执行文件。

### 环境要求

- Python 3.7+
- 已安装所有依赖包（`PyQt5`, `pandas`, `openpyxl`, `pyautogui`, `paramiko`）
- 操作系统：Windows 10/11

### 打包步骤

#### 方法一：使用打包脚本（推荐）

运行项目中的打包脚本：

```bash
cd e:\stock-index-futures-basis-monitor
python package_app.py
```

#### 方法二：手动执行命令

```bash
cd e:\stock-index-futures-basis-monitor

# 安装 PyInstaller（如果未安装）
pip install pyinstaller

# 执行打包命令
pyinstaller -F -w --name="股指期货基差监控" ^
  --hidden-import=paramiko ^
  --hidden-import=pandas ^
  --hidden-import=openpyxl ^
  --hidden-import=pyautogui ^
  --hidden-import=PyQt5.QtWidgets ^
  --hidden-import=PyQt5.QtGui ^
  --hidden-import=PyQt5.QtCore ^
  --hidden-import=PyQt5.QtPrintSupport ^
  basis_monitor_pyqt.py
```

### 参数说明

| 参数 | 说明 |
| --- | --- |
| `-F` | 打包为单个可执行文件 |
| `-w` | 不显示控制台窗口（仅图形界面） |
| `--name` | 指定输出文件名 |
| `--hidden-import` | 添加隐藏导入（解决动态导入问题） |

### 打包输出

打包成功后，可执行文件位于：

```
e:\stock-index-futures-basis-monitor\dist\股指期货基差监控.exe
```

### 使用说明

1. **运行方式**：双击 `股指期货基差监控.exe` 即可启动应用
2. **无需安装**：应用程序已包含所有依赖，无需配置 Python 环境
3. **文件路径**：应用程序会在运行目录创建必要的日志和数据文件
4. **截图保存**：自动截图保存在程序运行目录

### 打包后的文件结构

```
e:\stock-index-futures-basis-monitor\
├── dist\
│   └── 股指期货基差监控.exe    # 主程序（约150MB）
├── build\                      # 临时构建目录（可删除）
├── basis_monitor_pyqt.py        # 源代码
├── package_app.py               # 打包脚本
├── 股指期货基差监控.spec        # PyInstaller配置文件
└── README.md                    # 项目文档
```

### 注意事项

1. **首次运行**：首次启动可能需要几秒加载时间
2. **网络连接**：需要能访问公司SFTP和FTP服务器
3. **权限要求**：需要有程序运行目录的读写权限（用于保存截图和日志）
4. **防火墙设置**：确保防火墙允许应用程序访问网络
5. **运行目录**：建议将 `股指期货基差监控.exe` 放在单独目录运行

### 测试验证

打包完成后，建议进行以下测试：

| 测试项 | 验证方法 |
| --- | --- |
| 启动测试 | 双击可执行文件，检查是否能正常启动 |
| 连接测试 | 查看状态栏是否显示"SFTP连接成功" |
| 数据测试 | 检查表格是否正常显示合约数据 |
| 截图测试 | 手动触发截图功能（Ctrl+S） |
| 导出测试 | 测试Excel导出功能（Ctrl+E） |

### 故障排除

**打包失败**
- 确保所有依赖已安装：`pip install PyQt5 pandas openpyxl pyautogui paramiko pyinstaller`
- 检查 Python 版本是否 >= 3.7
- 确保路径中没有中文或特殊字符

**运行时错误**
- 检查网络连接是否正常
- 查看程序目录下的日志输出
- 确认SFTP和FTP服务器地址正确

**杀毒软件误报**
- 某些杀毒软件可能会误报PyInstaller打包的程序
- 将 `股指期货基差监控.exe` 添加到杀毒软件白名单
