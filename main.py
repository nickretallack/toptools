from flask import Flask, render_template, request, redirect, url_for, abort
from slugify import slugify
import json
app = Flask(__name__)

import pymongo
from pymongo.objectid import ObjectId

db_connection = pymongo.Connection()
db = db_connection['bestlibs']
questions = db.questions
tools = db.tools
question_tools = db.question_tools

@app.after_request
def close_mongo_session(response):
    db_connection.end_request()
    return response



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

