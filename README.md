# twack
*many people are streaming*

`twack` posts Twitch stream-go-live notifications to Slack.

Invoke it every minute via cron or systemd timer.

It checkpoints state, so it shouldn't send duplicate announcements.

# Getting started
* Create a Twitch application on their dev console:
  https://dev.twitch.tv/console
  * Make note of the client ID, and also generate a client secret.
    You need them for the config file.
* Write a config file.  Easiest is to `cp example-config.yaml config.yaml`
  and start editing.
    * If you need to, first create some Slack webhooks:
      https://api.slack.com/messaging/webhooks
    * It's best if the 'test' webhooks target a DM with yourself,
      and the 'prod' webhooks target where you actually want to post.
* Create an empty checkpoint file: `touch checkpoint.yaml`
* Invoke `twack.py` for a first test.  Without `--prod`, this will post to your
  test webhooks.  Perfect for testing.
* When you're satisfied, optionally truncate the checkpoint file,
  and run twack in a shell loop/from cron/from systemd once a minute,
  passing `--prod`.

## TODOs
* add Discord support.
* support monitoring more than 100 streams
* better docs
* example systemd unit files?
* debian package?
* post to a special Slack webhook once in a while if something is broken?
