"""Agent–admin connection configuration."""

# Reconnection: exponential backoff between connect attempts
RECONNECT_DELAY_INITIAL_S = 2.0
RECONNECT_DELAY_MAX_S = 120.0
RECONNECT_BACKOFF_FACTOR = 1.5

# Request timeout for bootstrap (get_config, etc.)
REQUEST_TIMEOUT_S = 15.0

# Register handshake: max time to wait for "registered" response
REGISTER_TIMEOUT_S = 30.0

# Heartbeat: minimum interval (admin may send config with different value)
HEARTBEAT_INTERVAL_MIN_S = 10

# Delay before starting background software reinstall (let connection establish first)
SOFTWARE_REINSTALL_DELAY_S = 2.0
