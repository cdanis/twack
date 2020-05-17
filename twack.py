#!/usr/bin/env python3
"""Posts Twitch go-live notifications to Slack.  https://i.imgur.com/vArGUrH.png"""

__author__ = "Chris Danis"
__email__ = "cdanis@gmail.com"
__version__ = "0.1.1"
__copyright__ = """
Copyright © 2020 Chris Danis
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software distributed under the
License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied.  See the License for the specific language governing permissions
and limitations under the License.
"""

import argparse
import requests
import yaml
import time

from collections import defaultdict

from box import Box
from logzero import logger

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'twack/{} (https://github.com/cdanis/twack) python-requests/{}'.format(
        __version__, requests.__version__)})


# TODO: cache game names in the checkpoint file as well
def get_game_names(games):
    if len(games) == 0:
        return {}
    params = {'id': list(games)}
    logger.debug('calling twitch API for games %s', params)
    response = SESSION.get('https://api.twitch.tv/helix/games',
                           params=params)
    rv = {}
    for game in response.json()['data']:
        rv[game['id']] = game['name']
    logger.debug('games response: %s %s', response, rv)
    return rv


def main(args):
    config = Box.from_yaml(args.config)
    SESSION.headers.update({'Client-ID': config.twitch_client_id})

    twitches_to_slacks = defaultdict(set)
    for dest, sink in config.sinks.items():
        for username in sink.twitches:
            twitches_to_slacks[username.lower()].add(dest)

    checkpoint = Box(yaml.safe_load(args.checkpoint) or {}, default_box=True)
    last_announce = checkpoint.last_announce

    if (not checkpoint.auth.token or not checkpoint.auth.expiry_time
            or time.time() >= checkpoint.auth.expiry_time):
        logger.debug('fetching new auth token')
        r = SESSION.post('https://id.twitch.tv/oauth2/token',
                         params={'client_id': config.twitch_client_id,
                                 'client_secret': config.twitch_client_secret,
                                 'grant_type': 'client_credentials'})
        r.raise_for_status()
        j = r.json()
        checkpoint.auth.token = j['access_token']
        checkpoint.auth.expiry_time = time.time() + j['expires_in']
        logger.debug('successfully fetched new auth token')

    SESSION.headers.update({'Authorization': 'Bearer {}'.format(checkpoint.auth.token)})

    params = {'user_login': list(twitches_to_slacks.keys())}
    logger.debug('calling twitch API for streams %s', params)
    # TODO need to split into multiple requests in chunks of 100, if we ever want to watch that many
    response = SESSION.get('https://api.twitch.tv/helix/streams',
                           params=params)
    logger.debug('got Twitch response %s', response)
    response.raise_for_status()
    data = Box(response.json()).data
    games = get_game_names(set([x.game_id for x in data]))
    for stream in data:
        logger.debug('processing stream %s', stream)
        twitch = stream.user_name.lower()
        sinks = {x: config.sinks[x] for x in twitches_to_slacks[twitch]}
        gamename = games[stream.game_id]
        preview_url = stream.thumbnail_url.replace('{width}', '320').replace('{height}', '180')
        text = (f"<https://twitch.tv/{stream.user_name}|twitch.tv/{stream.user_name}> has gone live"
                f"— {gamename} — {stream.title} <{preview_url}| >")
        for sinkname, sink in sinks.items():
            logger.debug('considering %s for %s', sinkname, twitch)
            # Don't notify about the same stream ID
            if last_announce[twitch][sinkname].last_id == stream.id:
                logger.debug('announced %s already', stream.id)
                continue
            # TODO: don't notify about too-similar titles?
            # Don't notify too often for the same stream, even if all the above changes
            since_last = time.time() - (last_announce[twitch][sinkname].last_time or 0)
            if since_last < 60*60*3:  # 3 hours?  TODO probably should be configurable
                logger.debug('announced too recently (%s seconds since %s)',
                             since_last, last_announce[twitch][sinkname].last_time)
                continue
            payload = {'text': text}
            logger.info('notifying %s about %s', sinkname, twitch)
            webhook_url = sink.webhook['prod' if args.prod else 'test']
            # TODO make another session for posting to slack
            notif = requests.post(webhook_url, json=payload,
                                  headers={'Content-Type': 'application/json'})
            logger.debug('response from Slack: %s', notif)
            last_announce[twitch][sinkname].last_id = stream.id
            last_announce[twitch][sinkname].last_title = stream.title
            last_announce[twitch][sinkname].last_time = time.time()
    args.checkpoint.seek(0, 0)
    args.checkpoint.truncate(0)
    args.checkpoint.write(checkpoint.to_yaml())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Poll the Twitch API and post to Slack')
    parser.add_argument('-c', '--config', type=argparse.FileType('r'), default='config.yaml')
    parser.add_argument('--checkpoint', type=argparse.FileType('r+'), default='checkpoint.yaml')
    parser.add_argument('--prod', action='store_true')

    args = parser.parse_args()
    main(args)
