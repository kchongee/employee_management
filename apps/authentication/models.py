from datetime import timedelta
import sys
import jwt
import json 
from functools import wraps
from decouple import config
from flask_login import UserMixin
from flask import g, request, redirect, url_for, render_template, flash, session
from apps import db, login_manager, elasticache_redis
from apps.authentication.util import hash_pass

class Users(db.Model, UserMixin):

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(64), unique=True)
    password = db.Column(db.LargeBinary)        
    full_name = db.Column(db.String(64))
    contact = db.Column(db.String(64))
    address = db.Column(db.String(64))
    department = db.Column(db.String(64))
    job = db.Column(db.String(64))    
    is_admin = db.Column(db.Boolean, nullable=False)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():            
            if hasattr(value, '__iter__') and not isinstance(value, str):                
                value = value[0]

            if property == 'password':
                value = hash_pass(value)  # we need bytes here (not plain str)

            setattr(self, property, value)        


    def __repr__(self):
        return str(self.username)

    def as_dict(self):
        return {c.name: getattr(self, c.name).decode('utf-8') if type(getattr(self,c.name)) is bytes else getattr(self,c.name) for c in self.__table__.columns}

    def to_json(self):        
        return json.dumps(self.as_dict())

class Departments(db.Model):

    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), unique=True)


    def __init__(self, **kwargs):
        for property, value in kwargs.items():            
            if hasattr(value, '__iter__') and not isinstance(value, str):                
                value = value[0]                        
            setattr(self, property, value)                
            

    def __repr__(self):
        return str(self.title)

class Jobs(db.Model):

    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), unique=True)


    def __init__(self, **kwargs):
        for property, value in kwargs.items():            
            if hasattr(value, '__iter__') and not isinstance(value, str):                
                value = value[0]            

            setattr(self, property, value)

    def __repr__(self):
        return str(self.title)

    def as_dict(self):
       return {c.name: getattr(self, c.name) for c in self.__table__.columns}


@login_manager.user_loader
def user_loader(id):
    return Users.query.filter_by(id=id).first()


@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    user = Users.query.filter_by(username=username).first()
    return user if user else None


def token_required(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        print(f'token_required decorator auth_token: {session.get("auth_token")}', file=sys.stdout)
        token = None
        # ensure the jwt-token is passed with the headers
        if not (session.get("auth_token") and elasticache_redis.get(session.get("auth_token"))):        
            return render_template('home/page-403.html'), 403                            
        token = session.get("auth_token")
        
        data = jwt.decode(token, config('SECRET_KEY'), algorithms=['HS256'])
        
        current_user = elasticache_redis.get(f"user-{data['id']}") if elasticache_redis.get(f"user-{data['id']}") else Users.query.filter_by(id=data['id']).first().to_json()
        
        elasticache_redis.set(f"user-{data['id']}",current_user,ex=timedelta(hours=1))
        print(f'cache user_json: {elasticache_redis.get("user-{0}".format(data["id"]))}', file=sys.stdout)
        # try:
        #     # decode the token to obtain user public_id
        #     print(f'token: {token}', file=sys.stdout)
        #     data = jwt.decode(token, config('SECRET_KEY'), algorithms=['HS256'])
        #     print(f'token decoded: {data}', file=sys.stdout)
        #     current_user = Users.query.filter_by(id=data['id']).first()
        # except:
        #     return render_template('home/page-403.html'), 403
         # Return the user information attached to the token
        return func(*args, **kwargs)
    return decorator