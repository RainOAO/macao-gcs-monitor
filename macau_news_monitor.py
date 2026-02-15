#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
澳門新聞局軍團菌新聞監控系統 - Email 推送版本
自動抓取一天內所有新聞，檢查標題和內文是否包含軍團菌關鍵詞，並通過 Email 推送
"""

import os
import sys
import json
import logging
import argparse
import time
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Set, Optional
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

import requests
from bs4 import BeautifulSoup


class MacauNewsMonitorEmail:
    """澳門新聞監控器 - Email 推送版本"""
    
    def __init__(self, config_file: str = "config.json"):
        """初始化監控器"""
        self.config = self._load_config(config_file)
        self._setup_logging()
        self.sent_news = self._load_sent_news()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def _load_config(self, config_file: str) -> dict:
        """加載配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"錯誤: 配置文件 {config_file} 不存在")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"錯誤: 配置文件格式錯誤 - {e}")
            sys.exit(1)
            
    def _setup_logging(self):
        """設置日誌"""
        log_level = getattr(logging, self.config.get('log_level', 'INFO'))
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('macau_news_monitor.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def _load_sent_news(self) -> Set[str]:
        """加載已發送的新聞記錄"""
        sent_file = self.config.get('sent_news_file', 'sent_news.json')
        if os.path.exists(sent_file):
            try:
                with open(sent_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get('sent_urls', []))
            except Exception as e:
                self.logger.warning(f"加載已發送記錄失敗: {e}")
        return set()
        
    def _save_sent_news(self):
        """保存已發送的新聞記錄"""
        sent_file = self.config.get('sent_news_file', 'sent_news.json')
        try:
            with open(sent_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'sent_urls': list(self.sent_news),
                    'last_updated': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存已發送記錄失敗: {e}")
    
    def fetch_page(self, page_num: int = 0) -> List[Dict[str, str]]:
        """抓取指定頁面的新聞列表"""
        news_url = self.config.get('news_url', 'https://www.gcs.gov.mo/list/zh-hans/news/')
        
        if page_num == 0:
            url = news_url
        else:
            url = f"{news_url}?0-1.0-infoContent-infoTable-nextItems&nextPage={page_num}"
        
        self.logger.debug(f"正在抓取第 {page_num + 1} 頁: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            news_list = []
            
            news_items = soup.find_all('tr', class_='infiniteItem')
            
            for item in news_items:
                try:
                    h5 = item.find('h5')
                    if not h5:
                        continue
                    
                    title = h5.get_text(strip=True)
                    if not title:
                        continue
                    
                    link_tag = item.find('a', href=lambda x: x and '/detail/' in x)
                    if not link_tag:
                        continue
                    
                    href = link_tag.get('href', '')
                    if not href:
                        continue
                    
                    url = urljoin(news_url, href)
                    
                    if ';jsessionid=' in url:
                        url = url.split(';jsessionid=')[0]
                    
                    publish_time = None
                    time_tag = item.find('time', class_='render_timeago_css')
                    if time_tag and time_tag.get('datetime'):
                        try:
                            datetime_str = time_tag.get('datetime')
                            publish_time = datetime.fromisoformat(datetime_str.replace('+0800', '+08:00'))
                        except Exception as e:
                            self.logger.debug(f"解析日期失敗 {datetime_str}: {e}")
                    
                    news_list.append({
                        'title': title,
                        'url': url,
                        'publish_time': publish_time,
                        'content': None
                    })
                    
                except Exception as e:
                    self.logger.warning(f"解析新聞項失敗: {e}")
                    continue
            
            return news_list
            
        except requests.RequestException as e:
            self.logger.error(f"抓取第 {page_num + 1} 頁失敗: {e}")
            return []
        except Exception as e:
            self.logger.error(f"解析第 {page_num + 1} 頁失敗: {e}")
            return []
    
    def fetch_all_pages(self) -> List[Dict[str, str]]:
        """抓取多頁新聞列表，並過濾一天內的新聞"""
        max_pages = self.config.get('max_pages', 10)
        days_to_check = self.config.get('days_to_check', 1)
        all_news = []
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_to_check)
        
        self.logger.info(f"開始抓取最多 {max_pages} 頁新聞（只保留 {days_to_check} 天內的新聞）...")
        
        for page in range(max_pages):
            news_list = self.fetch_page(page)
            
            if not news_list:
                self.logger.info(f"第 {page + 1} 頁無新聞，停止抓取")
                break
            
            old_news_count = 0
            for news in news_list:
                if news.get('publish_time'):
                    if news['publish_time'] < cutoff_time:
                        old_news_count += 1
            
            all_news.extend(news_list)
            self.logger.info(f"第 {page + 1} 頁: {len(news_list)} 條新聞 ({old_news_count} 條超過 {days_to_check} 天)")
            
            if old_news_count >= len(news_list) * 0.8:
                self.logger.info(f"第 {page + 1} 頁大部分新聞已超過 {days_to_check} 天，停止抓取")
                break
            
            if page < max_pages - 1:
                time.sleep(1)
        
        seen = {}
        for news in all_news:
            if news['url'] not in seen:
                seen[news['url']] = news
        
        unique_news = list(seen.values())
        
        recent_news = []
        for news in unique_news:
            if news.get('publish_time'):
                if news['publish_time'] >= cutoff_time:
                    recent_news.append(news)
            else:
                recent_news.append(news)
        
        self.logger.info(f"共抓取 {len(all_news)} 條新聞，去重後 {len(unique_news)} 條，{days_to_check} 天內新聞 {len(recent_news)} 條")
        
        return recent_news
    
    def fetch_article_content(self, url: str) -> str:
        """抓取單篇新聞的內文"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            content_parts = []
            
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 20 and not text.startswith('跳至'):
                    content_parts.append(text)
            
            if not content_parts:
                main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
                if main_content:
                    content_parts.append(main_content.get_text(separator=' ', strip=True))
            
            if not content_parts:
                og_desc = soup.find('meta', property='og:description')
                if og_desc and og_desc.get('content'):
                    content_parts.append(og_desc.get('content'))
            
            content_text = ' '.join(content_parts)
            content_text = ' '.join(content_text.split())
            
            return content_text
            
        except Exception as e:
            self.logger.debug(f"抓取內文失敗 {url}: {e}")
            return ""
    
    def fetch_contents_concurrent(self, news_list: List[Dict]) -> List[Dict]:
        """併發抓取多個新聞的內文"""
        if not self.config.get('check_content', True):
            self.logger.info("配置爲不檢查內文，跳過內文抓取")
            return news_list
        
        max_workers = self.config.get('concurrent_requests', 5)
        self.logger.info(f"開始併發抓取 {len(news_list)} 條新聞內文（併發數: {max_workers}）...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_news = {
                executor.submit(self.fetch_article_content, news['url']): news
                for news in news_list
            }
            
            completed = 0
            for future in as_completed(future_to_news):
                news = future_to_news[future]
                try:
                    content = future.result()
                    news['content'] = content
                    completed += 1
                    if completed % 10 == 0:
                        self.logger.info(f"已完成 {completed}/{len(news_list)} 條")
                except Exception as e:
                    self.logger.warning(f"獲取內文失敗: {e}")
                    news['content'] = ""
        
        self.logger.info(f"內文抓取完成: {len(news_list)} 條")
        return news_list
    
    def filter_news(self, news_list: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """過濾包含關鍵詞的新聞（標題或內文）"""
        keywords = self.config.get('keywords', [])
        filtered = []
        
        for news in news_list:
            text_to_search = news['title']
            if news.get('content'):
                text_to_search += ' ' + news['content']
            
            has_keyword = any(kw.lower() in text_to_search.lower() for kw in keywords)
            
            if has_keyword and news['url'] not in self.sent_news:
                filtered.append(news)
                self.logger.info(f"發現相關新聞: {news['title']}")
            elif has_keyword and news['url'] in self.sent_news:
                self.logger.debug(f"新聞已發送過，跳過: {news['title']}")
        
        return filtered
    
    def _build_email_html(self, news_list: List[Dict[str, str]]) -> str:
        """構建 HTML 格式的郵件內容"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif; background: #f4f6f9; margin: 0; padding: 20px; }}
  .container {{ max-width: 700px; margin: 0 auto; background: #ffffff; border-radius: 10px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); overflow: hidden; }}
  .header {{ background: linear-gradient(135deg, #1a73e8, #0d47a1); padding: 24px 30px; color: #ffffff; }}
  .header h1 {{ margin: 0; font-size: 22px; font-weight: 600; }}
  .header p {{ margin: 8px 0 0; font-size: 13px; opacity: 0.85; }}
  .content {{ padding: 24px 30px; }}
  .summary {{ background: #e8f0fe; border-left: 4px solid #1a73e8; padding: 12px 16px; margin-bottom: 20px; border-radius: 0 6px 6px 0; font-size: 14px; color: #1a56b8; }}
  .news-item {{ border: 1px solid #e8eaed; border-radius: 8px; padding: 16px 20px; margin-bottom: 14px; transition: box-shadow 0.2s; }}
  .news-item:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
  .news-title {{ font-size: 16px; font-weight: 600; color: #202124; margin: 0 0 8px; }}
  .news-title a {{ color: #1a73e8; text-decoration: none; }}
  .news-title a:hover {{ text-decoration: underline; }}
  .news-preview {{ font-size: 13px; color: #5f6368; line-height: 1.6; margin: 0; }}
  .news-time {{ font-size: 12px; color: #9aa0a6; margin-top: 8px; }}
  .footer {{ padding: 16px 30px; background: #f8f9fa; border-top: 1px solid #e8eaed; text-align: center; font-size: 12px; color: #9aa0a6; }}
  .badge {{ display: inline-block; background: #e8f0fe; color: #1a73e8; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; margin-left: 8px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🔔 澳門新聞局 — 軍團菌相關新聞</h1>
    <p>監控時間: {now}</p>
  </div>
  <div class="content">
    <div class="summary">
      共發現 <strong>{len(news_list)}</strong> 條相關新聞
    </div>
"""
        
        for i, news in enumerate(news_list, 1):
            content_preview = ""
            if news.get('content'):
                content_preview = news['content'][:300]
                if len(news['content']) > 300:
                    content_preview += "..."
            
            publish_time_str = ""
            if news.get('publish_time'):
                publish_time_str = news['publish_time'].strftime('%Y-%m-%d %H:%M')
            
            html += f"""
    <div class="news-item">
      <p class="news-title">
        {i}. <a href="{news['url']}" target="_blank">{news['title']}</a>
        <span class="badge">軍團菌</span>
      </p>
      {"<p class='news-preview'>" + content_preview + "</p>" if content_preview else ""}
      {"<p class='news-time'>📅 " + publish_time_str + "</p>" if publish_time_str else ""}
    </div>
"""
        
        html += """
  </div>
  <div class="footer">
    此郵件由澳門新聞局軍團菌新聞監控系統自動發送 · 數據來源: <a href="https://www.gcs.gov.mo" style="color:#1a73e8;">澳門新聞局</a>
  </div>
</div>
</body>
</html>
"""
        return html
    
    def send_email(self, news_list: List[Dict[str, str]]) -> bool:
        """通過 Email 發送新聞通知"""
        if not news_list:
            self.logger.info("沒有需要發送的新聞")
            return True
        
        # 讀取 SMTP 配置
        smtp_server = self.config.get('smtp_server', 'smtp-mail.outlook.com')
        smtp_port = self.config.get('smtp_port', 587)
        smtp_use_ssl = self.config.get('smtp_use_ssl', False)
        smtp_username = self.config.get('smtp_username', '')
        smtp_password = self.config.get('smtp_password', '')
        email_from = self.config.get('email_from', smtp_username)
        email_to = self.config.get('email_to', [])
        subject_prefix = self.config.get('email_subject_prefix', '【澳門新聞監控】')
        
        if not smtp_username or not smtp_password:
            self.logger.error("SMTP 用戶名或密碼未配置，請在 config.json 中設置")
            return False
        
        if not email_to:
            self.logger.error("收件人未配置，請在 config.json 中設置 email_to")
            return False
        
        # 確保 email_to 是列表
        if isinstance(email_to, str):
            email_to = [email_to]
        
        # 構建郵件
        subject = f"{subject_prefix} 發現 {len(news_list)} 條軍團菌相關新聞"
        html_content = self._build_email_html(news_list)
        
        msg = MIMEMultipart('alternative')
        msg['From'] = email_from
        msg['To'] = ', '.join(email_to)
        msg['Subject'] = Header(subject, 'utf-8')
        
        # 純文本備用內容
        text_content = f"澳門新聞局軍團菌新聞監控\n\n共發現 {len(news_list)} 條相關新聞:\n\n"
        for i, news in enumerate(news_list, 1):
            text_content += f"{i}. {news['title']}\n   鏈接: {news['url']}\n\n"
        
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        # 發送郵件
        try:
            if smtp_use_ssl:
                # SSL 連接（端口 465）
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context, timeout=30) as server:
                    server.login(smtp_username, smtp_password)
                    server.sendmail(email_from, email_to, msg.as_string())
            else:
                # TLS 連接（端口 587）
                with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(smtp_username, smtp_password)
                    server.sendmail(email_from, email_to, msg.as_string())
            
            self.logger.info(f"郵件發送成功! 收件人: {', '.join(email_to)}")
            
            # 標記爲已發送
            for news in news_list:
                self.sent_news.add(news['url'])
            self._save_sent_news()
            
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"SMTP 認證失敗，請檢查用戶名和密碼: {e}")
            self.logger.error("提示: Outlook 可能需要使用應用專用密碼")
            return False
        except smtplib.SMTPException as e:
            self.logger.error(f"SMTP 發送失敗: {e}")
            return False
        except Exception as e:
            self.logger.error(f"郵件發送失敗: {e}")
            return False
    
    def run(self, test_mode: bool = False):
        """運行監控"""
        self.logger.info("=" * 80)
        self.logger.info("澳門新聞局軍團菌監控系統 (Email版) - 開始運行")
        self.logger.info("=" * 80)
        
        # 1. 抓取多頁新聞列表
        news_list = self.fetch_all_pages()
        if not news_list:
            self.logger.warning("未能獲取新聞列表")
            return
        
        # 2. 抓取新聞內文（如果配置啓用）
        if self.config.get('check_content', True):
            news_list = self.fetch_contents_concurrent(news_list)
        
        # 3. 過濾相關新聞
        filtered_news = self.filter_news(news_list)
        
        # 測試模式：只顯示結果
        if test_mode:
            self.logger.info(f"\n{'='*80}")
            self.logger.info("測試模式 - 抓取結果:")
            self.logger.info(f"總新聞數: {len(news_list)}")
            self.logger.info(f"相關新聞數: {len(filtered_news)}")
            if filtered_news:
                self.logger.info("\n相關新聞列表:")
                for i, news in enumerate(filtered_news, 1):
                    self.logger.info(f"{i}. {news['title']}")
                    self.logger.info(f"   鏈接: {news['url']}")
                    if news.get('content'):
                        preview = news['content'][:100]
                        self.logger.info(f"   預覽: {preview}...")
                    self.logger.info("")
            else:
                self.logger.info("未發現包含關鍵詞的新聞")
            self.logger.info(f"{'='*80}\n")
            self.logger.info("（測試模式不會發送郵件）")
            return
        
        # 正式模式：發送郵件
        if filtered_news:
            self.send_email(filtered_news)
            self.logger.info(f"處理完成，共發送 {len(filtered_news)} 條新聞")
        else:
            self.logger.info("未發現新的相關新聞")
            
        self.logger.info("=" * 80)


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='澳門新聞局軍團菌新聞監控系統 (Email版)')
    parser.add_argument('--test', action='store_true', help='測試模式，只顯示結果不發送郵件')
    parser.add_argument('--config', default='config.json', help='配置文件路徑')
    
    args = parser.parse_args()
    
    try:
        monitor = MacauNewsMonitorEmail(config_file=args.config)
        monitor.run(test_mode=args.test)
    except KeyboardInterrupt:
        print("\n程序已中斷")
    except Exception as e:
        print(f"程序運行錯誤: {e}")
        logging.exception("詳細錯誤信息:")
        sys.exit(1)


if __name__ == '__main__':
    main()
