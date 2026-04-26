# Updated __main__.py

# Importing necessary functions
from .notify import send_telegram, notify

# Other code...

# Replacing all calls to send_telegram with notify
notify(report)  # (replace this line for all instances)

# Remaining code...