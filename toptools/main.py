from flask import Flask, request, session, g, redirect, abort, url_for, render_template, flash
from flaskext.sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref, joinedload
from slugify import slugify
import json
from itertools import groupby
from coalesce import coalesce_rankings

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

