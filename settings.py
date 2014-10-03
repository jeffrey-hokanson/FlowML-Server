SECRET_KEY = 'somedumbsalt'
CELERY_BROKER_URL = 'amqp://'
CELERY_RESULT_BACKEND = 'amqp://'
UPLOAD_FOLDER = 'data/'
THUMBNAIL_FOLDER = 'data/thumbnail'
MAX_CONTENT_LENGTH = 200 * 1024 * 1024
TSNE_ROOT = 'tsne/data/'
# Email settings
MAIL_SERVER = 'smtp.googlemail.com'
MAIL_PORT = 465
MAIL_USERNAME = 'flowml@hokanson.us'
MAIL_DEFAULT_SENDER = 'flowml@hokanson.us'
MAIL_USE_TLS = False
MAIL_USE_SSL = True
MAIL_SUPPRESS_SEND = False
EXTERNAL_URL_BASE = 'http://flowml.mdanderson.edu'
