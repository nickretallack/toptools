from flask import Flask, request, session, g, redirect, abort, url_for, render_template, flash
from flaskext.sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref, joinedload
from slugify import slugify
import json
from itertools import groupby
from coalesce import coalesce_rankings

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://postgres:sporks@localhost/toptools'
app.config['SQLALCHEMY_ECHO'] = True
app.secret_key = "Secret key for testing purposes only"
db = SQLAlchemy(app)

import logging
file_handler = logging.FileHandler("log/log.txt")
file_handler.setLevel(logging.DEBUG)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.DEBUG)


@app.before_request
def set_current_user():
    if 'openid' in session:
        openid = session['openid']
        g.current_user = User.query.filter_by(openid=openid).first()
    else:
        g.current_user = None

def setup_database():
    db.create_all()
    cache_user = User(id=0, name='Cache User')
    db.session.add(cache_user)
    db.session.commit()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(80))
    openid = db.Column(db.Unicode(255))

    def __repr__(self):
        return "<User %s %s:%s>" % (self.id, self.name, self.openid)

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Unicode(255))
    slug = db.Column(db.Unicode(255))
    created_by_id = db.Column(db.Integer, ForeignKey(User.id))

    created_by = relationship(User, backref='questions')

    def __init__(self, text):
        self.text = text
        self.slug = slugify(text)
        self.created_by = g.current_user

    def __repr__(self):
        return "<Question %s: %s>" % (self.id, self.text)

    @property
    def url(self):
        return url_for('show', id=self.id, slug=self.slug)

    @property
    def edit_url(self):
        return url_for('edit_question', id=self.id, slug=self.slug)
    
    def save_answer(self, user, answers):
        question = self

        # delete existing answers for this user,question, and also the cached answers
        db.session.query(Answer).filter_by(question=question, user=user).delete()
        db.session.query(Answer).filter_by(question=question, user_id=0).delete()

        for position, name in enumerate(answers):
            # find or create the tool.
            # NOTE: could speed this up by doing an 'IN' query earlier
            tool = Tool.query.filter_by(name=name).first()
            if not tool:
                tool = Tool(name=name)
                db.session.add(tool)

            answer = Answer(tool=tool, question=question, user=user, position=position)
            db.session.add(answer)

        db.session.commit()

        # Calculate the winners from all votes
        answers = Answer.query.filter_by(question=question).filter(Answer.user_id != 0).order_by('user','position asc').all()
        
        rankings = []
        for user, user_answers in groupby(answers, key=lambda answer: answer.user):
            rankings.append([answer.tool_id for answer in user_answers])

        ranking = coalesce_rankings(rankings)
        canonical_answers = [Answer(tool_id=answer, question=question, user_id=0, position=position)
                for position, answer in enumerate(ranking)]

        [db.session.add(answer) for answer in canonical_answers]
        db.session.commit()

    @property
    def top_answers(self):
        return Tool.query.join(Answer).filter(Answer.question==self).filter(Answer.user_id==0).order_by(Answer.position.asc()).all()

    def get_answers(self, user):
        if not user:
            return None
        else:
            return Tool.query.join(Answer).filter(Answer.question==self).filter(Answer.user==user).order_by(Answer.position.asc()).all()


class Tool(db.Model):
    __tablename__ = 'tools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(80))

    def __repr__(self):
        return "<Tool %s: %s>" % (self.id, self.name)

class Answer(db.Model):
    __tablename__ = 'answers'
    user_id = db.Column(db.Integer, ForeignKey(User.id), primary_key=True)
    question_id = db.Column(db.Integer, ForeignKey(Question.id), primary_key=True)
    tool_id = db.Column(db.Integer, ForeignKey(Tool.id), primary_key=True)
    position = db.Column(db.Integer)

    tool = relationship(Tool)
    question = relationship(Question)
    user = relationship(User)

    def __repr__(self):
        return "\n<Answer\n\tby:%s\n\ttool:%s\n\tposition:%s\n\tquestion:%s>\n" % (
                self.user, self.tool, self.position, self.question)


@app.route('/')
def front():
    app.logger.debug("YEAH")
    all_questions = Question.query.all()
    question_texts = json.dumps([question.text for question in all_questions])
    print question_texts
    return render_template('front.html', popular_questions=all_questions, question_texts=question_texts)


@app.route('/search')
def search():
    question_text = request.args.get('q','')
    search_results = []
    return render_template('search.html', question_text=question_text, search_results=search_results)


@app.route('/create', methods=['POST'])
def create():
    question_text = request.form['question']
    question = Question(question_text)
    db.session.add(question)
    db.session.commit()
    return redirect(question.url)

@app.route('/<id>/<slug>/edit', methods=['GET','POST'])
def edit_question(id, slug=''):
    question = Question.query.get_or_404(id)
    if request.method == 'POST':
        if request.form['button'] == 'delete':
            db.session.delete(question)
            return redirect(url_for('front'))
        else: # assume it's 'save'
            question.text = request.form['question']
            db.session.commit()
            return redirect(question.url)
    return render_template('edit.html', question=question)
    

@app.route('/<id>/<slug>')
def show(id, slug=''):
    question = Question.query.get_or_404(id)
    all_tools = Tool.query.all()
    tool_texts = json.dumps([tool.name for tool in all_tools])
    your_answers = question.get_answers(g.current_user)
    canonical_answers = question.top_answers 
    return render_template('show.html', question=question, tool_texts=tool_texts, 
            your_answers=your_answers, canonical_answers=canonical_answers)


@app.route('/answer/<question_id>', methods=['POST'])
def answer(question_id):
    tools = request.json
    question = Question.query.get_or_404(question_id)
    question.save_answer(g.current_user, tools)
    return 'success'


from pywebfinger import finger
from flaskext.openid import OpenID
oid = OpenID(app, 'log')

@app.route('/login', methods=['POST','GET'])
@oid.loginhandler
def login():
#    if g.current_user is not None:
#        return redirect(oid.get_next_url())
    if request.method == 'POST':
        email_address = request.form['email']
        info = finger(email_address, True)
        openid = info.open_id
        return oid.try_login(openid, ask_for=['email', 'fullname', 'nickname'])
    return oid.fetch_error()

@oid.after_login
def after_login(info):
    openid = info.identity_url
    session['openid'] = openid
    user = User.query.filter_by(openid=openid).first()
    if user is None:
        name = info.nickname or info.fullname
        user = User(name=name, openid=openid)
        db.session.add(user)
        db.session.commit()

    flash(u'Successfully signed in')
    return redirect(oid.get_next_url())

@app.route('/logout')
def logout():
    session.pop('openid', None)
    flash(u'You were signed out')
    return redirect(oid.get_next_url())



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080) #host='0.0.0.0', port=6000)

