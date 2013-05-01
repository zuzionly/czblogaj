""" czblog API"""

# python imports
import os,datetime,re,traceback
import flask
from flask.ext.restless import APIManager
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug.contrib.cache import FileSystemCache, NullCache
from functools import wraps
from unicodedata import normalize
#web
from werkzeug.security import check_password_hash
from flask import render_template, request, Flask, flash, redirect, url_for, \
                  abort, jsonify, Response, make_response,send_from_directory
from werkzeug import secure_filename
#markdown
import markdown
# SMTP mail
from flask.ext.mail import Mail,Message
#logs
import logging

# for slugify
_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

def slugify(text, delim=u'-'):
    """Generates an slightly worse ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', unicode(word)).encode('ascii', 'ignore')
        if word:
            result.append(word)
    slug = unicode(delim.join(result))
    # This could have issues if a post is marked as draft, then live, then
    # draft, then live and there are > 1 posts with the same slug. Oh well.
    count = db.session.query(Post).filter_by(slug=slug).count()
    if count > 0:
        return "%s%s%s" % (slug, delim, count)
    else:
        return slug

# Create the Flask application and the Flask-SQLAlchemy object.
app = flask.Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///simple.db'

# for session
app.secret_key = "$\xb8\xf1\xdf\xd4\x9c\xcf5\xcb\x9f\xb2On\x12\xde\xcb\x8f\xa5\xd6\t\x85\xdf\xe2Y\xc8\xfb\xcd\x05-u"

# db
db = SQLAlchemy(app)

# set file logger handler
file_handler = logging.FileHandler("czblog.log", mode='a', encoding="utf8", delay=False)
file_handler.setLevel(logging.ERROR)
app.logger.addHandler(file_handler)

# cache
cache_directory = os.path.dirname(__file__)
try:
    cache = FileSystemCache(os.path.join(cache_directory, "cache"))
except Exception,e:
    print "Could not create cache folder, caching will be disabled."
    print "Error: %s"%e
    cache = NullCache()

# mark down
MARKDOWN_PARSER = markdown.Markdown(extensions=['fenced_code'],
                                    output_format="html5",
                                    safe_mode=True)

# mail
myMail = Mail(app)

# logger
def trace_back():
    try:
        return traceback.format_exc()
    except:
        return ''

class Post(db.Model):
    def __init__(self, title=None, created_at=None):
        if title:
            self.title = title
            self.slug = slugify(title)
        if created_at:
            self.created_at = created_at
            self.updated_at = created_at

    __tablename__ = "posts"
    id    = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    slug  = db.Column(db.String(), unique=True)
    text  = db.Column(db.String(), default="")
    draft = db.Column(db.Boolean(), index=True, default=True)
    views = db.Column(db.Integer(), default=0)
    created_at = db.Column(db.DateTime, index=True)
    updated_at = db.Column(db.DateTime)

    def render_content(self):
        _cached = cache.get("post_%s"%self.id)
        if _cached is not None:
            return _cached
        text = MARKDOWN_PARSER.convert(self.text)
        cache.set("post_%s"%self.id, text)
        return text

    def set_content(self, content):
        cache.delete("post_%s"%self.id)
        self.text = content


try:
    db.create_all()
except Exception:
    app.logger.error('exception caught: ' + trace_back())
    pass

# Create the Flask-Restless API manager.
manager = APIManager(app, flask_sqlalchemy_db=db)

# Create API endpoints, which will be available at /api/<tablename> by
# default. Allowed HTTP methods can be specified as well.
##manager.create_api(Post, methods=['GET', 'POST', 'DELETE'])
manager.create_api(Post, methods=['GET'], url_prefix='/api/get')
manager.create_api(Post, methods=['POST'], url_prefix='/api/add')
manager.create_api(Post, methods=['PATCH'], url_prefix='/api/update')
manager.create_api(Post, methods=['DELETE'], url_prefix='/api/remove')



@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
            os.path.join(app.root_path, 'static'),
                'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/guestbook")
def guestbook():

    return render_template("guestbook.html",
                           now=datetime.datetime.now())

@app.route("/about")
def about():

    return render_template("about.html",
                           now=datetime.datetime.now())

@app.route("/<int:post_id>")
def view_post(post_id):
    """ view_post renders a post and returns the Response object """
    try:
        post = db.session.query(Post).filter_by(id=post_id, draft=False).one()
    except Exception:
        app.logger.error("---------------------")
        app.logger.error(datetime.datetime.now())
        app.logger.error('exception caught: ' + trace_back())
        app.logger.error('Post id:'+str(post_id))
        app.logger.error("---------------------")
        return abort(404)

    db.session.query(Post)\
        .filter_by(id=post_id)\
        .update({Post.views:Post.views + 1})
    db.session.commit()

    return render_template("view.html", post=post)

@app.route("/post/<slug>")
def view_post_slug(slug):
    try:
        post = db.session.query(Post).filter_by(slug=slug,draft=False).one()
    except Exception:
        #TODO: Better exception
        app.logger.error("---------------------")
        app.logger.error(datetime.datetime.now())
        app.logger.error('exception caught: ' + trace_back())
        app.logger.error('slug:'+slug)
        app.logger.error("---------------------")
        return abort(404)

    if not any(botname in request.user_agent.string for botname in
                ['Googlebot',  'Slurp',         'Twiceler',     'msnbot',
                 'KaloogaBot', 'YodaoBot',      '"Baiduspider',
                 'googlebot',  'Speedy Spider', 'DotBot']):
        db.session.query(Post)\
            .filter_by(slug=slug)\
            .update({Post.views:Post.views+1})
        db.session.commit()

##    pid = request.args.get("pid", "0")
##    return render_template("view.html", post=post, pid=pid, is_admin=is_admin())
    return render_template("view.html", post=post)

@app.route("/new", methods=["POST", "GET"])
def new_post():
    post = Post(title=request.form.get("post_title","untitled"),
                created_at=datetime.datetime.now())

    db.session.add(post)
    db.session.commit()

    return redirect(url_for("edit", post_id=post.id))

@app.route("/edit/<int:post_id>", methods=["GET","POST"])
def edit(post_id):
    try:
        post = db.session.query(Post).filter_by(id=post_id).one()
    except Exception:
        #TODO: better exception
        app.logger.error("---------------------")
        app.logger.error(datetime.datetime.now())
        app.logger.error('exception caught: ' + trace_back())
        app.logger.error('Post id:'+str(post_id))
        app.logger.error("---------------------")
        return abort(404)

    if request.method == "GET":
        return render_template("edit.html", post=post)
    else:
        if post.title != request.form.get("post_title", ""):
            post.title = request.form.get("post_title","")
            post.slug = slugify(post.title)
        post.set_content(request.form.get("post_content",""))
        post.updated_at = datetime.datetime.now()

        if any(request.form.getlist("post_status", type=int)):
        #if str(request.form.get("post_status")) == 'True':
            post.draft = True
        else:
            post.draft = False

        db.session.add(post)
        db.session.commit()
        return redirect(url_for("edit", post_id=post_id))

@app.route("/delete/<int:post_id>", methods=["GET","POST"])
def delete(post_id):
    try:
        post = db.session.query(Post).filter_by(id=post_id).one()
    except Exception:
        # TODO: define better exceptions for db failure.
        app.logger.error("---------------------")
        app.logger.error(datetime.datetime.now())
        app.logger.error('exception caught: ' + trace_back())
        app.logger.error('Post id:'+str(post_id))
        app.logger.error("---------------------")
        flash("Error deleting post ID %s"%post_id, category="error")
        return abort(500)
    else:
        db.session.delete(post)
        db.session.commit()

    return redirect(request.args.get("next","")
        or request.referrer
        or url_for('index'))

@app.route("/admin", methods=["GET", "POST"])
def admin():
    drafts = db.session.query(Post)\
                 .filter_by(draft=True)\
                 .order_by(Post.created_at.desc()).all()
    posts  = db.session.query(Post)\
                 .filter_by(draft=False)\
                 .order_by(Post.created_at.desc()).all()
    return render_template("admin.html", drafts=drafts, posts=posts, now=datetime.datetime.now())

@app.route("/admin/save/<int:post_id>", methods=["POST"])
def save_post(post_id):
    try:
        post = db.session.query(Post).filter_by(id=post_id).one()
    except Exception:
        # TODO Better exception
        app.logger.error("---------------------")
        app.logger.error(datetime.datetime.now())
        app.logger.error('exception caught: ' + trace_back())
        app.logger.error('Post id:'+post_id)
        app.logger.error("---------------------")
        return abort(404)
    if post.title != request.form.get("title", ""):
        post.title = request.form.get("title","")
        post.slug = slugify(post.title)
    post.set_content(request.form.get("content", ""))
    post.updated_at = datetime.datetime.now()
    db.session.add(post)
    db.session.commit()
    return jsonify(success=True)

@app.route("/preview/<int:post_id>")
def preview(post_id):
    try:
        post = db.session.query(Post).filter_by(id=post_id).one()
    except Exception:
        # TODO: Better exception
        app.logger.error("---------------------")
        app.logger.error(datetime.datetime.now())
        app.logger.error('exception caught: ' + trace_back())
        app.logger.error('Post id:'+post_id)
        app.logger.error("---------------------")
        return abort(404)

    return render_template("post_preview.html", post=post)

@app.route("/settings")
def settings():

    return render_template("settings.html",now=datetime.datetime.now())

@app.route("/settings/save", methods=["POST"])
def save_settings():
    custom_config = {'POSTS_PER_PAGE':None,\
                     'POST_CONTENT_ON_HOMEPAGE':None,\
                     'SHOW_VIEWS_ON_HOMEPAGE':None,\
                     'ANALYTICS_ID':None,\
                     'GITHUB_USERNAME':None,\
                     'GOOGLE_PLUS_PROFILE':None,\
                     'TWITTER_HANDLE':None,\
                     'CONTACT_EMAIL':None,\
                     'BLOG_TITLE':None,\
                     'BLOG_TAGLINE':None,\
                     'BLOG_URL':None,\
                     'DISQUS_NAME':None,\
                     'FONT_NAME':None}
    # only save changed value
    try:
        for i in custom_config:
            if(app.config[i]!= request.form.get(i)):
                custom_config[i] = request.form.get(i)
                updateSettingFile(i,str(custom_config[i]))

        return jsonify(success=True)
    except:
        return jsonify(success=False)


def updateSettingFile(paraName,paraValue):
    oldFile = open('settings_custom.py')
    oldFileContent = oldFile.read()
    oldFile.close()
    # replace the new field
    newFileContent = re.sub(paraName+''' = "'''+str(app.config[paraName])+'''"''', paraName+''' = "'''+ paraValue+'''"''', oldFileContent)
    if newFileContent != oldFileContent and newFileContent != None:
        open('settings_custom.py', 'wb').write(newFileContent)

# routers
@app.route("/mail/<int:post_id>",methods=["POST", "GET"])
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
        app.logger.error('Post id:'+str(post_id))
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

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']

@app.route("/file/save", methods=["POST"])
def save_files():
    if request.method == 'POST':
            file = request.files['file']
            if file and allowed_file(file.filename.lower()):
                filename = secure_filename(file.filename)
                if '.' not in filename:
                    filename = secure_filename("%s.%s" % (datetime.datetime.now(), filename))
                try:
                    file.save(os.path.join(app.config['PATH'],app.config['UPLOAD_FOLDER'], filename))
                    return jsonify(filename=filename)
                except:
                    return jsonify(errorcode="save file failed!")
            else:
                return jsonify(errorcode="file type is not allowed!")

@app.route('/file/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html',now=datetime.datetime.now()), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html',now=datetime.datetime.now()), 500



if __name__ == "__main__":
    # Listen on all interfaces. This is so I could view the page on my iPhone/WP7 *not* so you can deploy using this file.
    app.run(host="0.0.0.0")
