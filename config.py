import os
from dotenv import load_dotenv, find_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

if not find_dotenv():
    exit("Environment variables are not loaded because there is no .env file")
else:
    load_dotenv()


class Config(object):
    """Config properties"""
    SECRET_KEY = os.getenv('SECRET_KEY') or "I'm the secret key, honey."

    # DB config
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # The number of displayed items in the /index, /explore
    POSTS_PER_PAGE = 25
