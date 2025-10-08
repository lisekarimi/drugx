# 💊 DrugX Failed Lookups Monitoring Workflow

The "Failed Lookups n8n workflow" monitors the DrugX application for drug lookup failures across multiple APIs (RxNorm, PubChem, DDInter, OpenFDA) and sends automated summary reports via Telegram. This workflow is located in the `monitoring` folder and requires n8n to be installed and running to function.

![n8n Workflow](https://github.com/lisekarimi/drugx/blob/main/assets/img/n8n.png?raw=true)

## ⚙️ Workflow Components

### 1. Schedule Trigger
- **Frequency**: Every 3 days at 5:00 PM
- **Purpose**: Initiates the monitoring cycle

### 2. Gmail Reader
- **Source**: Reads failure notification emails from `sender@yourdomain.com`
- **Filter**: Subject contains "DrugX Alert"
- **Time Range**: Past 3 days (using `{{DateTime.now().minus({days: 3}).toISO()}}`)
- **Output**: Raw email data with subjects and snippets

### 3. Parse DrugX Failures (Function Node)
- **Input**: Gmail email data
- **Processing**:
  - Extracts drug names from email subjects
  - Identifies failure sources from email snippets
  - Aggregates failures by API source
  - Creates formatted strings for notification
- **Output**: Structured data with totals, summaries, and formatted lists

### 4. Send DrugX Summary Alert (Telegram)
- **Recipient**: Your configured Telegram chat
- **Content**:
  - Total failure count
  - Specific drugs and their failure sources
  - Summary breakdown by API
  - Next monitoring schedule

## 🔧 Setup Requirements

### Environment Variables
```
RESEND_API_KEY=your_resend_key
RESEND_FROM_EMAIL=sender@yourdomain.com
MONITORING_EMAIL=recipient@recipient.com
```

### Prerequisites
1. **Gmail OAuth**: Configure Gmail API access in n8n
2. **Telegram Bot**: Create bot with @BotFather and get your chat ID
3. **Resend Account**: For sending failure notifications from DrugX app

## 💡 Sample Output
```
🚨 DrugX Monitoring Summary
📅 Period: Past 3 days
📊 Total Failures: 2

📋 Failed Drug Lookups:
• invaliddrugname123 (pubchem) - 2025-09-19
• invaliddrugname123 (rxnorm_pubchem) - 2025-09-19

📊 Summary by Source:
• pubchem: 1 failures
• rxnorm_pubchem: 1 failures

⏰ Next summary in 3 days
```

## 🧩 Benefits
- **Proactive Monitoring**: Know when drugs fail lookup without checking logs
- **Actionable Intelligence**: See exactly which drugs and APIs are failing
- **Database Improvement**: Identify missing drugs to add to your database
- **API Health**: Monitor which external APIs are causing issues
- **Cost Optimization**: Track patterns to optimize API usage

## 🎨 Customization
- **Frequency**: Adjust "Days Between Triggers" (1 for daily, 7 for weekly)
- **Time**: Change "Trigger at Hour" for different notification times
- **Recipients**: Add multiple Telegram chats or switch to email/Slack
- **Filters**: Modify Gmail filters for different alert types

## 🛠️ Troubleshooting
- Ensure Gmail OAuth permissions include read access
- Verify Telegram bot token and chat ID
- Check that DrugX app is sending emails to the monitored address
- Test with manual workflow execution before relying on schedule
