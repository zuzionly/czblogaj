""" czblog API & Router"""

# python imports
import os
import datetime
import traceback
import flask
from flask.ext.restless import APIManager
from flask.ext.sqlalchemy import SQLAlchemy
from unicodedata import normalize
from functools import wraps

# web
from werkzeug.security import check_password_hash
from flask import render_template, request, Flask, flash, redirect, url_for, \
    abort, jsonify, Response, make_response, send_from_directory
from werkzeug import secure_filename

# SMTP mail
from flask.ext.mail import Mail, Message
# logs
import logging
# utils
from utils import allowed_file, MARKDOWN_PARSER, slugify


# Create the Flask application and the Flask-SQLAlchemy object.
app = flask.Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///simple.db'

# for session
app.secret_key = "$\xb8\xf1\xdf\xd4\x9c\xcf5\xcb\x9f\xb2On\x12\xde\xcb\x8f\xa5\xd6\t\x85\xdf\xe2Y\xc8\xfb\xcd\x05-u"

# db
db = SQLAlchemy(app)


# mail
myMail = Mail(app)

# logger
# set file logger handler
file_handler = logging.FileHandler(
    "czblog.log", mode='a', encoding="utf8", delay=False)
file_handler.setLevel(logging.ERROR)
app.logger.addHandler(file_handler)


def trace_back():
    try:
        return traceback.format_exc()
    except:
        return ''

# Model


class Post(db.Model):

    def __init__(self, title=None, created_at=None):
        if title:
            self.title = title
            self.slug = slugify(title)
        if created_at:
            self.created_at = created_at
            self.updated_at = created_at

    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    slug = db.Column(db.String(), unique=True)
    text = db.Column(db.String(), default="")
    draft = db.Column(db.Boolean(), index=True, default=True)
    views = db.Column(db.Integer(), default=0)
    created_at = db.Column(db.DateTime, index=True)
    updated_at = db.Column(db.DateTime)

    def render_content(self):
        _cached = cache.get("post_%s" % self.id)
        if _cached is not None:
            return _cached
        text = MARKDOWN_PARSER.convert(self.text)
        cache.set("post_%s" % self.id, text)
        return text

    def set_content(self, content):
        cache.delete("post_%s" % self.id)
        self.text = content

# Create db
try:
    db.create_all()
except Exception:
    app.logger.error('exception caught: ' + trace_back())
    pass

# Create the Flask-Restless API manager.
manager = APIManager(app, flask_sqlalchemy_db=db)

# Define pre- and postprocessor functions as described below.
def pre_update(instance_id=None, data=None, **kw):
    if data != None:
        title = data.title
        data.slug = slugify(title)

# Create API endpoints, which will be available at /api/<method>/<tablename> by
# default. Allowed HTTP methods can be specified as well.
manager.create_api(Post,
                   methods=['GET', 'POST', 'PATCH', 'DELETE'],
                   # A list of preprocessors for each method.
                   preprocessors={
                       'POST': [pre_update],
                       'PUT_SINGLE': [pre_update],
                   },
                   url_prefix='/api')


# favicon.ico
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico', mimetype='image/vnd.microsoft.icon')

# index


@app.route("/")
def index():
    return render_template('index.html')

# view by post id


@app.route("/pid/<int:post_id>")
def view_post(post_id):
    return render_template("view.html")

# view by post slug


@app.route("/p/<slug>")
def view_post_slug(slug):
    return render_template("view.html")

# edit post by id


@app.route("/edit/<int:post_id>")
def edit(post_id):
    return render_template("edit.html")

# guest book


@app.route("/guestbook")
def guestbook():
    return render_template("guestbook.html")

# about


@app.route("/about")
def about():
    return render_template("about.html")

# admin


@app.route("/admin")
def admin():
    return render_template("admin.html")

# settings


@app.route("/settings")
def settings():
    return render_template("settings.html")

# send mail


@app.route("/mail/<int:post_id>", methods=["POST", "GET"])
def mail(post_id):
    try:
        title = request.form.get("title")
        body = request.form.get("body")
        if title:
            msg = Message("%s @blog" % (title),
                          sender="admin@chuan7i.com",
                          recipients=["zuzionly.4e540@m.evernote.com"])
            msg.html = body
            myMail.send(msg)
            return jsonify(success=True)
        else:
            return jsonify(success=False)
    except:
        app.logger.error("-----send mail fail----------")
        app.logger.error(datetime.datetime.now())
        app.logger.error('exception caught: ' + trace_back())
        app.logger.error('Post id:' + str(post_id))
        app.logger.error("-----------------------------")
        return jsonify(success=False)


@app.route("/posts.rss")
def feed():
    posts = db.session.query(Post)\
        .filter_by(draft=False)\
        .order_by(Post.created_at.desc())\
        .limit(10)\
        .all()

    response = make_response(render_template('index.xml'))
    response.mimetype = "application/xml"
    return response


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', now=datetime.datetime.now()), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html', now=datetime.datetime.now()), 500


if __name__ == "__main__":
    # Listen on all interfaces. This is so I could view the page on my
    # iPhone/WP7 *not* so you can deploy using this file.
    app.run(host="0.0.0.0")
