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

Example nginx proxy configuration
---------------------------------

    location /tentrss/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_redirect default;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_set_header X-Original-Request-URI $request_uri;
    }

The X-Original-Request-URI header allows TentRSS to generate a correct
URL to the resulting feed.
