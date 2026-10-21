Captured real tool schemas (`<server>.json`) go here. While a file is missing, the mock uses its built-in defaults.
After capturing, run `python -m mcp_mocks.capture_schemas --check` and add handlers for any tools the tasks need.
Tools without a handler return a "not implemented" error.
