About
================
A simple blog based on [Simple](http://github.com/orf/simple).
rebuilt the UI with Bootstrap and PJAX.
using disqus as the comment plugin.


Installation
============

###Prerequisite
    pip install -r requirements.txt

###Customize the Configuration
    python create_config.py

###Run
    python czblog.py

Deployment
============
Deploying Simple is easy. Simply clone this repo (or your own) and install [Gunicorn](http://gunicorn.org/).
Then cd to the directory containing simple.py and run the following command:

    venv/bin/gunicorn -w 4 -p /tmp/gunicorn.pid czblog:app

This will start 4 gunicorn workers serving czblog. You can then use nginx or apache to forward requests to Gunicorn.

[watch dog](https://github.com/gorakhargosh/watchdog)
=============
######listen python file change and auto restart gunicorn(gunicorn no auto restart option)

###install:
    pip install watchdog
###command line:
    watchmedo shell-command --patterns="*.py" --recursive --command='kill -HUP `cat /tmp/gunicorn.pid`' /czblog

Example
============
You can see my blog running this software [here](http://chuan7i.com).

TODO
============

