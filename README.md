# twack
*many people are streaming*

`twack` posts Twitch stream-go-live notifications to Slack.

Invoke it every minute via cron or systemd timer.

It checkpoints state, so it shouldn't send duplicate announcements.

# TODOs
* add Discord support.
* support monitoring more than 100 streams
* better docs
* example systemd unit files?
* debian package?
* post to a special Slack webhook once in a while if something is broken?
