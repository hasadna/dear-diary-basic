import argparse
import datetime
from dateutil import parser as dateutil_parser
import json
import re
import sys

from datetime import datetime, date
import locale


class ColumnFinder:
    @staticmethod
    def first_match(row, possible_keys):
        for key in possible_keys:
            key = key.strip()
            key = re.sub("\s", " ", key)
            if key in row:
                return row[key]
        return None

    @classmethod
    def start_time(cls, row):
        return cls.first_match(
            row,
            [
                "Start",
                "Start Time",
                "שעת התחלה",
                "התחלה",
                "שעה",
                "משעה",
                "תאריך ושעת התחלה",
                "מזמן",
            ],
        )

    @classmethod
    def start_date(cls, row):
        return cls.first_match(
            row, ["תאריך התחלה", "Start Date", "יום התחלה", "תאריך", "יום"]
        )

    @classmethod
    def end_time(cls, row):
        return cls.first_match(
            row,
            [
                "End",
                "End Time",
                "שעת סיום",
                "סיום",
                "סוף",
                "תאריך ושעת סיום",
            ],
        )

    @classmethod
    def end_date(cls, row):
        return cls.first_match(
            row, ["תאריך סיום", "תאריך", "תאריך ", "תאריך וסיום", "תאריך סוף"]
        )

    @classmethod
    def subject(cls, row):
        return cls.first_match(
            row,
            [
                "נושא",
                "Subject",
                "נושא הפגישה",
                "הנושא",
                "Title",
            ],
        )

    @classmethod
    def why_missing(cls, row):
        black_keys = [k for k in row.keys() if "השחרה" in k]
        if black_keys:
            return row[black_keys[0]]
        return None


def handle_errors(quiet: bool = True, allow_empties: bool = True):
    def wrapper2(func):
        def wrapper(cls, row, *args, **kwargs):
            try:
                ret = func(cls, row, *args, **kwargs)
                if not allow_empties:
                    assert ret, "No return value"
                return ret
            except Exception as e:
                # TODO log?
                if not quiet:
                    print(json.dumps(str(e)))
                    print(json.dumps(row))

        return wrapper

    return wrapper2


class ColumnParser:
    @staticmethod
    def parse_date(s):
        MONTHS = {
            "ינו": "Jan",
            "פבר": "Feb",
            "מרץ": "Mar",
            "אפר": "Apr",
            "מאי": "May",
            "יונ": "Jun",
            "יול": "Jul",
            "אוג": "Aug",
            "ספט": "Sep",
            "אוק": "Oct",
            "נוב": "Nov",
            "דצמ": "Dec",
        }
        for mon, sub in MONTHS.items():
            s = re.sub(r"\b" + re.escape(mon) + r"\b", sub, s)
        s = re.sub("[א-ת]{3} \d+", "", s)
        s = re.sub("[א-ת]+", "", s)
        return dateutil_parser.parse(s)

    @classmethod
    @handle_errors(quiet=True)
    def start_value(cls, row):
        start_time = ColumnFinder.start_time(row)
        start_date = ColumnFinder.start_date(row)

        # Date being xx-xx/xx/xx
        if start_date and start_date.count("-") == 1:
            start_block, end_block = start_date.split("-")
            start_date = start_block + end_block[len(start_block) :]

        if start_date and re.match(r"\*+", start_date):
            end_date = ColumnFinder.end_date(row)
            start_date = re.sub("\d{2}:\d{2}:\d{2}", "", end_date)

        if start_time and len(start_time) > 10:
            return cls.parse_date(start_time)
        if start_time and start_date:
            start_date = start_date.replace("00:00:00", "")
            return cls.parse_date(f"{start_time} {start_date}")
        return None

    @classmethod
    @handle_errors(quiet=False, allow_empties=True)
    def end_value(cls, row):
        end_time = ColumnFinder.end_time(row)
        end_date = ColumnFinder.end_date(row)

        if end_time and not end_date and (start_date := ColumnFinder.start_date(row)):
            start_date = start_date.replace("00:00:00", "")
            end_date = start_date

        # Date being xx-xx/xx/xx
        if end_date and end_date.count("-") == 1:
            start_block, end_block = end_date.split("-")
            end_date = end_block

        if end_time and len(end_time) > 10:
            return cls.parse_date(end_time)
        if end_time and end_date:
            end_time = end_time.replace("00:00:00", "")
            return cls.parse_date(f"{end_time} {end_date}")
        if not end_time and end_date:
            return cls.parse_date(end_date)

        return None

    @classmethod
    @handle_errors(quiet=False, allow_empties=True)
    def subject(cls, row):
        subject = ColumnFinder.subject(row)
        if subject:
            return subject
        why_missing = ColumnFinder.why_missing(row)
        if why_missing:
            # TODO report reason
            return "CENSORED"
        return None


class RowParser:
    @staticmethod
    def parse_row(row):
        return {
            "reource_id": row["resource_id"],
            "start": str(ColumnParser.start_value(row)),
            "end": str(ColumnParser.end_value(row)),
            "subject": ColumnParser.subject(row),
        }


@handle_errors
def end_value(row):
    res = (
        extract_date(
            row, postfix="End", hour_prefix="Time", date_prefix="Date", is_start=False
        )
        or extract_date(
            row, postfix="סיום", hour_prefix="שעת", date_prefix="תאריך", is_start=False
        )
        or extract_date(
            row, postfix="סוף", hour_prefix="שעת", date_prefix="תאריך", is_start=False
        )
        or extract_date(
            row,
            postfix="סוף",
            hour_prefix="שעת",
            date_prefix="תאריך התחלה",
            is_start=False,
        )
        or None
    )
    assert res
    return res


######################3


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_filename", type=argparse.FileType("r"))
    parser.add_argument(
        "-o", "--output", type=argparse.FileType("w"), default=sys.stdout
    )
    return parser.parse_args()


def parse_row(row):
    # Skipping troublesome cals
    if list(row.keys()) == ["resource_id"]:
        return
    if len(row.keys()) < 4:
        return
    if row["resource_id"] in [
        "1e2c3348-aed3-4749-9a92-db95d915ee02",
        "2f003499-2843-4849-a734-26b42b4962d6",
        "59904c98-8e28-410b-b7fd-5e5cdd28a658",
        "64eefcdd-63a8-4c75-9d8b-a77a65b6cd84",
        "4ad91d4a-e1d0-47b0-a26e-f7a2dcb77761",
        "95cde5e1-2c78-45ad-baec-1afe22baa40f",
        "b903d50e-b58f-4c41-8d0f-664a621caeee",
    ]:
        return

    # Fixing typos
    new_row = {}
    for k, v in row.items():
        k = k.replace("התחילה", "התחלה")
        new_row[k] = v
    row = new_row

    dic = RowParser.parse_row(row)

    if any((not v for v in dic.values())):
        return None

    return dic


def main():
    args = parse_args()
    for row_raw in args.raw_filename:
        row = json.loads(row_raw)
        res = parse_row(row)
        if res:
            print(json.dumps(res), file=args.output)


main()
