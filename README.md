# Emby-notifier

A notification script that sends a mail with posters of the latest added movies and shows.

## Dependencies
- python3
- python3-requests

It is tested to run on the host that runs Emby with the os Ubuntu 22.04, but it should be able to run on a seperate host as long the script can access Emby.

For the links on the poster images to work, the user that recieves the email need to be able to access Emby from the internet or trough some other means.

## Install

Move the files to the host(eg. the host that run Emby) and put them in the users home directory.
Eg. `/home/<user>/emby-notifier/`

Copy the file `example-config.ini` to `config.ini`

Open `config.ini` and configure your settings

Add the files to crontab with `crontab -e`

Add the following and change the paths so the match the path to the files in `/home/<user>/emby-notifier/`
```
0 * * * * <path-to_pull-recent.py>
0 10 * * * <path-to_sendmail-recent.py>
```
This will run the pull script every hour and send a mail every 24h at 10.00.
