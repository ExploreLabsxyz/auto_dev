# Frontend Development Guide

This guide describes how to create and integrate frontend UIs for autonomous agents using auto_dev. Frontend components allow you to build web interfaces that can interact with your agents in real-time.

## Component Structure

Frontend components follow this directory structure:

```bash
packages/AUTHOR/customs/COMPONENT_NAME/
├── build
│   └── index.html
├── component.yaml
├── __init__.py
└── openapi3_spec.yaml
```

### Key Files

#### component.yaml
This file defines the frontend component and its dependencies:

```yaml
name: example_ui
author: your_name
version: 0.1.0
type: custom
description: Custom UI for interacting with an autonomous agent
license: Apache-2.0
aea_version: '>=1.0.0, <2.0.0'
api_spec: openapi3_spec.yaml
frontend_dir: build
behaviours:
  - class_name: ExampleBehaviour
    args: {}
handlers:
  - class_name: UserInterfaceHttpHandler
    args: {}
```

#### openapi3_spec.yaml
Defines the API endpoints for your frontend component:

```yaml
openapi: 3.0.0
info:
  title: Agent Frontend API
  description: API endpoints for agent interaction
  version: 0.1.0
servers:
  - url: http://0.0.0.0:5555
paths:
  /:
    get:
      summary: Returns the main HTML page
      responses:
        '200':
          description: HTML response
          content:
            text/html:
              schema:
                type: string
  /api/agent-info:
    get:
      summary: Returns the agent's state and info
      responses:
        '200':
          description: JSON response
          content:
            application/json:
              schema:
                type: object
                properties:
                  agent-status:
                    type: string
```

#### Frontend Directory (build/)
Contains your compiled frontend code. For example, a simple `index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Agent UI</title>
</head>
<body>
    <div id="root"></div>
    <script>
        // Example of API interaction
        fetch('http://localhost:5555/api/agent-info')
            .then(response => response.json())
            .then(data => {
                console.log('Agent status:', data['agent-status']);
            });
    </script>
</body>
</html>
```

## Features

### HTTP and WebSocket Support
- Generate routes from the `build` directory
- Enable API routes from the `openapi3_spec.yaml` file
- Support for both HTTP and WebSocket connections
- CORS headers handled automatically
- Background tasks support

### Real-time Communication
The frontend loader supports real-time communication between the frontend and agent through WebSockets:

#### Handlers
Handle incoming messages from the frontend:

```python
from aea.skills.base import Handler

class ExampleHandler(Handler):
    def handle(self, msg):
        """Handle incoming messages."""
        return f"Received: {msg.data}"
```

#### Behaviours
Send updates from the agent to the frontend:

```python
from aea.skills.base import Behaviour

class ExampleBehaviour(Behaviour):
    def act(self):
        """Send updates to connected clients."""
        for client in self.context.clients.values():
            self.send_message("Update", client)
```

## Configuration

Enable the frontend loader in your agent's configuration:

```yaml
public_id: valory/agent_abci:0.1.0
type: skill
models:
  params:
    args:
      user_interface:
        enabled: true
        custom_component: author/component_name
```

## Best Practices

1. **API Design**
   - Use OpenAPI 3.0 specification for clear API documentation
   - Keep endpoints RESTful and well-structured
   - Include proper error handling

2. **Real-time Updates**
   - Use WebSockets for real-time data instead of polling
   - Implement proper connection handling and reconnection logic
   - Consider message queuing for reliable delivery

3. **Frontend Structure**
   - Keep the build directory clean and optimized
   - Include only necessary assets
   - Implement proper error handling for API calls

4. **Security**
   - Implement proper input validation
   - Use secure WebSocket connections when needed
   - Follow security best practices for API endpoints
