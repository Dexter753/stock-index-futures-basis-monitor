# -*- coding:utf-8 -*-  
import os
import pandas as pd
import time
import warnings
from cryptography.utils import CryptographyDeprecationWarning
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)
import paramiko

class SftpManager(object):
    host = None
    port = None
    user = None
    passwd = None
    
    @classmethod
    def init(self, host, port, user, passwd):
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
          
    @classmethod
    def load(self, csvfile, type_dict = {'code': str}, cols_list = None):
        csvfile = csvfile.replace("\\", "/")
        csvfile = csvfile.replace("//", "/")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.host, self.port, self.user, self.passwd)

        data = None
        with client.open_sftp() as sftp:
            #print(csvfile)
            try:
                remote_file = sftp.open(csvfile, 'r')

                if cols_list is None:
                    if type_dict is None:
                        data = pd.read_csv(remote_file)
                    else:
                        data = pd.read_csv(remote_file, dtype = type_dict)
                else:
                    if type_dict is None:                    
                        data = pd.read_csv(remote_file, usecols = cols_list)
                    else:
                        data = pd.read_csv(remote_file, dtype = type_dict, usecols = cols_list)
            except Exception as e:
                print(e)

        #finish load
        client.close()
        return data
    

if __name__ == '__main__':
    host = '168.yibeiinv.com'  # 主机
    port = 39866  # 端口
    username = 'trading'  # 用户名
    password = 'Js123456!Yibei3618!'  # 密码
    SftpManager.init(host=host,port=port,user=username,passwd=password)
    today = time.strftime('%Y%m%d')
    # 读取 期货行情数据
    df = SftpManager.load(f'/data/Std_Data/idata/StdData/real_tik/{today}_fut.csv',type_dict={"代码":str})
    print(df.head())
    # 读取 指数行情数据
    df = SftpManager.load(f'/data/Std_Data/idata/StdData/real_tik/{today}_idx.csv',type_dict={"代码":str})
    df = df[df['代码'] .isin(['sz399905','sh000300','sz399852','sh000016',])]
    print(df.head())
