import argparse
import logging
import requests
from datetime import timedelta
from dataclasses import dataclass, astuple
from functools import partial
from typing import List

DISCOGS_SEARCH = 'https://api.discogs.com/database/search'
TOKEN = open('token.txt').read()
DEBUG = 0

logging.basicConfig(format='%(asctime)s\t%(levelname)s\t%(filename)s\t%(lineno)d\t%(message)s', level=logging.DEBUG)


class Timestamp(object):
    """ Wrapper on timedelta, for customized str conversions """

    def __init__(self, *args, **kwargs):
        self._td = timedelta(*args, **kwargs)

    def __add__(self, other: 'Timestamp') -> 'Timestamp':
        ts = Timestamp()
        ts._td = self._td + other._td
        return ts

    def __repr__(self) -> str:
        return f'{self.__class__.__qualname__}({repr(self._td)})'

    def __str__(self) -> str:
        minute = 60
        hour = minute ** 2

        remainder = int(self._td.total_seconds())
        hours = remainder // hour
        remainder %= hour
        minutes = remainder // minute
        remainder %= minute
        seconds = remainder

        if hours:
            return f'{hours}:{minutes:02}:{seconds:02}'
        return f'{minutes}:{seconds:02}'

    @staticmethod
    def from_str(duration: str) -> 'Timestamp':
        parts = duration.split(':')
        if not (duration and 0 < len(parts) <= 3):
            raise ValueError(f'Invalid duration: "{duration}"')
        if len(parts) == 3:
            return Timestamp(hours=int(parts[0]), minutes=int(parts[1]), seconds=int(parts[2]))
        if len(parts) == 2:
            return Timestamp(minutes=int(parts[0]), seconds=int(parts[1]))
        return Timestamp(seconds=int(parts[0]))


@dataclass
class Track:
    position: str
    title: str
    time: Timestamp

    def __iter__(self):
        """ Allows us to unpack (e.g: `position, title, time = track`) """
        yield from astuple(self)


def httpget(url: str) -> dict:
    return requests.get(url).json()


def durations_to_timestamps(tracklist: List[Track]) -> None:
    acc_durations = Timestamp()
    for track in tracklist:
        duration = track.time
        track.time = acc_durations
        acc_durations += duration


def get_tracklist_data(query: str) -> List[Track]:
    try:
        if DEBUG > 1:
            import json
            tracklist = json.load(open('sample_tracklist.txt'))
        else:
            results = httpget(f'{DISCOGS_SEARCH}?q={query}&type=release&token={TOKEN}')['results']
            # release = next(filter(lambda result: result['type'] == 'release', results), {})
            if not results:
                logging.error(f'Album not found: "{query}"')
                return []
            release = results[0]
            logging.info(f'Generating tracklist for "{release["title"]}"')
            tracklist = httpget(release['resource_url'])['tracklist']

        logging.debug(tracklist)
        tracklist = [Track(track['position'], track['title'], Timestamp.from_str(track['duration']))
                     for track in tracklist if track['type_'] == 'track']
        durations_to_timestamps(tracklist)
        return tracklist

    except (KeyError, ValueError, IndexError, requests.RequestException):
        logging.exception(f'Error getting tracklist for "{query}"')
        return []


def format_lines(tracklist: List[Track], **args) -> List[str]:
    def format_timestamp(timestamp: Timestamp):
        open_parens = ('(', '[', '{', '<')
        close_parens = (')', ']', '}', '>')
        paren = args['parentheses']
        if not paren:
            return str(timestamp)
        return f'{paren}{str(timestamp)}{close_parens[open_parens.index(paren)]}'

    return [(f"{args['prefix']} " if args['prefix'] else '')
            + (f'{position}. ' if args['numbered'] else '')
            + (format_timestamp(time) if args['ts_first'] else title)
            + (f" {args['separator']} " if args['separator'] else ' ')
            + (title if args['ts_first'] else format_timestamp(time))
            for position, title, time in tracklist]


def main():
    global DEBUG

    parser = argparse.ArgumentParser(description='Generate tracklist timestamps for YouTube video description')
    parser.add_argument('query', metavar='title', help='the (artist name and) album title')
    parser.add_argument('-n', '--numbered', action='store_true', help='display track numbers')
    parser.add_argument('-tf', '--ts-first', action='store_true', help='timestamp before title')
    parser.add_argument('-pr', '--prefix', help='beginning of line')
    parser.add_argument('-s', '--separator', help='separator between title and timestamp')
    parser.add_argument('-pa', '--parentheses', choices=('(', '[', '{', '<'), help='surround timestamps with parentheses')
    parser.add_argument('-o', '--output', type=partial(open, mode='w'), default=None, help='output filename')
    parser.add_argument('-d', '--debug', action='count')
    args = parser.parse_args()

    DEBUG = args.debug or 0
    if not DEBUG:
        logging.disable(logging.DEBUG)
    logging.debug(args)

    tracklist = get_tracklist_data(args.query)
    if not tracklist:
        return

    print('\n'.join(format_lines(tracklist, **vars(args))), file=args.output)


if __name__ == '__main__':
    main()
