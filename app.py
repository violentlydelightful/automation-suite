"""
Automation Suite - Workflow Automation Platform

A mini-Zapier that allows you to:
- Create automated workflows with triggers and actions
- Connect multiple services (Email, Slack, Webhooks, Schedules)
- Monitor execution history and logs
- Visual workflow builder
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import threading
import time
import hashlib
import uuid

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'automation-suite-dev-key')

# Configuration
DEMO_MODE = not os.getenv('SLACK_WEBHOOK_URL')

# In-memory storage (would be database in production)
workflows = {}
execution_history = []
scheduled_jobs = {}


class TriggerTypes:
    """Available trigger types."""
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"
    MANUAL = "manual"
    EMAIL = "email"


class ActionTypes:
    """Available action types."""
    SLACK = "slack"
    EMAIL = "email"
    WEBHOOK = "webhook"
    TRANSFORM = "transform"
    DELAY = "delay"
    CONDITION = "condition"
    LOG = "log"


class Workflow:
    """Represents an automation workflow."""

    def __init__(self, name: str, trigger: dict, actions: list, enabled: bool = True):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.trigger = trigger
        self.actions = actions
        self.enabled = enabled
        self.created_at = datetime.now().isoformat()
        self.run_count = 0
        self.last_run = None
        self.webhook_key = hashlib.md5(f"{self.id}{time.time()}".encode()).hexdigest()[:12]

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'trigger': self.trigger,
            'actions': self.actions,
            'enabled': self.enabled,
            'created_at': self.created_at,
            'run_count': self.run_count,
            'last_run': self.last_run,
            'webhook_url': f"/webhook/{self.webhook_key}" if self.trigger.get('type') == TriggerTypes.WEBHOOK else None
        }


class WorkflowExecutor:
    """Executes workflow actions."""

    def __init__(self):
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.sendgrid_key = os.getenv('SENDGRID_API_KEY')

    async def execute(self, workflow: Workflow, trigger_data: dict = None) -> dict:
        """Execute a workflow."""
        execution_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()
        logs = []
        context = {'trigger_data': trigger_data or {}, 'results': []}

        logs.append({
            'time': datetime.now().isoformat(),
            'level': 'info',
            'message': f'Starting workflow: {workflow.name}'
        })

        success = True
        error = None

        try:
            for i, action in enumerate(workflow.actions):
                action_type = action.get('type')
                action_config = action.get('config', {})

                logs.append({
                    'time': datetime.now().isoformat(),
                    'level': 'info',
                    'message': f'Executing action {i+1}: {action_type}'
                })

                result = await self._execute_action(action_type, action_config, context)
                context['results'].append(result)

                if result.get('error'):
                    logs.append({
                        'time': datetime.now().isoformat(),
                        'level': 'error',
                        'message': f'Action failed: {result.get("error")}'
                    })
                    if action.get('stop_on_error', True):
                        success = False
                        error = result.get('error')
                        break
                else:
                    logs.append({
                        'time': datetime.now().isoformat(),
                        'level': 'success',
                        'message': f'Action completed: {result.get("message", "OK")}'
                    })

        except Exception as e:
            success = False
            error = str(e)
            logs.append({
                'time': datetime.now().isoformat(),
                'level': 'error',
                'message': f'Execution error: {str(e)}'
            })

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logs.append({
            'time': datetime.now().isoformat(),
            'level': 'info',
            'message': f'Workflow completed in {duration:.2f}s'
        })

        # Update workflow stats
        workflow.run_count += 1
        workflow.last_run = end_time.isoformat()

        execution_record = {
            'id': execution_id,
            'workflow_id': workflow.id,
            'workflow_name': workflow.name,
            'trigger_data': trigger_data,
            'started_at': start_time.isoformat(),
            'completed_at': end_time.isoformat(),
            'duration': duration,
            'success': success,
            'error': error,
            'logs': logs,
            'demo_mode': DEMO_MODE
        }

        execution_history.insert(0, execution_record)
        if len(execution_history) > 100:
            execution_history.pop()

        return execution_record

    async def _execute_action(self, action_type: str, config: dict, context: dict) -> dict:
        """Execute a single action."""
        if DEMO_MODE:
            return self._demo_action(action_type, config, context)

        if action_type == ActionTypes.SLACK:
            return await self._send_slack(config, context)
        elif action_type == ActionTypes.WEBHOOK:
            return await self._call_webhook(config, context)
        elif action_type == ActionTypes.DELAY:
            return await self._delay(config)
        elif action_type == ActionTypes.TRANSFORM:
            return self._transform(config, context)
        elif action_type == ActionTypes.LOG:
            return self._log(config, context)
        elif action_type == ActionTypes.CONDITION:
            return self._check_condition(config, context)
        else:
            return {'error': f'Unknown action type: {action_type}'}

    async def _send_slack(self, config: dict, context: dict) -> dict:
        """Send a Slack message."""
        message = self._interpolate(config.get('message', 'Automation triggered'), context)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    self.slack_webhook,
                    json={'text': message}
                ) as resp:
                    if resp.status == 200:
                        return {'message': 'Slack message sent'}
                    else:
                        return {'error': f'Slack error: {resp.status}'}
            except Exception as e:
                return {'error': f'Slack error: {str(e)}'}

    async def _call_webhook(self, config: dict, context: dict) -> dict:
        """Call an external webhook."""
        url = config.get('url')
        method = config.get('method', 'POST').upper()
        payload = config.get('payload', {})

        # Interpolate variables
        for key, value in payload.items():
            if isinstance(value, str):
                payload[key] = self._interpolate(value, context)

        async with aiohttp.ClientSession() as session:
            try:
                if method == 'GET':
                    async with session.get(url) as resp:
                        return {'message': f'Webhook called: {resp.status}'}
                else:
                    async with session.post(url, json=payload) as resp:
                        return {'message': f'Webhook called: {resp.status}'}
            except Exception as e:
                return {'error': f'Webhook error: {str(e)}'}

    async def _delay(self, config: dict) -> dict:
        """Delay execution."""
        seconds = config.get('seconds', 1)
        await asyncio.sleep(min(seconds, 10))  # Cap at 10 seconds
        return {'message': f'Delayed {seconds}s'}

    def _transform(self, config: dict, context: dict) -> dict:
        """Transform data."""
        operation = config.get('operation', 'uppercase')
        field = config.get('field', '')
        value = context.get('trigger_data', {}).get(field, '')

        if operation == 'uppercase':
            result = str(value).upper()
        elif operation == 'lowercase':
            result = str(value).lower()
        elif operation == 'extract':
            result = value
        else:
            result = value

        context['transformed'] = result
        return {'message': f'Transformed: {result}', 'value': result}

    def _log(self, config: dict, context: dict) -> dict:
        """Log a message."""
        message = self._interpolate(config.get('message', 'Log'), context)
        return {'message': f'Logged: {message}'}

    def _check_condition(self, config: dict, context: dict) -> dict:
        """Check a condition."""
        field = config.get('field', '')
        operator = config.get('operator', 'equals')
        value = config.get('value', '')
        actual = context.get('trigger_data', {}).get(field, '')

        passed = False
        if operator == 'equals':
            passed = str(actual) == str(value)
        elif operator == 'contains':
            passed = str(value) in str(actual)
        elif operator == 'not_empty':
            passed = bool(actual)

        return {'message': f'Condition {"passed" if passed else "failed"}', 'passed': passed}

    def _interpolate(self, template: str, context: dict) -> str:
        """Interpolate variables in template."""
        result = template
        trigger_data = context.get('trigger_data', {})
        for key, value in trigger_data.items():
            result = result.replace(f'{{{{{key}}}}}', str(value))
        return result

    def _demo_action(self, action_type: str, config: dict, context: dict) -> dict:
        """Simulate action execution for demo mode."""
        time.sleep(0.3)  # Simulate processing time
        demos = {
            ActionTypes.SLACK: {'message': 'Slack message sent (demo)'},
            ActionTypes.EMAIL: {'message': 'Email sent (demo)'},
            ActionTypes.WEBHOOK: {'message': 'Webhook called (demo)'},
            ActionTypes.TRANSFORM: {'message': 'Data transformed (demo)', 'value': 'TRANSFORMED_VALUE'},
            ActionTypes.DELAY: {'message': f'Delayed {config.get("seconds", 1)}s (demo)'},
            ActionTypes.CONDITION: {'message': 'Condition passed (demo)', 'passed': True},
            ActionTypes.LOG: {'message': f'Logged: {config.get("message", "Log")} (demo)'},
        }
        return demos.get(action_type, {'message': f'{action_type} executed (demo)'})


# Initialize executor
executor = WorkflowExecutor()


# Routes
@app.route('/')
def index():
    """Main dashboard."""
    return render_template('index.html', demo_mode=DEMO_MODE)


@app.route('/api/workflows', methods=['GET'])
def list_workflows():
    """List all workflows."""
    return jsonify([w.to_dict() for w in workflows.values()])


@app.route('/api/workflows', methods=['POST'])
def create_workflow():
    """Create a new workflow."""
    data = request.get_json()

    workflow = Workflow(
        name=data.get('name', 'Untitled Workflow'),
        trigger=data.get('trigger', {'type': TriggerTypes.MANUAL}),
        actions=data.get('actions', [])
    )

    workflows[workflow.id] = workflow
    return jsonify(workflow.to_dict()), 201


@app.route('/api/workflows/<workflow_id>', methods=['GET'])
def get_workflow(workflow_id):
    """Get a specific workflow."""
    workflow = workflows.get(workflow_id)
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404
    return jsonify(workflow.to_dict())


@app.route('/api/workflows/<workflow_id>', methods=['DELETE'])
def delete_workflow(workflow_id):
    """Delete a workflow."""
    if workflow_id in workflows:
        del workflows[workflow_id]
        return jsonify({'message': 'Deleted'})
    return jsonify({'error': 'Workflow not found'}), 404


@app.route('/api/workflows/<workflow_id>/toggle', methods=['POST'])
def toggle_workflow(workflow_id):
    """Toggle workflow enabled/disabled."""
    workflow = workflows.get(workflow_id)
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404
    workflow.enabled = not workflow.enabled
    return jsonify(workflow.to_dict())


@app.route('/api/workflows/<workflow_id>/run', methods=['POST'])
def run_workflow(workflow_id):
    """Manually run a workflow."""
    workflow = workflows.get(workflow_id)
    if not workflow:
        return jsonify({'error': 'Workflow not found'}), 404

    trigger_data = request.get_json() or {}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(executor.execute(workflow, trigger_data))
    finally:
        loop.close()

    return jsonify(result)


@app.route('/webhook/<key>', methods=['POST', 'GET'])
def webhook_trigger(key):
    """Handle webhook triggers."""
    # Find workflow with this webhook key
    workflow = None
    for w in workflows.values():
        if w.webhook_key == key:
            workflow = w
            break

    if not workflow:
        return jsonify({'error': 'Webhook not found'}), 404

    if not workflow.enabled:
        return jsonify({'error': 'Workflow disabled'}), 400

    trigger_data = request.get_json() if request.is_json else dict(request.args)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(executor.execute(workflow, trigger_data))
    finally:
        loop.close()

    return jsonify({'message': 'Workflow triggered', 'execution_id': result['id']})


@app.route('/api/history')
def get_history():
    """Get execution history."""
    limit = request.args.get('limit', 20, type=int)
    return jsonify(execution_history[:limit])


@app.route('/api/templates')
def get_templates():
    """Get workflow templates."""
    templates = [
        {
            'id': 'slack-notify',
            'name': 'Slack Notification',
            'description': 'Send a Slack message when triggered',
            'trigger': {'type': TriggerTypes.WEBHOOK},
            'actions': [
                {'type': ActionTypes.SLACK, 'config': {'message': 'Workflow triggered: {{event}}'}}
            ]
        },
        {
            'id': 'webhook-chain',
            'name': 'Webhook Chain',
            'description': 'Call an external API when triggered',
            'trigger': {'type': TriggerTypes.WEBHOOK},
            'actions': [
                {'type': ActionTypes.LOG, 'config': {'message': 'Received: {{data}}'}},
                {'type': ActionTypes.WEBHOOK, 'config': {'url': 'https://httpbin.org/post', 'method': 'POST'}}
            ]
        },
        {
            'id': 'data-processor',
            'name': 'Data Processor',
            'description': 'Transform and log data',
            'trigger': {'type': TriggerTypes.MANUAL},
            'actions': [
                {'type': ActionTypes.TRANSFORM, 'config': {'operation': 'uppercase', 'field': 'message'}},
                {'type': ActionTypes.LOG, 'config': {'message': 'Processed: {{message}}'}}
            ]
        },
        {
            'id': 'conditional-flow',
            'name': 'Conditional Flow',
            'description': 'Execute actions based on conditions',
            'trigger': {'type': TriggerTypes.WEBHOOK},
            'actions': [
                {'type': ActionTypes.CONDITION, 'config': {'field': 'priority', 'operator': 'equals', 'value': 'high'}},
                {'type': ActionTypes.SLACK, 'config': {'message': '🚨 High priority: {{message}}'}}
            ]
        }
    ]
    return jsonify(templates)


@app.route('/api/status')
def status():
    """API status."""
    return jsonify({
        'status': 'operational',
        'demo_mode': DEMO_MODE,
        'workflows_count': len(workflows),
        'executions_today': len([e for e in execution_history
                                  if e['started_at'][:10] == datetime.now().strftime('%Y-%m-%d')])
    })


# Create some demo workflows on startup
def create_demo_workflows():
    demo_workflows = [
        Workflow(
            name="Welcome Notification",
            trigger={'type': TriggerTypes.WEBHOOK},
            actions=[
                {'type': ActionTypes.LOG, 'config': {'message': 'New signup: {{email}}'}},
                {'type': ActionTypes.SLACK, 'config': {'message': '👋 New user signed up: {{email}}'}}
            ]
        ),
        Workflow(
            name="Data Pipeline",
            trigger={'type': TriggerTypes.WEBHOOK},
            actions=[
                {'type': ActionTypes.TRANSFORM, 'config': {'operation': 'uppercase', 'field': 'name'}},
                {'type': ActionTypes.DELAY, 'config': {'seconds': 1}},
                {'type': ActionTypes.WEBHOOK, 'config': {'url': 'https://httpbin.org/post'}}
            ]
        ),
        Workflow(
            name="Alert System",
            trigger={'type': TriggerTypes.MANUAL},
            actions=[
                {'type': ActionTypes.CONDITION, 'config': {'field': 'severity', 'operator': 'equals', 'value': 'critical'}},
                {'type': ActionTypes.SLACK, 'config': {'message': '🚨 CRITICAL: {{message}}'}}
            ]
        )
    ]

    for w in demo_workflows:
        workflows[w.id] = w


create_demo_workflows()


if __name__ == '__main__':
    print("\n" + "="*50)
    print("⚡ Automation Suite")
    print("="*50)
    if DEMO_MODE:
        print("⚠️  Running in DEMO MODE")
        print("   Add SLACK_WEBHOOK_URL to .env for live actions")
    else:
        print("✅ Live mode enabled")
    print(f"\n🌐 Open http://localhost:5016")
    print("="*50 + "\n")

    app.run(debug=True, port=5016)
