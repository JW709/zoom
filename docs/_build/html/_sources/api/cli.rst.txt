Zoom CLI
========

- zoom database [ < options > ]

    - manage the database


- zoom new [] [name]

    - create an app


- zoom server [] [instance]

    - run an instance using Python's builtin HTTP server


- zoom setup [] [name]

     - set up a new Zoom instance




zoom database
-------------
| usage: zoom database {database name} [options]  ...
| required: database name and command
| commands:

- create
- list
- show
- setup

| optional arguments:

-   -help, - -help

        - show this help message and exit

-   -e ENGINE, - -engine ENGINE

        - database engine (sqlite3 or mysql)
        - defaults to 'sqlite3'

-   -H HOST, - -host HOST

        - database host
        - defaults to 'localhost'

-   -d DATABASE, - -database DATABASE

        - database name
        - defaults to zoomdata

-   -P PORT, - -port PORT

        - database service port
        - defaults to '3306'

-   -u [USER], - -user [USER]

        - database username
        - defaults to 'zoomuser'


-   -p [PASSWORD], - -password [PASSWORD]

        - database password
        - defaults to 'zoompass'


-   -v, - -verbose

        - verbose console logging


-   -f, - -force

        - force database creation (drop existing)