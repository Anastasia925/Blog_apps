import sqlalchemy as sa
import sqlalchemy.orm as so
from app import app, db
from app.models import User, Post


@app.shell_context_processor
def make_shell_context():
    """
    Creates a shell context
    that adds the database instance
    and models to the shell session
     """
    return {'sa': sa, 'so': so, 'db': db, 'User': User, 'Post': Post}


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
