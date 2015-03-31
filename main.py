import jinja2
import json
import logging
import os
import random
import webapp2

from google.appengine.api import users
from google.appengine.ext import ndb

from models import *


JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        os.path.join(os.path.dirname(__file__), 'templates')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class BaseRequestHandler(webapp2.RequestHandler):
    def __init__(self, request=None, response=None):
        super(BaseRequestHandler, self).__init__(request, response)
        self.template_name = None
        self.template_values = {}

    def complete_request(self):
        template = JINJA_ENVIRONMENT.get_template(self.template_name)
        self.template_values.update({
            'login_url': users.create_login_url(self.request.uri),
            'logout_url': users.create_logout_url('/home'),
            'user': users.get_current_user()
        })

        self.response.write(template.render(self.template_values))

    def require_login(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return True


class AboutPage(BaseRequestHandler):
    def get(self):
        self.template_name = 'about.html'
        self.complete_request()


class DashboardPage(BaseRequestHandler):
    def get(self):
        if self.require_login():
            return

        self.template_name = 'dashboard.html'
        self.complete_request()


class UserPage(BaseRequestHandler):
    def get(self):
        if self.require_login():
            return

        self.template_name = 'user.html'
        self.complete_request()


class ResponsePage(BaseRequestHandler):
    def get(self):
        if self.require_login():
            return

        self.template_name = 'respond.html'
        self.template_values = {
            'pin_default': 0
        }

        self.complete_request()

    def post(self):
        if self.require_login():
            return

        self.template_name = 'respond.html'
        pin = int(self.request.get('pin', -1))
        current_answer = self.request.get('answer')

        self.template_values = {
            'pin_default': pin,
            'current_answer': current_answer
        }

        self.complete_request()


class CreatePage(BaseRequestHandler):
    def get(self):
        if self.require_login():
            return

        self.template_name = 'create.html'
        self.complete_request()

    def post(self):
        user = users.get_current_user()
        if not user:
            self.error(401)
            return

        data = json.loads(self.request.body)
        quiz = Quiz()
        for q in data['questions']:
            question = Question(
                question=q['question'],
                answers=q['answers'],
                correct_answer=q['correctAnswer'])

            quiz.questions.append(question)

        quiz.name = data['name']
        quiz.userid = user.user_id()
        quiz.put()


class QuizPage(BaseRequestHandler):
    def get(self):
        if self.require_login():
            return

        user = users.get_current_user()
        self.template_name = 'quizzes.html'
        quizzes = Quiz.query(Quiz.userid == user.user_id()).fetch(10)
        self.template_values = {
            'quizzes': quizzes
        }

        self.complete_request()

class PresentAPI(BaseRequestHandler):
    def post(self):
        if self.require_login():
            return
            
        self.template_name = 'start.html'
        quiz_key = self.request.get('quiz')
        quiz_key = int(quiz_key)
        question_number = int(self.request.get('question'))
        quiz = Quiz.get_by_id(quiz_key, parent=None)
        
        if question_number==0:
            quiz.code = random.randint(1000,2000)
            quiz.put()
        
        if question_number >= 0 and question_number < len(quiz.questions):
            try:
                question = quiz.questions[question_number]
                question_number = question_number+1

            except IndexError:
                self.response.write('invalid question number')
                return

            self.template_values = {
                'code' : quiz.code,
                'quiz_key' : quiz_key,
                'question' : question.question,
                'answers' : question.answers,
                'question_number' : question_number,
                'total_questions' : len(quiz.questions)
            }
            
            self.complete_request()
            return
             

application = webapp2.WSGIApplication([
    ('/', AboutPage),
    ('/home', DashboardPage),
    ('/respond', ResponsePage),
    ('/create', CreatePage),
    ('/quizzes', QuizPage),
    ('/start', PresentAPI),
    ('/user', UserPage)
], debug=True)
