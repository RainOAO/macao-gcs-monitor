#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速測試 Email 發送功能"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime


def test_email():
    # 讀取配置
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    smtp_server = config.get('smtp_server', 'smtp-mail.outlook.com')
    smtp_port = config.get('smtp_port', 587)
    smtp_use_ssl = config.get('smtp_use_ssl', False)
    smtp_username = config['smtp_username']
    smtp_password = config['smtp_password']
    email_from = config.get('email_from', smtp_username)
    email_to = config.get('email_to', [])
    
    if isinstance(email_to, str):
        email_to = [email_to]
    
    print(f"SMTP 服務器: {smtp_server}:{smtp_port}")
    print(f"發件人: {email_from}")
    print(f"收件人: {', '.join(email_to)}")
    print()
    
    # 構建測試郵件
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    msg = MIMEMultipart('alternative')
    msg['From'] = email_from
    msg['To'] = ', '.join(email_to)
    msg['Subject'] = Header(f'【測試】澳門新聞監控系統 Email 測試 - {now}', 'utf-8')
    
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f4f6f9; padding: 20px;">
<div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 10px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); overflow: hidden;">
  <div style="background: linear-gradient(135deg, #1a73e8, #0d47a1); padding: 24px 30px; color: #fff;">
    <h1 style="margin:0; font-size:22px;">✅ Email 發送測試成功!</h1>
    <p style="margin:8px 0 0; font-size:13px; opacity:0.85;">測試時間: {now}</p>
  </div>
  <div style="padding: 24px 30px;">
    <p style="font-size:15px; color:#333;">如果您收到此郵件，說明 Email 推送配置正確！</p>
    <p style="font-size:14px; color:#666;">系統將在檢測到軍團菌相關新聞時，自動發送格式化的通知郵件到此郵箱。</p>
    <div style="background:#e8f0fe; border-left:4px solid #1a73e8; padding:12px 16px; border-radius:0 6px 6px 0; margin-top:16px;">
      <strong>配置信息</strong><br>
      SMTP: {smtp_server}:{smtp_port}<br>
      發件人: {email_from}
    </div>
  </div>
  <div style="padding:16px 30px; background:#f8f9fa; border-top:1px solid #e8eaed; text-align:center; font-size:12px; color:#999;">
    澳門新聞局軍團菌新聞監控系統 · Email 版
  </div>
</div>
</body>
</html>"""
    
    text = f"Email 發送測試成功!\n測試時間: {now}\n\n如果您收到此郵件，說明配置正確。"
    
    msg.attach(MIMEText(text, 'plain', 'utf-8'))
    msg.attach(MIMEText(html, 'html', 'utf-8'))
    
    # 發送
    print("正在連接 SMTP 服務器...")
    try:
        if smtp_use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context, timeout=30) as server:
                print("正在登錄...")
                server.login(smtp_username, smtp_password)
                print("正在發送郵件...")
                server.sendmail(email_from, email_to, msg.as_string())
        else:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                print("正在登錄...")
                server.login(smtp_username, smtp_password)
                print("正在發送郵件...")
                server.sendmail(email_from, email_to, msg.as_string())
        
        print()
        print("=" * 50)
        print("✅ 郵件發送成功!")
        print(f"請檢查 {', '.join(email_to)} 的收件箱")
        print("=" * 50)
        
    except smtplib.SMTPAuthenticationError as e:
        print()
        print("=" * 50)
        print(f"❌ 認證失敗: {e}")
        print()
        print("可能原因:")
        print("1. 用戶名或密碼錯誤")
        print("2. Outlook 需要使用應用專用密碼")
        print("3. 賬號安全設置阻止了登錄")
        print("=" * 50)
    except Exception as e:
        print()
        print(f"❌ 發送失敗: {e}")


if __name__ == '__main__':
    test_email()
