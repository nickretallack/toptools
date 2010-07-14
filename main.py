from flask import Flask, render_template, request, redirect, url_for, abort, g
from flaskext.sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref
from slugify import slugify
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:5sporks@localhost/bestlibs'
db = SQLAlchemy(app)

import logging
file_handler = logging.FileHandler("log.txt")
file_handler.setLevel(logging.DEBUG)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.DEBUG)


@app.before_request
def set_current_user():
    g.current_user = User.query.get(1)



class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(80))

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

    @property
    def url(self):
        return url_for('show', id=self.id, slug=self.slug)

    @property
    def edit_url(self):
        return url_for('edit_question', id=self.id, slug=self.slug)
    

class Tool(db.Model):
    __tablename__ = 'tools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(80))

class Answer(db.Model):
    __tablename__ = 'answers'
    user_id = db.Column(db.Integer, ForeignKey(User.id), primary_key=True)
    question_id = db.Column(db.Integer, ForeignKey(Question.id), primary_key=True)
    tool_id = db.Column(db.Integer, ForeignKey(Tool.id), primary_key=True)
    position = db.Column(db.Integer)

    tool = relationship(Tool)
    question = relationship(Question)
    user = relationship(User)


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
    your_answers = Tool.query.join(Answer).filter(Answer.question_id==id).filter(Answer.user_id==g.current_user.id
            ).order_by(Answer.position.asc()).all()
    return render_template('show.html', question=question, tool_texts=tool_texts, your_answers=your_answers)


@app.route('/answer/<question_id>', methods=['POST'])
def answer(question_id):
    tools = request.json
    question = Question.query.get_or_404(question_id)

    # delete existing answers for this user,question
    db.session.query(Answer).filter_by(question=question, user=g.current_user).delete()

    for position, name in enumerate(tools):
        # find or create the tool.
        # NOTE: could speed this up by doing an 'IN' query earlier
        tool = Tool.query.filter_by(name=name).first()
        if not tool:
            tool = Tool(name=name)
            db.session.add(tool)

        answer = Answer(tool=tool, question=question, user=g.current_user, position=position)
        db.session.add(answer)

    db.session.commit()
    return ''


@app.route('/associate_tool/<question_id>', methods=['POST'])
def associate_tool(question_id):
    question = Question.query.get_or_404(question_id)
    
    # create the tool if it doesn't exist
    tool_name = request.form['tool']
    if tool_name:
        tool = Tool.query.filter_by(name=tool_name).first()
        if not tool:
            tool = Tool(name=tool_name)
            db.session.add(tool)

        # TODO
        # associate it with the question
        if 'tools' not in question:
            question['tools'] = []

        if not question_has_tool(question, tool):
            question['tools'].append({'id':tool['_id'], 'name':tool['name']})
            questions.save(question)
    
    return redirect(question_url(question))


def question_url(question):
    return url_for('show', id=question['_id'], slug=question['slug'])

def question_has_tool(question, tool):
    for item in question['tools']:
        if 'name' in item and 'name' in tool and item['name'] == tool['name']:
            return True
    return False



app.jinja_env.globals['question_url'] = question_url


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080) #host='0.0.0.0', port=6000)

