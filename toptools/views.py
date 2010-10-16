from models import *

from flask import Flask, request, session, g, redirect, abort, url_for, render_template, flash
from pywebfinger import finger
from flaskext.openid import OpenID
import json
import logging

file_handler = logging.FileHandler("log/log.txt")
file_handler.setLevel(logging.DEBUG)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.DEBUG)
oid = OpenID(app, 'log')


@app.before_request
def set_current_user():
    if 'openid' in session:
        openid = session['openid']
        g.current_user = User.query.filter_by(openid=openid).first()
    else:
        g.current_user = None


@app.route('/')
def front():
    all_questions = Question.query.all()
    question_texts = json.dumps([question.text for question in all_questions])
    return render_template('front.html', popular_questions=all_questions, question_texts=question_texts)


@app.route('/search')
def search():
    question_text = request.args.get('q','')

    # If you used the autocomplete, there may be an exact match in the database
    matched_question = Question.query.filter(Question.text==question_text).first()
    if matched_question:
        return redirect(url_for('show', id=matched_question.id, slug=matched_question.slug))

    search_results = Question.query.all()
    return render_template('search.html', question_text=question_text, search_results=search_results)


@app.route('/create', methods=['POST'])
def create():
    if not g.current_user:
        abort(404)
    question_text = request.form['question']
    question = Question(question_text)
    db.session.add(question)
    db.session.commit()
    return redirect(question.url)


@app.route('/<id>/<slug>/edit', methods=['GET','POST'])
def edit_question(id, slug=''):
    question = Question.query.get_or_404(id)
    if question.created_by != g.current_user:
        abort(404)
    if request.method == 'POST':
        if request.form['button'].lower() == 'delete':
            db.session.delete(question)
            db.session.commit()
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
    if not g.current_user:
        abort(404)
    tools = request.json
    question = Question.query.get_or_404(question_id)
    question.save_answer(g.current_user, tools)
    return 'success'


@app.route('/login', methods=['POST','GET'])
@oid.loginhandler
def login():
    if g.current_user is not None:
        return redirect(oid.get_next_url())
    if request.method == 'POST':
        email = request.form['email']
        info = finger(email, True)
        if info.open_id:
            return oid.try_login(info.open_id, ask_for=['email', 'fullname', 'nickname'])
        else:
            return render_template('webfinger.html', email=email)
    return oid.fetch_error() or redirect(url_for('front'))


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
    if not g.current_user:
        abort(404)
    session.pop('openid', None)
    flash(u'You were signed out')
    return redirect(oid.get_next_url())

