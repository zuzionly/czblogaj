#!/usr/bin/env python
# encoding: utf-8
from xpinyin import Pinyin

p = Pinyin()

def slugify(text):
    return p.get_pinyin(text.decode("utf-8"))

s = "哈哈"
print(slugify(s))