#! /opt/local/bin/python
from flask import Flask, render_template
from flask_mail import Mail, Message

from  werkzeug.debug import get_current_traceback

app = Flask(__name__)
app.config.from_object('settings')
# password storeds in separate file
try:
	app.config.from_object('secret_settings')
except:
	pass

# setup for mail
mail = Mail()
mail.init_app(app)


@app.route('/')
def index():
	msg = Message('Hello', recipients = ['jeffrey@hokanson.us'])
	msg.body = 'this is the message body'
	try:
		mail.send(msg)
		return "Email sent"
	except:
		track = get_current_traceback()
		track.log()
		return 'Failed'

if __name__ == '__main__':
#	print app.config
	app.run()
