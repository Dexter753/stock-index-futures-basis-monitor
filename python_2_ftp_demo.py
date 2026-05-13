#!/usr/bin/python
# -*- coding: utf-8 -*-

import re
import os
import sys
import math
import time
import datetime
import traceback
from io import BytesIO

import ftplib

import pandas as pd
ftp_encoding = "utf-8"


class FtpManager(object):
    ftp_client = None

    @classmethod
    def init(self, host, port, user, pwd, encoding=ftp_encoding):
        """
        初始化FTP管理器，连接FTP服务器

        参数:
        host(str): FTP服务器主机名
        port(int): FTP服务器端口号
        user(str): FTP服务器登录用户名
        pwd(str): FTP服务器登录密码
        encoding(str, 可选): FTP服务器编码格式，默认为"utf-8"

        返回:
        无
        """
        connect_time = 0
        while connect_time <=3:
            connect_time = connect_time + 1
            try:
                self.ftp_client = ftplib.FTP()
                self.ftp_client.encoding = encoding
                self.ftp_client.connect(host=host, port=port)
                self.ftp_client.login(user=user, passwd=pwd)
                
                print(f'ftp连接成功 第{connect_time}次')
                break
            except:
                time.sleep(1)
                print(f'ftp连接失败 第{connect_time}次，开始重连>>>>>>>>>>>>>>>>>>>>>')
        if connect_time>3:
            exit(0)

    @classmethod
    def release(self):
        """
        释放FTP管理器资源

        参数:
        无

        返回:
        无
        """
        if self.ftp_client is not None:

            self.ftp_client.quit()

    @classmethod
    def read_file(self, remote_file):
        """
        读取FTP服务器上的文件

        参数:
        remote_file(str): 远程文件路径

        返回:
        file_stream(bytesIO对象): 文件流对象
        """
        remote_dir = os.path.dirname(remote_file)
        remote_name = os.path.basename(remote_file)

        remote_file = remote_file.replace("\\","/")


        try:
            self.ftp_client.cwd(remote_dir)
        except Exception as e:
            print(e)
            self.ftp_client.mkd(remote_dir)
            self.ftp_client.cwd(remote_dir)

        files = self.ftp_client.nlst()

        if remote_name not in files:
            err_msg = "ERR: ftp文件%s不存在!" % (remote_file)
            # raise Exception(err_msg)
            # print(err_msg)
            return False

        data = []
        def handle_binary(more_data):
            data.append(more_data)
        self.ftp_client.retrbinary("RETR " + remote_file, callback=handle_binary)
        f_stream = BytesIO(b''.join(data))
        f_stream.seek(0)
        self.release()
        return f_stream

   

if __name__ == '__main__':

    ftp_config = {"host": "168.yibeiinv.com", "port": 59100,"user": "Scripts_Only", "passwd": "only_186447"}
    FtpManager.init(ftp_config["host"], ftp_config["port"], ftp_config["user"], ftp_config["passwd"])   
    workdays = FtpManager.read_file('/common_config/workdays.cfg').read().decode().split('\r\n')
    print("workdays=",workdays[-5:])
