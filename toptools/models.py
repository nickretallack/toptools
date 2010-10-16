from toptools import app
from flaskext.sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref, joinedload
from itertools import groupby
from slugify import slugify
from flask import Flask, request, session, g, redirect, abort, url_for, render_template, flash

from coalesce import coalesce_rankings

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://postgres:sporks@localhost/toptools'
app.config['SQLALCHEMY_ECHO'] = True
app.secret_key = "Secret key for testing purposes only"
db = SQLAlchemy(app)

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


