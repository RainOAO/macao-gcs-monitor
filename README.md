# 澳門新聞局新聞監控系統

自動監控澳門新聞局網站，**抓取一天內所有新聞**，檢查**標題和內文**中是否提及指定詞，並通過 **Email** 推送通知。


## 快速開始

### 第一步：安裝環境

```
setup_env.bat
```

### 第二步：取得 Gmail 應用專用密碼

1. 登入 [Google 帳戶](https://myaccount.google.com/)
2. 進入 **安全性** → 確保已開啟 **兩步驟驗證**
3. 存取 [應用專用密碼頁面](https://myaccount.google.com/apppasswords)
4. 建立應用密碼，複製 **16 位密碼**

### 第三步：編輯配置文件 `config.json`

```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_username": "你的Gmail地址@gmail.com",
  "smtp_password": "你的16位應用專用密碼",
  "email_from": "你的Gmail地址@gmail.com",
  "email_to": ["收件人郵箱@example.com"]
}
```

### 第四步：測試郵件發送

```
venv\Scripts\python.exe test_email.py
```

收到測試郵件 → 繼續下一步

### 第五步：測試運行

```
run.bat --test
```

- 抓取多頁新聞並分析內文
- 顯示包含關鍵詞的新聞
- **不會**發送郵件

### 第六步：正式運行

```
run.bat
```

### 第七步：設置定時任務（可選）

```
setup_task.bat
```

每天 09:00 自動運行。

---

##  完整配置說明

| 參數                   | 說明                          | 預設值             |
| ---------------------- | ----------------------------- | ------------------ |
| `smtp_server`          | SMTP 伺服器                   | `smtp.gmail.com`   |
| `smtp_port`            | SMTP 端口                     | `587`              |
| `smtp_use_ssl`         | 使用 SSL（端口465時設為true） | `false`            |
| `smtp_username`        | 發件人帳號                    | 必填               |
| `smtp_password`        | 應用專用密碼                  | 必填               |
| `email_from`           | 發件人地址                    | 必填               |
| `email_to`             | 收件人列表（支援多個）        | 必填               |
| `email_subject_prefix` | 郵件標題前綴                  | `【澳門新聞監控】` |
| `keywords`             | 監控關鍵詞列表                | 軍團菌相關         |
| `max_pages`            | 最多抓取頁數                  | `10`               |
| `days_to_check`        | 檢查最近幾天                  | `2`                |
| `check_content`        | 是否檢查內文                  | `true`             |
| `concurrent_requests`  | 併發線程數                    | `5`                |

### 其他郵箱 SMTP 設定

| 郵箱服務 | smtp_server    | smtp_port | smtp_use_ssl |
| -------- | -------------- | --------- | ------------ |
| Gmail    | smtp.gmail.com | 587       | false        |
| QQ 郵箱  | smtp.qq.com    | 587       | false        |
| 163 郵箱 | smtp.163.com   | 465       | true         |

---

##  專案結構

```
plugin-email/
├── macau_news_monitor.py   # 核心監控程式
├── config.json             # 配置文件
├── run.bat                 # 運行腳本
├── setup_task.bat          # 定時任務設置
├── setup_env.bat           # 環境安裝
├── test_email.py           # 郵件發送測試
├── requirements.txt        # Python 依賴
├── .gitignore              # Git 忽略
├── README.md               # 本文檔
├── sent_news.json          # 已推送記錄（自動生成）
└── macau_news_monitor.log  # 運行日誌（自動生成）
```

---

**最後更新**: 2026-02-14

