import argparse
import datetime
from dateutil import parser as dateutil_parser
import json
import re

from datetime import datetime, date
import locale

def fail_silently(func):
    def wrapper(row, *args, **kwargs):
        try:
            func(row, *args, **kwargs)
        except Exception as e:
            # TODO log?
            print(json.dumps(str(e)))
            print(json.dumps(row))
            pass
    return wrapper

def parse_date(s):
    MONTHS = {
        "ינו": "Jan",
        "מרץ": "Mar",
        "אפר": "Apr",
        "מאי": "May",
        "יונ": "Jun",
    }
    for mon,sub in MONTHS.items():
        s = re.sub(r"\b"+re.escape(mon)+r"\b", sub, s)
    s = re.sub("[א-ת]{3} \d+","",s)
    s = re.sub("[א-ת]+","",s)
    return dateutil_parser.parse(s)

def extract_date(row, postfix, hour_prefix, date_prefix, is_start:bool):
    if re.match("[a-zA-Z]+",postfix):
        date_postfix = f"{postfix} {date_prefix}"
        hour_postfix = f"{postfix} {hour_prefix}"
    else:
        date_postfix = f"{date_prefix} {postfix}"
        hour_postfix = f"{hour_prefix} {postfix}"

    bare = row.get(postfix)
    date = row.get(f"{date_prefix} ") or row.get(date_prefix) or row.get(date_postfix)
    hour = row.get(hour_postfix)

    if hour and len(hour) > 10:
        return parse_date(hour)
    if hour and date:
        date = date.replace("00:00:00","")
        return parse_date(f"{hour} {date}")
    if bare and date:
        date = date.replace("00:00:00","")
        return parse_date(f"{bare} {date}")
    if bare:
        return parse_date(bare)
    if date:
        return parse_date(date)
    return None


@fail_silently
def start_value(row):
    res = (
        extract_date(row, postfix="Start", hour_prefix="Time", date_prefix="Date", is_start=True) or
        extract_date(row, postfix="התחלה", hour_prefix="שעת", date_prefix="תאריך", is_start=True) or
        extract_date(row, postfix="תאריך ושעת התחלה", hour_prefix="", date_prefix="", is_start=True)
    )
    assert res



@fail_silently
def end_value(row):
    pass

######################3

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_filename", type=argparse.FileType('r'))
    return parser.parse_args()

def parse_row(row):
    # Skipping troublesome cals
    if list(row.keys()) == ['resource_id']:
        return 
    if len(row.keys()) < 4:
        return
    if row['resource_id'] in [
        '1e2c3348-aed3-4749-9a92-db95d915ee02',
        '2f003499-2843-4849-a734-26b42b4962d6',
        '59904c98-8e28-410b-b7fd-5e5cdd28a658',
        '64eefcdd-63a8-4c75-9d8b-a77a65b6cd84',
        '4ad91d4a-e1d0-47b0-a26e-f7a2dcb77761',
        '95cde5e1-2c78-45ad-baec-1afe22baa40f',
    ]:
        return
    """
    # Debuggin
    if not row['resource_id'] == '937b6514-559f-42a6-89d2-8ac2993d7bae':
        return
    """

    # Fixing typos
    new_row = {}
    for k,v in row.items():
        k = k.replace("התחילה", "התחלה")
        new_row[k]=v
    row=new_row

    dic = {
        'start': start_value(row),
        # 'end': end_value(row),
    }

    """
    if any((v is None for v in dic.values())):
        print(row, dic)
    """

def main():
    args = parse_args()
    for row_raw in args.raw_filename:
        row = json.loads(row_raw)
        parse_row(row)

main()