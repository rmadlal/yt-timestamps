import argparse
import requests
import logging
import traceback
from collections import namedtuple
from datetime import timedelta
from functools import partial, reduce
from operator import attrgetter
from typing import List


DISCOGS_SEARCH = 'https://api.discogs.com/database/search'
TOKEN = 'hAzLxILnlVAkXByQddbJcvsaYnmjytIXnuxzfYHm'
DEBUG = False

Track = namedtuple('Track', ['position', 'title', 'time'])  # time is first duration, then timestamp

logging.basicConfig(format='%(levelname)s\t%(funcName)s\t%(lineno)d\t%(message)s', level=logging.DEBUG)


def str_to_timedelta(duration: str) -> timedelta:
    time_parts = list(map(int, duration.split(':')))
    return timedelta(minutes=time_parts[0], seconds=time_parts[1])


def timedelta_to_str(td: timedelta) -> str:
    s = str(td)
    if s.startswith('0:'):
        return ':'.join(s.split(':')[1:])
    return s


def get_or_empty(url: str) -> dict:
    try:
        with requests.get(url) as response:
            return response.json() if response.ok else {}
    except requests.RequestException:
        logging.error(traceback.format_exc())
        return {}


def get_tracklist_data(query: str) -> List[Track]:
    try:
        if DEBUG > 1:
            import json
            data = json.load(open('sample_timestamps.txt'))
        else:
            data = get_or_empty(f'{DISCOGS_SEARCH}?q={query}&token={TOKEN}')
            data = get_or_empty(data['results'][0]['resource_url'])
        logging.debug(data)
        return [Track(track['position'], track['title'], str_to_timedelta(track['duration']))
                for track in data['tracklist'] if track['type_'] == 'track']
    except (KeyError, ValueError, IndexError):
        logging.error(traceback.format_exc())
        return []


def durations_to_deltas(tracklist: List[Track]) -> List[Track]:
    deltas = reduce(lambda acc, curr: acc + [acc[-1] + curr], map(attrgetter('time'), tracklist), [timedelta()])
    logging.debug(deltas)
    return [track._replace(time=timestamp) for track, timestamp in zip(tracklist, deltas)]


def process_tracklist(tracklist: List[Track]) -> List[Track]:
    tracklist = sorted(tracklist, key=attrgetter('position'))
    tracklist = durations_to_deltas(tracklist)
    logging.debug(tracklist)
    return tracklist


def format_lines(tracklist: List[Track], **args) -> List[str]:
    return [(f'{args["prefix"]} ' if args["prefix"] else '')
            + (f'{position}. ' if args["numbered"] else '')
            + (timedelta_to_str(time) if args["ts_first"] else title)
            + (f' {args["separator"]} ' if args["separator"] else ' ')
            + (title if args["ts_first"] else timedelta_to_str(time))
            for position, title, time in tracklist]


def main():
    global DEBUG

    parser = argparse.ArgumentParser(description='Generate tracklist timestamps for YouTube video description')
    parser.add_argument('query', metavar='title', help='the (artist name and) album title')
    parser.add_argument('-n', '--numbered', action='store_true', help='display track numbers')
    parser.add_argument('-tf', '--ts-first', action='store_true', help='timestamp before title')
    parser.add_argument('-p', '--prefix', help='beginning of line')
    parser.add_argument('-s', '--separator', help='separator between title and timestamp')
    parser.add_argument('-o', '--output', type=partial(open, mode='w'), default=None, help='output filename')
    parser.add_argument('-d', '--debug', action='count')
    args = parser.parse_args()

    DEBUG = args.debug
    if not DEBUG:
        logging.disable(logging.DEBUG)
    logging.debug(args)

    tracklist = get_tracklist_data(args.query)
    if not tracklist:
        print('Album not found')
        return
    tracklist = process_tracklist(tracklist)

    print('\n'.join(format_lines(tracklist, **vars(args))), file=args.output)


if __name__ == '__main__':
    main()
