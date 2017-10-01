Development
===========

Pull Requests
-------------

- Submit Pull Requests against the `master` branch.
- Provide a good description of what you're doing and why.
- Provide tests that cover your changes and try to run the tests locally first.

**Example**. Assuming you set up GitHub account, forked wheel repository from
https://github.com/pypa/wheel to your own page via web interface, and your
fork is located at https://github.com/yourname/wheel

::

  $ git clone git@github.com:pypa/wheel.git
  $ cd wheel
  # ...
  $ git diff
  $ git add <modified> ...
  $ git status
  $ git commit

You may reference relevant issues in commit messages (like #1259) to
make GitHub link issues and commits together, and with phrase like
"fixes #1259" you can even close relevant issues automatically. Now
push the changes to your fork::

  $ git push git@github.com:yourname/wheel.git

Open Pull Requests page at https://github.com/yourname/wheel/pulls and
click "New pull request". That's it.
