import argparse
import requests
from collections import namedtuple
from datetime import timedelta
from operator import attrgetter

DISCOGS_SEARCH = 'https://api.discogs.com/database/search'
TOKEN = 'hAzLxILnlVAkXByQddbJcvsaYnmjytIXnuxzfYHm'

Track = namedtuple('Track', ['position', 'title', 'time'])  # time is first duration, then timestamp


def str_to_timedelta(duration: str):
    time_parts = list(map(int, duration.split(':')))
    return timedelta(minutes=time_parts[0], seconds=time_parts[1])


def timedelta_to_str(td: timedelta):
    s = str(td)
    if s.startswith('0:'):
        return ':'.join(s.split(':')[1:])
    return s


def get_or_empty(url: str):
    with requests.get(url) as response:
        return response.json() if response.ok else {}


def get_tracklist_data(query):
    data = get_or_empty(f'{DISCOGS_SEARCH}?q={query}&token={TOKEN}')
    if not data['results']:
        return []
    data = get_or_empty(data['results'][0]['resource_url'])
    return [Track(track['position'], track['title'], str_to_timedelta(track['duration']))
            for track in data['tracklist'] if track['type_'] == 'track']


def durations_to_timestamps(tracklist):
    new_tracklist = [tracklist[0]._replace(time=timedelta())]
    for i in range(1, len(tracklist)):
        timestamp = new_tracklist[i - 1].time + tracklist[i - 1].time
        new_tracklist.append(tracklist[i]._replace(time=timestamp))
    return new_tracklist


def organize_lines(tracklist, prefix, separator, numbered, ts_first):
    return [(f'{prefix} ' if prefix else '')
            + (f'{position}. ' if numbered else '')
            + (timedelta_to_str(time) if ts_first else title)
            + (f' {separator} ' if separator else ' ')
            + (title if ts_first else timedelta_to_str(time))
            for position, title, time in tracklist]


def main():
    parser = argparse.ArgumentParser(description='Generate tracklist timestamps for YouTube video description')
    parser.add_argument('title', nargs='+', help='the (artist name and) album title')
    parser.add_argument('-n', '--numbered', action='store_true', help='display track numbers')
    parser.add_argument('-tf', '--ts-first', action='store_true', help='timestamp before title')
    parser.add_argument('-p', '--prefix', help='beginning of line')
    parser.add_argument('-s', '--separator', help='separator between title and timestamp')
    args = parser.parse_args()

    query = ' '.join(args.title)
    tracklist = sorted(get_tracklist_data(query), key=attrgetter('position'))
    tracklist = durations_to_timestamps(tracklist)
    lines = organize_lines(tracklist, args.prefix, args.separator, args.numbered, args.ts_first)

    print('\n'.join(lines))


if __name__ == '__main__':
    main()
