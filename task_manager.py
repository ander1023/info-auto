# task_manager.py
import asyncio
import threading
import time
import subprocess
import sys
from queue import Queue
import logging
from logging.handlers import QueueHandler, QueueListener
import json
from datetime import datetime

import main


class TaskManager:
    def __init__(self):
        self.is_running = False
        self.current_process = None
        self.log_queue = Queue()
        self.log_listener = None
        self.log_buffer = []  # 存储最近的日志
        self.max_log_entries = 1000  # 最大日志条目数
        self.setup_logging()
        self.socketio = None

    def set_socketio(self, socketio):
        """设置SocketIO实例用于实时推送"""
        self.socketio = socketio

    def setup_logging(self):
        """设置日志系统"""
        # 创建自定义的日志处理器
        self.log_listener = QueueListener(self.log_queue, self)
        self.log_listener.start()

    def handle(self, record):
        """处理日志记录"""
        log_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name
        }

        # 添加到缓冲区
        self.log_buffer.append(log_entry)
        if len(self.log_buffer) > self.max_log_entries:
            self.log_buffer.pop(0)

        # 实时推送到前端
        if self.socketio:
            try:
                self.socketio.emit('log_update', log_entry)
            except Exception as e:
                print(f"推送日志失败: {e}")

    def get_logger(self, name):
        """获取配置好的logger"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)

        # 移除已有的处理器，避免重复
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        logger.addHandler(QueueHandler(self.log_queue))
        logger.propagate = False
        return logger

    def run_main(self):
        """在新的线程中运行main函数"""

        def run_task():
            self.is_running = True
            logger = self.get_logger('task_runner')

            try:
                logger.info("开始信息收集自动化流程...")
                iteration = 1

                while self.is_running:
                    logger.info(f"=== 第 {iteration} 轮处理 ===")

                    processed_count = 0

                    # 执行各个任务
                    try:
                        logger.info("开始子域名解析...")
                        processed_count += main.host()
                        logger.info("子域名解析完成")
                    except Exception as e:
                        logger.error(f"子域名解析失败: {e}")

                    try:
                        logger.info("开始IP地理位置识别...")
                        processed_count += main.nali()
                        logger.info("IP地理位置识别完成")
                    except Exception as e:
                        logger.error(f"IP地理位置识别失败: {e}")

                    try:
                        logger.info("开始端口扫描...")
                        processed_count += main.masscan()
                        logger.info("端口扫描完成")
                    except Exception as e:
                        logger.error(f"端口扫描失败: {e}")

                    try:
                        logger.info("开始HTTP服务发现...")
                        processed_count += main.httpx()
                        logger.info("HTTP服务发现完成")
                    except Exception as e:
                        logger.error(f"HTTP服务发现失败: {e}")

                    if processed_count == 0:
                        logger.info("所有处理流程已完成，退出循环")
                        break

                    iteration += 1

                    # 检查是否应该停止
                    if not self.is_running:
                        logger.info("任务被用户停止")
                        break

                logger.info("信息收集自动化流程执行完毕")

            except Exception as e:
                logger.error(f"任务执行出错: {e}")
            finally:
                self.is_running = False

        # 在新线程中运行任务
        thread = threading.Thread(target=run_task)
        thread.daemon = True
        thread.start()

    def stop_main(self):
        """停止main函数执行"""
        self.is_running = False
        if self.current_process:
            self.current_process.terminate()
            self.current_process = None

    def get_status(self):
        """获取任务状态"""
        return {
            'is_running': self.is_running,
            'timestamp': time.time()
        }

    def get_logs(self, last_n=100):
        """获取最近的日志"""
        return self.log_buffer[-last_n:] if last_n <= len(self.log_buffer) else self.log_buffer


# 全局任务管理器实例
task_manager = TaskManager()