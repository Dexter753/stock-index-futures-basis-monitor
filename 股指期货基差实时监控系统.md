# 股指期货基差实时监控系统

## 项目安装依赖项

```bash
pip install PyQt5 pandas openpyxl pyautogui paramiko
```

## 项目说明

本项目是一个专业的股指期货基差实时监控工具，基于PyQt5开发，数据源通过SFTP获取公司内部实时行情，适合给领导展示使用。

## 文件说明

| 文件 | 说明 | 用途 |
| --- | --- | --- |
| `basis_monitor_pyqt.py` | **主程序（推荐使用）** | PyQt5版本，界面专业，功能完善，内嵌SFTP数据源 |
| `python_3_sftp_1.py` | SFTP数据源参考 | 提供SFTP连接参数和数据读取示例，主程序已内嵌此功能 |
| `shujujiankong.py` | 备用程序 | tkinter版本，轻量级（已弃用） |

## 推荐使用方案

**建议使用 `basis_monitor_pyqt.py`**，原因：

1. 界面更专业，适合给领导展示
2. 功能更完善（菜单栏、工具栏、状态栏）
3. 支持收盘自动截图
4. 支持数据导出Excel
5. 支持自定义更新频率
6. 内嵌SFTP数据源，无需额外配置API Token

## 数据源说明

### SFTP连接配置

- **主机**: `168.yibeiinv.com`
- **端口**: `39866`
- **用户名**: `trading`

> SFTP连接参数已内嵌在 `basis_monitor_pyqt.py` 的 `SftpManager` 类中，无需额外配置。

### 数据源架构（混合方案）

系统采用混合数据源方案，从两个SFTP路径分别获取不同数据：

| 数据类型 | SFTP路径 | 说明 |
| --- | --- | --- |
| 合约列表 | `/data/ctp_data/future/{日期}/name_map.csv` | 动态获取当前可用的IF/IH/IC/IM合约 |
| 合约日期 | `/data/ctp_data/future/{日期}/future_code_list.csv` | 获取上市日(open_date)和到期日(expire_date) |
| 期货价格 | `/data/Std_Data/idata/StdData/real_tik/{日期}_fut.csv` | 获取期货实时/收盘价格 |
| 指数现货 | `/data/Std_Data/idata/StdData/real_tik/{日期}_idx.csv` | 获取指数现货价格 |

**为什么采用混合方案？**

`/data/ctp_data/future/{日期}/` 目录结构如下：
```
/data/ctp_data/future/20260512/
├── name_map.csv          ← 合约映射（instrument_id → file_name）
├── future_code_list.csv  ← 合约信息（上市日、到期日等）
├── main.csv              ← 主力合约
├── bond_main.csv         ← 国债主力合约
├── tik/                  ← 逐笔数据（仅含国债期货TF/TL/TS/T）
└── 1min/                 ← 1分钟数据
```

`tik/` 子目录中只有国债期货的价格文件（如 `TF2606.CFFE.csv`），**没有**股指期货（IF/IH/IC/IM）的价格文件。因此期货价格需要从旧路径 `real_tik/{日期}_fut.csv` 获取。

### 数据获取流程

```
1. 读取 name_map.csv → 筛选 instrument_id 包含 IF/IH/IC/IM 的合约 → 得到合约列表
2. 读取 future_code_list.csv → 提取上市日和到期日 → 转换为Excel日期序列号
3. 读取 real_tik/{日期}_fut.csv → 按合约代码匹配价格 → 得到期货价格
4. 读取 real_tik/{日期}_idx.csv → 按指数代码匹配价格 → 得到现货价格
5. 计算基差、年化等指标 → 更新界面和Excel
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
- 合约列表动态获取（从 `name_map.csv` 自动筛选），无需手动维护
- 合约日期动态获取（从 `future_code_list.csv` 自动解析），无需手动配置
- 默认3秒更新频率，可自定义调整

### 数据展示

- 专业表格展示所有合约数据
- 基差为负时自动标红提醒
- 顶部深色信息栏显示系统状态（数据源、更新间隔、时间、合约数、运行状态）
- 底部统计面板按品种分组显示最大/最小/平均基差及年化数据

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
cd e:\价格实时监控
python basis_monitor_pyqt.py
```

程序启动后会自动测试SFTP连接并开始实时监控。

## 使用指南

### 首次运行

1. 确保已安装所有依赖（特别是 `paramiko`）
2. 确保网络可访问SFTP服务器 `168.yibeiinv.com:39866`
3. 运行程序，系统自动测试SFTP连接并开始监控

### 日常使用

1. **开盘前**：启动程序，系统开始实时监控
2. **交易时间**：实时查看基差变化，基差为负的合约会标红显示
3. **收盘时**：系统自动截图保存（15:00）
4. **日终**：可手动导出Excel数据或截图

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

### 计算公式（严格按照Excel公式）

- **合约总天数** = 到期日 - 上市日（Excel日期序列号）
- **剩余天数** = 到期日 - 今天
- **剩余天数占比** = 剩余天数 / 合约总天数
- **基差(期-现)** = 期货价格 - 现货价格
- **基差点比** = 基差 / 现货价格 × 10000
- **年化(交易日)** = 基差 / 剩余天数 × 252
- **年化(自然日)** = 基差 / 剩余天数 × 365

### 合约日期配置（动态获取）

合约日期从 `/data/ctp_data/future/{日期}/future_code_list.csv` 动态获取，自动解析 `open_date`（上市日）和 `expire_date`（到期日）并转换为Excel日期序列号。

> 日期配置随 `future_code_list.csv` 内容自动变化，无需手动更新代码。

## 注意事项

1. **网络连接**：需要能访问公司SFTP服务器 `168.yibeiinv.com:39866`
2. **收盘截图**：仅在交易日（周一到周五）15:00自动截图
3. **截图保存**：截图保存在程序运行目录，文件名包含时间戳
4. **非交易时间**：盘后数据使用当天收盘价，不会变化
5. **合约自动更新**：合约列表和日期从SFTP动态获取，合约到期换月后自动适配

## 故障排除

### 无法获取数据

- 检查网络是否能访问SFTP服务器
- 检查SFTP账号密码是否正确（已内嵌在代码中）
- 查看运行日志中的详细错误信息
- 确认 `name_map.csv` 和 `future_code_list.csv` 是否存在

### SFTP连接失败

- 检查网络连接
- 确认SFTP服务器地址和端口是否正确
- 确认账号密码是否有效

### 界面显示异常

- 确保已安装PyQt5
- 尝试更换字体（代码中设置为Microsoft YaHei）

### 截图失败

- 检查是否有写入权限
- 检查磁盘空间是否充足
- 确保已安装 `pyautogui`

## 技术支持

如有问题，请检查：

1. Python版本 >= 3.7
2. 所有依赖包已正确安装（`PyQt5`, `pandas`, `openpyxl`, `pyautogui`, `paramiko`）
3. SFTP服务器可正常访问
4. 运行日志中的错误提示信息
