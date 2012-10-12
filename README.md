TentRSS
=======

Script to show public [Tent](https://tent.io/) status posts as an RSS feed.

Based on [Flask](http://flask.pocoo.org/).
See Flask's install instructions to get this running.

This is a fork
--------------

This is a fork of [graue/tentrss](https://github.com/graue/tentrss).
The primary addition is the ability to pass `include_replies=0` in the URL
and receive an RSS feed with ^-replies excluded.

Useful for pushing your content to other networks, like [Twitter](https://ifttt.com/recipes/60394).

Use it
------

Find it at http://tentrss.herokuapp.com/.

A typical feed URL will look like this:
http://tentrss.herokuapp.com/feed?include_replies=0&uri=http%3A%2F%2Fiangreenleaf.tent.is%2F
