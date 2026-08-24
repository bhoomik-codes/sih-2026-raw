"""
conftest.py
-----------
Root pytest configuration.

Adding this file at the project root makes pytest add the root to sys.path
automatically, so all absolute imports (apps.edge.*, cv.detection.*, etc.)
resolve correctly without any sys.path manipulation in test files.
"""
