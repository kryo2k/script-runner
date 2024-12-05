# Script Runner

Simplifies the process of running backend scripts manually from a web interface.

# Installation

## Prerequisites

- Python 3+ (+venv)
- Make

## Setup python virtual environment

```
make venv
```

## Activate python virtual environment

```
source venv/bin/activate
```

# Configuration

## Environment Variables

| Variable             | Default             | Description                                                                      |
| -------------------- | ------------------- | -------------------------------------------------------------------------------- |
| LOCALE               | en_US               | Controls what locale is used across the app.                                     |
| TIMEZONE             | US/Eastern          | Controls what timezone to use when a date+time is displayed.                     |
| AUTH_ENABLED         | 1                   | Controls if authentication is required.                                          |
| AUTH_FILE            | .script-runner-auth | File to use for authentication. File should be in username:password line format. |
| EXECUTION_INTEPRETOR | /bin/sh             | Script interepreter to use for execution.                                        |
| EXECUTION_SCRIPT     | None                | File path of script to execute. **This is required to work correctly.**          |
| EXECUTION_USER       | current-user        | Determines what user runs the script. Requires sudo privilege.                   |
| INDEX_TITLE          | Home                | Displayed in the main page header.                                               |

# Launch in debug mode (non-wsgi)

This **should not** be used in production.

```
flask --app path/to/script-runner run \
 -h localhost \
 -p 3000 \
 --debug
```

# Launch in production mode

### Gunicorn

```
pip install gunicorn eventlet
gunicorn -b localhost:3000 --worker-class eventlet -w 1 --chdir /path/to script-runner:app
```

Flask SocketIO does not appear to support multiple workers in gunicorn.