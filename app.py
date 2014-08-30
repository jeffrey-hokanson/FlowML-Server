#! /opt/local/bin/python


# This code is largely indebted to several projects on github.
#
# This follows large portions of the jQuery-File-Upload project
# https://github.com/blueimp/jQuery-File-Upload
# and the corresponding flask code:
# https://github.com/ngoduykhanh/flask-file-uploader
# This code borrows from 
# https://github.com/thrisp/flask-celery-example
# when setting up the celery server

from __future__ import absolute_import

import os
import time
import zipfile
from os import listdir
from os.path import isfile, join
import json
import simplejson
from flask import Flask, Blueprint, abort, jsonify, request, render_template, \
	session, redirect, url_for, flash, send_from_directory, make_response
from flask.ext.bootstrap import Bootstrap
from flask_mail import Mail, Message
from werkzeug import secure_filename
from celery import Celery

import md5

from wtforms import Form, StringField, validators

# Logging setup:
# https://gist.github.com/ibeex/3257877

import logging
from logging.handlers import RotatingFileHandler


# Local lib
from lib.upload_file import uploadfile
import settings

import flowml as fml

ALLOWED_EXTENSIONS = set(['fcs'])
IGNORED_FILES = set(['.gitignore'])


app = Flask(__name__)
app.config.from_object('settings')
# password stored in separate file
try:
	app.config.from_object('secret_settings')
except:
	pass
bootstrap = Bootstrap(app)

# setup for mail
mail = Mail()
mail.init_app(app)


def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

celery = make_celery(app)

def make_id(ip, use_time = False, iterate = False):
	if use_time:
		from time import time
	salt = app.config['SECRET_KEY']
	hsh = md5.new()
	base = unicode(salt + "%s" % (ip))
	hsh.update(base.encode("utf8"))
	if use_time:
		hsh.update(str(time()).encode("utf8"))

	if iterate:
		while True:
			session_id = hsh.hexdigest()
			if os.path.exists(join('tsne/data/download', session_id)):
				hsh.update('not new'.encode("utf8"))
			else:
				break
	return session_id

################################################################################
# Webpages
#
# NOTE ON DATA LOCATIONS:
# When files are uploaded, they go to tsne/data/upload.
# Upon clicking Run t-sne, they are moved to tsne/data/download prior to 
# analysis.  In this way, users can queue up another set.
################################################################################
@app.route('/')
def index():
	return render_template('index.html')

@app.route('/tsne')
def tsne():
	# Here we generate a session id based on the IP address
	# These are a unique combination of the salt, IP address and do not overlap
	# any previous session ID
	
	salt = app.config['SECRET_KEY']
	hsh = md5.new()
	base = unicode(salt + "%s" % (request.remote_addr))
	hsh.update(base.encode("utf8"))
	session_id = hsh.hexdigest()

	return redirect('tsne/{}'.format(session_id)) 

@app.route('/tsne/<session_id>/')
def tsne_id(session_id):
	kwargs = {}	
	kwargs['warning_email'] = request.args.get('warning_email', False)
	kwargs['tsne_success'] = request.args.get('tsne_success', False)
	kwargs['no_files'] = request.args.get('no_files', False)
	try:
		os.mkdir('tsne/data/upload/{}'.format(session_id))
	except:
		pass
	return render_template('tsne.html', session_id = session_id, **kwargs)

################################################################################
# File Upload Functions
# Code mainly from 
# https://github.com/ngoduykhanh/flask-file-uploader
# that handles multiple simultaneous file uploads
################################################################################
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def gen_file_name(base_path, filename):
    """
    If file was exist already, rename it and return a new name
    """
    i = 1
    while os.path.exists(os.path.join(base_path, filename)):
        name, extension = os.path.splitext(filename)
        filename = '%s_%s%s' % (name, str(i), extension)
        i = i + 1

    return filename

@app.route("/tsne/<session_id>/upload", methods=['GET', 'POST'])
def upload(session_id):
	base_path = os.path.join(app.config['TSNE_ROOT'], 'upload', session_id)
	if request.method == 'POST':
		file = request.files['file']
		#pprint (vars(objectvalue))
		if file:
			filename = secure_filename(file.filename)
			filename = gen_file_name(base_path, filename)
			mimetype = file.content_type


			if not allowed_file(file.filename):
				result = uploadfile(name=filename, type=mimetype, size=0, not_allowed_msg="Filetype not allowed", session_id = session_id)
			else:
				# save file to disk
				uploaded_file_path = os.path.join(base_path, filename)
				file.save(uploaded_file_path)

                # get file size after saving
				size = os.path.getsize(uploaded_file_path)

                # return json for js call back
				result = uploadfile(name=filename, type=mimetype, size=size, session_id = session_id)
            
			return simplejson.dumps({"files": [result.get_file()]})

	if request.method == 'GET':
		# get all file in ./data directory
		files = [ f for f in os.listdir(base_path) if os.path.isfile(os.path.join(base_path,f)) and f not in IGNORED_FILES ]
        
		file_display = []

		for f in files:
			size = os.path.getsize(os.path.join(base_path, f))
			file_saved = uploadfile(name=f, size=size, session_id = session_id)
			file_display.append(file_saved.get_file())

		return simplejson.dumps({"files": file_display})

	return redirect(url_for('tsne'))

@app.route("/tsne/<session_id>/delete/<string:filename>", methods=['DELETE'])
def delete(session_id, filename):
	base_path = os.path.join(app.config['TSNE_ROOT'], 'upload', session_id)
	file_path = os.path.join(base_path, filename)
    #file_thumb_path = os.path.join(app.config['THUMBNAIL_FOLDER'], filename)

	if os.path.exists(file_path):
		try:
			os.remove(file_path)

            #if os.path.exists(file_thumb_path):
            #    os.remove(file_thumb_path)
            
			return simplejson.dumps({filename: 'True'})
		except:
			return simplejson.dumps({filename: 'False'})

@app.route("/tsne/<session_id>/data/<string:filename>", methods=['GET'])
def get_file(session_id, filename):
	base_path = os.path.join(app.config['TSNE_ROOT'],'upload', session_id)
	return send_from_directory(base_path, filename=filename)

################################################################################
# Code for running tsne on selected files
################################################################################


@celery.task(name='tasks.batch_tsne')
def batch_tsne(fnames, email, job_id):
	sample = 100
	fdarray = []
	for fname in fnames:
		fdarray.append(fml.FlowData(fname))

	fml.tsne(fdarray, 'visne', sample = sample, verbose = True)
	
	for fd, fname in zip(fdarray, fnames):
		fd.fcs_export(fname)

	# zip the files together to be mailed
	zipfilename = 'tsne.zip'
	zipf = zipfile.ZipFile(zipfilename,'w')
	path = join(fnames[0], os.pardir)
	for root, dirs, files in os.walk(path):
		for f in files:
			if f.endswidth('.fcs'):
				zipf.write(os.path.join(root,file))

	# send an email to announce completion
	msg = Message("Your t-SNE run is complete.", recipients = [email])
	url = app.config['EXTERNAL_URL_BASE'] + 'tsne/data/download/{}/{}'.format(job_id, zipfilename)
	msg.body = ('Congradulations, your t-SNE run has completed.'
			'You may download the results at: ' + url)
	mail.send(msg)	
	app.logger.info('Job: {} COMPLETE!'.format(job_id))

class EmailRegistrationForm(Form):
	email = StringField('email', [validators.Length(min=6, max=35)])

@app.route("/tsne/data/download/<session_id>/tsne.zip")
def download_tsne(session_id):
	# see: https://stackoverflow.com/questions/5410255/preferred-method-for-downloading-a-file-generated-on-the-fly-in-flask
	response = make_response()
	response.headers['Cache-Control'] = 'no-cache'
	response.headers['Content-Type'] = 'application/zip'
	response.headers['X-Accel-Redirect'] = url_for('download_tsne', session_id = session_id)
	return response
	

@app.route("/tsne/<session_id>/run-tsne", methods = ['POST', 'GET'])
def run_tsne(session_id):
	"""Run t-SNE
	"""
	error = None
	form = EmailRegistrationForm(request.form)
	if request.method == 'POST' and form.validate():
		email = form.email.data
	else:
		app.logger.warning('Invalid email')
		error = 'Invalid email'		
		return redirect(url_for('tsne_id', session_id = session_id, warning_email = True))
	
	# move the uploaded files into a download directory to be worked on
	base_upload = join(app.config['TSNE_ROOT'], 'upload', session_id)
	# we move to a new folder name
	job_id = make_id(request.remote_addr, use_time = True, iterate = True)

	base_download = join(app.config['TSNE_ROOT'], 'download', job_id)
	#app.logger.info('Moving {} to {}'.format(base_upload, base_download))
	os.rename(base_upload, base_download)
	fnames = [ os.path.abspath(join(base_download,f)) for f in listdir(base_download) \
				if isfile(join(base_download,f)) & f.endswith(".fcs") ]

	if len(fnames) == 0:
		return redirect(url_for('tsne_id', session_id = session_id, no_files = True))

	# make a file with the email address to send
	f = open(join(base_download,'email.txt'), 'w')
	f.write(email)
	f.close()
	# Log info about this job
	app.logger.info('### Job {} ###'.format(job_id))
	app.logger.info('Email: {}'.format(email))
	app.logger.info('Time: {}'.format(time.strftime('%X %x %Z')))
	for fname in fnames:
		app.logger.info('File: {}'.format(fname))

	# queue the job	
	batch_tsne.apply_async((fnames, email, job_id))


	# TODO: point at success page (or put notice?)
	return redirect(url_for('tsne_id', session_id = session_id, tsne_success = True))

################################################################################
# Start the server, if asked
################################################################################
if __name__ == "__main__":
	port = int(os.environ.get("PORT", 5000))

	# Setup logging functionality as per
	# https://gist.github.com/ibeex/3257877
	handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount = 1)
	handler.setLevel(logging.INFO)
	app.logger.addHandler(handler)
	

	# local test
	deploy_bad = False
	if deploy_bad:
		app.run(host = '0.0.0.0', port = 5000, debug = False)
	else:
		app.run(host='localhost', port=port, debug=True)

	
