import click, pytest, sys, os
from flask.cli import with_appcontext, AppGroup

from App import create_app
from App.database import db, get_migrate
from App.models import User
from App.controllers import ( create_user, get_all_users_json, get_all_users, initialize )


sys.path.insert(0, os.path.dirname(__file__))

app = create_app()
migrate = get_migrate(app)

# This command creates and initializes the database
@app.cli.command("init", help="Creates and initializes the database")
def init():
    """Initialize the database."""
    db.create_all()
    initialize()
    print('database initialized')

'''
User Commands
'''


# eg : flask user <command>
user_cli = AppGroup('user', help='User object commands') 

# Then define the command and any parameters and annotate it with the group (@)
@user_cli.command("create", help="Creates a user")
@click.argument("firstname", default="rob")
@click.argument("lastname", default="bob")
@click.argument("username", default="rob")
@click.argument("email", default="rob@email.com")
@click.argument("password", default="robpass")
def create_user_command(firstname, lastname, username, email, password):
    create_user(firstname, lastname, username, email, password)
    print(f'{username} created!')

@user_cli.command("list", help="Lists users in the database")
@click.argument("format", default="string")
def list_user_command(format):
    if format == 'string':
        print(get_all_users())
    else:
        print(get_all_users_json())

app.cli.add_command(user_cli) # add the group to the cli

'''
Test Commands
'''

test = AppGroup('test', help='Testing commands') 

@test.command("user", help="Run User tests")
@click.argument("type", default="all")
def user_tests_command(type):
    if type == "unit":
        sys.exit(pytest.main(["-k", "UserUnitTests"]))
    elif type == "int":
        sys.exit(pytest.main(["-k", "UserIntegrationTests"]))
    else:
        sys.exit(pytest.main(["-k", "App"]))
    
app.cli.add_command(test)

if __name__ == "__main__":
    app.run()