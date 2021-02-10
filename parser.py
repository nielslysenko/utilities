import argparse
from datetime import datetime

class Parser:
    def parseOptions():
        parser = argparse.ArgumentParser()
        parser.add_argument("date", type=lambda s: datetime.strptime(s, '%Y-%m-%d'), help="Example: 2020-12-20")
        args = parser.parse_args()
        return args.date
