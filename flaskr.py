# -*- coding: utf-8 -*-
"""
    Flaskr
    ~~~~~~

    A microblog example application written as Flask tutorial with
    Flask and sqlite3.

    :copyright: (c) 2010 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement
from sqlite3 import dbapi2 as sqlite3
from contextlib import closing
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
from flask.ext.principal import (
    Principal, Identity, identity_changed, identity_loaded, Need, Permission,
    AnonymousIdentity)


# configuration
DATABASE = '/tmp/flaskr.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

# initialize flask-principal
principals = Principal(app)


@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    print '>' * 10, 'on_identity_loaded()'
    if identity.name == 'admin':
        identity.provides.add(Need('my_method', 'my_value'))


def connect_db():
    """Returns a new connection to the database."""
    return sqlite3.connect(app.config['DATABASE'])


def init_db():
    """Creates the database tables."""
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()


@app.before_request
def before_request():
    """Make sure we are connected to the database each request."""
    g.db = connect_db()


@app.teardown_request
def teardown_request(exception):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'db'):
        g.db.close()


@app.route('/')
def show_entries():
    my_permission = Permission(Need('my_method', 'my_value'))
    if my_permission.can():
        permitted = True
    else:
        permitted = False

    cur = g.db.execute('select title, text from entries order by id desc')
    entries = [dict(title=row[0], text=row[1]) for row in cur.fetchall()]
    return render_template('show_entries.html', entries=entries, permitted=permitted)


@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    g.db.execute('insert into entries (title, text) values (?, ?)',
                 [request.form['title'], request.form['text']])
    g.db.commit()
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            identity_changed.send(app, identity=Identity(request.form['username']))

            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    identity_changed.send(app, identity=AnonymousIdentity())

    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


if __name__ == '__main__':
    app.run()
