from flask import Flask, render_template, request, redirect, url_for, abort
from slugify import slugify
import json
app = Flask(__name__)

#from sqlalchemy import create_engine, MetaData
#engine = create_engine('mysql://', convert_unicode=True)
#metadata = MetaData(bind=engine



PASSWORD = '5spoons'

import pymongo
from pymongo.objectid import ObjectId

db_connection = pymongo.Connection()
db = db_connection['bestlibs']
questions = db.questions
tools = db.tools
question_tools = db.question_tools


#def question_texts():
#    all_questions = questions.find()
#    texts = [question.text for question in all_questions]
#    return json.dumps[texts]





@app.route('/')
def front():
    all_questions = list(questions.find())
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
    slug = slugify(question_text)
    question = {'text': question_text, 'slug':slug}
    questions.insert(question)
    return redirect(question_url(question))


@app.route('/<id>/<slug>')
def show(id, slug):
    question = questions.find_one({'_id':ObjectId(id)})

    return render_template('show.html', question=question)


@app.route('/associate_tool/<question_id>', methods=['POST'])
def associate_tool(question_id):
    question = questions.find_one({'_id':ObjectId(id)})
    if not question:
        abort(400)

    # create the tool
    tool_name = request.form['tool']
    tool = {'name': tool_name}
    tools.insert(tool)

    # Automatically vote that this tool is related to this question
    question_tool = {'tool':tool['_id'], 'question':question['_id']}
    question_tools.insert(question_tool)
    return redirect(question_url(question))


def question_url(question):
    return url_for('show', id=question['_id'], slug=question['slug'])


app.jinja_env.globals['question_url'] = question_url


if __name__ == '__main__':
    app.run(debug=True, port=8080) #host='0.0.0.0', port=6000)

