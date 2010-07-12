from flask import Flask, render_template, request, redirect, url_for, abort
from flaskext.sqlalchemy import SQLAlchemy
from slugify import slugify
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:5sporks/bestlibs'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(80))

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Unicode(255))
    slug = db.Column(db.Unicode(255))

    def __init__(self, text):
        self.text = text
        self.slug = slugify(text)

    @property
    def url(self):
        return url_for('show', id=self.id, slug=self.slug)


class Tool(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(80))

class Affinity(db.Model):
    user_id = db.Column(db.Integer, ForeignKey(User.id), primary_key=True)
    question_id = db.Column(db.Integer, ForeignKey(Question.id), primary_key=True)
    tool_id = db.Column(db.Integer, ForeignKey(Tool.id), primary_key=True)
    position = db.Column(db.Integer)


import pymongo
from pymongo.objectid import ObjectId


@app.route('/')
def front():
    all_questions = Question.query.all()
    question_texts = json.dumps([question['text'] for question in all_questions])
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
    session.add(question)
    return redirect(question.url)


@app.route('/<id>/<slug>')
def show(id, slug):
    question = questions.find_one({'_id':ObjectId(id)})
    all_tools = list(tools.find())
    tool_texts = json.dumps([tool['name'] for tool in all_tools])
    return render_template('show.html', question=question, tool_texts=tool_texts)


@app.route('/associate_tool/<question_id>', methods=['POST'])
def associate_tool(question_id):
    question = questions.find_one({'_id':ObjectId(question_id)})
    if not question:
        abort(400)
    
    # create the tool if it doesn't exist
    tool_name = request.form['tool']
    if tool_name:
        tool = tools.find_one({'name':tool_name})
        if not tool:
            tool = {'name': tool_name}
            tools.insert(tool)

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
    app.run(debug=True, port=8080) #host='0.0.0.0', port=6000)

