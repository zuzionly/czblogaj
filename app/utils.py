import re
import os
# markdown
import markdown
# cache
from werkzeug.contrib.cache import FileSystemCache, NullCache
# pinyin
from xpinyin import Pinyin

# mark down
MARKDOWN_PARSER = markdown.Markdown(extensions=['fenced_code'],
                                    output_format="html5",
                                    safe_mode=True)
# cache
cache_directory = os.path.dirname(__file__)
try:
    cache = FileSystemCache(os.path.join(cache_directory, "cache"))
except Exception as e:
    print "Could not create cache folder, caching will be disabled."
    print "Error: %s" % e
    cache = NullCache()

# slugify the chinese charachers to pinyin
def slugify(text):
    # for slugify
    p = Pinyin()
    return p.get_pinyin(text.decode("utf-8"))

# define the allowed file type
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']