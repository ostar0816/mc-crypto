shore
=====

-----

Installation
------------

To install it, run

    $ pip install -r requirements.txt

Running
-------


To run Shore, run ``python manage.py runserver --settings=shore.settings --configuration=Dev`` (for dev mode),
run ``python manage.py runserver --settings=shore.settings --configuration=Prod`` (for prod mode)
on the command line. It starts a
local server that listens on http://localhost:8000.


Webpack configurations
----------------------

For webpack make sure that you have installed webpack globally (version 4.1.1)
``npm install webpack -g``.  Run ``npm install`` in shore/shore directory, then
``npm run dev`` or ``npm run dev-watch`` for DEBUG=True and ``npm run prod`` for DEBUG=False.


Database
--------

To create the PostgreSQL database, use the following commands:

.. code::

    $ sudo -u postgres -i
    # createdb shore
    # psql shore
    CREATE ROLE shore WITH LOGIN PASSWORD 'shore';
    GRANT ALL PRIVILEGES ON DATABASE shore TO shore;
    ALTER USER shore CREATEDB;
