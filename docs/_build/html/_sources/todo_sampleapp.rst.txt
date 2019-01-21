=======================
Application Development
=======================

This tutorial will walk you through creating a new application and cover aspects from basic application structure, controllers and storage, to generating fake data and model properties. At the end you will have a functioning ToDo application.

- Part 1: Creation and Basic structure
- Part 2: Controllers and storage
- Part 3: Fake Data, Model Properties, and Deleting

====================================
Part 1: Creation and Basic structure
====================================

Covered in this section:

- Setting the stage
- General application structure
- Define content for the Team page
- Define content for the Overview page

-----------------
Setting the stage
-----------------

Actions covered in this step:
    - Workstation update 
    - Use ``zoom new`` to create a new app using the default template
    - Start local zoom server

End results:
    - New ``todo`` applicaiton created with:
        - app.py
        - index.py
        - config.ini

Key concepts with further reading (if available):
    - update_local_workstation
    - zoom new
    - run_local_server

--------------------------
Creating a new application
--------------------------

Zoom comes with a built in command to create all the files necessary to create a new application complete with a default template. 

1. ``cd`` to the directory where you want to create your app
    ``cd ~work``

2. ``zoom new todo``

Inspecting the contents of that directory you will see (at a minimum) the files:

    - app.py
        Every Zoom application is required to provide a module called app.py stored in the main folder for the application, which, when called, returns content for the browser.

        Through this single python program, your program will be able to provide everything from simple pages to complex visualizations and dashboards. Zoom provides many convenient tools to accomplish this with very little programming.

    - config.ini
        The config.ini file contains application settings which might include things like the application title.

    - index.py
        The index.py file contains the index or default views for the application (we will discuss more about views later in the document).

3. Open ``app.py``, this is where you will see your main application menu. We want to add two new menu items, a team page and a task page. 

    ``app.menu = 'Overview', 'About', 'Tasks', 'Team'``

If you click on our new menu items you will get a 404, this is expected as we haven't built any content yet! We are now done working with this module.

4. Open ``index.py`` to start adding functionality. To serve something from the task page create a member in the index view. Zoom will look in index.py for the ``main`` dispatcher, in this case we're calling the view. 

-----------------------------
General application structure
-----------------------------

Actions covered in this
    - Add items to the application menu - editing app.py
    - Define views/pages for the new menu items - editing index.py step:

Results at the end of this step:
    - Team menu items displayed
    - Static, simple content displayed for each of the new menu items