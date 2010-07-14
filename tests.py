import unittest
from main import app, db

class Tests(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:5sporks@localhost/bestlibs_test'
        self.app = app.test_client()
        db.create_all()

    def tearDown(self):
        db.drop_all()

    def test_something(self):
        print "hello"

if __name__ == '__main__':
    unittest.main()
