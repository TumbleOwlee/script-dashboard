from flask import Flask

app = Flask(__name__)

app.secret_key = 'JDCSMAKCOEMQO@#!MM@132m3112m3u'
app.config['UPLOAD_FOLDER'] = '/tmp'
app.config['MAX_CONTENT-PATH'] = 124 * 1024 * 1024 * 1024 * 1024
