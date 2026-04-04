"""
Entry point for running mathclaw as a module: python -m mathclaw
"""

from .cli.commands import app

if __name__ == "__main__":
    app()
