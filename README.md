# Automation Suite

A workflow automation platform (like a mini-Zapier) that lets you create, manage, and execute automated workflows with triggers and actions.

## What It Does

- **Visual Workflow Builder**: Create automations without code
- **Multiple Trigger Types**: Webhooks, manual triggers, schedules (coming soon)
- **Chainable Actions**: Slack, webhooks, data transforms, conditions, delays
- **Execution Monitoring**: Full logs and history for every run
- **Demo Mode**: Works without any integrations configured

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Automation Suite                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    Triggers                              │   │
│   │   ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│   │   │ Webhook  │  │  Manual  │  │ Schedule │              │   │
│   │   │   🔗     │  │    👆    │  │    ⏰    │              │   │
│   │   └────┬─────┘  └────┬─────┘  └────┬─────┘              │   │
│   │        └─────────────┼─────────────┘                     │   │
│   └──────────────────────┼──────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              Workflow Executor                           │   │
│   │                                                          │   │
│   │   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐       │   │
│   │   │ 1   │ → │ 2   │ → │ 3   │ → │ 4   │ → │ N   │       │   │
│   │   └─────┘   └─────┘   └─────┘   └─────┘   └─────┘       │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼                                       │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    Actions                               │   │
│   │                                                          │   │
│   │   💬 Slack    🔗 Webhook    🔄 Transform    ⏱️ Delay     │   │
│   │   📝 Log      ❓ Condition   📧 Email                    │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### Trigger Types
- **Webhook**: Unique URL that triggers workflow on HTTP request
- **Manual**: Click-to-run from the dashboard
- **Schedule**: Time-based triggers (coming soon)

### Action Types
| Action | Description |
|--------|-------------|
| 📝 Log | Log a message (with variable interpolation) |
| 💬 Slack | Send message to Slack channel |
| 🔗 Webhook | Call external HTTP endpoint |
| 🔄 Transform | Modify data (uppercase, lowercase, extract) |
| ⏱️ Delay | Wait before next action |
| ❓ Condition | Branch based on data values |

### Variable Interpolation
Use `{{variable}}` syntax to inject trigger data into actions:
```
"Message: {{event}} from {{user}}"
```

### Execution Logging
Every workflow run is logged with:
- Start/end timestamps
- Duration
- Success/failure status
- Step-by-step logs
- Error details

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run (demo mode - no integrations needed)
python app.py

# Open http://localhost:5016
```

## Full Setup

1. Copy `.env.example` to `.env`
2. Add your integration keys:
   - [Slack Webhook](https://api.slack.com/messaging/webhooks) - For Slack notifications
   - [SendGrid](https://sendgrid.com) - For email actions (optional)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard |
| `/api/workflows` | GET | List all workflows |
| `/api/workflows` | POST | Create new workflow |
| `/api/workflows/:id` | GET | Get workflow details |
| `/api/workflows/:id` | DELETE | Delete workflow |
| `/api/workflows/:id/toggle` | POST | Enable/disable workflow |
| `/api/workflows/:id/run` | POST | Manually run workflow |
| `/webhook/:key` | POST/GET | Trigger workflow via webhook |
| `/api/history` | GET | Get execution history |
| `/api/templates` | GET | Get workflow templates |

### Create Workflow
```bash
curl -X POST http://localhost:5016/api/workflows \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Automation",
    "trigger": {"type": "webhook"},
    "actions": [
      {"type": "log", "config": {"message": "Received: {{data}}"}},
      {"type": "slack", "config": {"message": "New event: {{event}}"}}
    ]
  }'
```

### Trigger Webhook
```bash
curl -X POST http://localhost:5016/webhook/abc123 \
  -H "Content-Type: application/json" \
  -d '{"event": "user_signup", "email": "user@example.com"}'
```

## Workflow Templates

Pre-built templates to get started quickly:
- **Slack Notification**: Send Slack message on webhook
- **Webhook Chain**: Forward data to another API
- **Data Processor**: Transform and log incoming data
- **Conditional Flow**: Branch based on data values

## Tech Stack

- **Backend**: Python, Flask, aiohttp (async execution)
- **Integrations**: Slack, HTTP webhooks
- **Frontend**: Vanilla JS with visual workflow builder
- **Storage**: In-memory (would use database in production)

## Why This Matters

This project demonstrates:
1. **Event-driven architecture** - Trigger-action workflow patterns
2. **Async execution** - Non-blocking action chains
3. **Visual automation builders** - No-code interface design
4. **Integration patterns** - Connecting multiple services
5. **Execution monitoring** - Observability and logging

---

*Automate the boring stuff.*
