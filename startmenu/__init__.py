import sys
from .application import StartApplication


def main() -> None:
    app = StartApplication()
    sys.exit(app.run(sys.argv))
