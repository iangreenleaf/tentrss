import re
import os
from datetime import datetime
from urlparse import urljoin
from flask import Flask, render_template, make_response, url_for, \
                  request as flask_request
import requests
app = Flask(__name__)

def get_latest_posts(tent_uri):
    app.logger.debug('tent_uri is %s' % tent_uri)
    if tent_uri == '':
        return None, None, 'No URI!'
    try:
        r = requests.get(tent_uri, timeout=5)
    except requests.ConnectionError as e:
        app.logger.debug('Connection to %s failed: %s' % (tent_uri, repr(e)))
        return None, None, "Can't connect to %s" % tent_uri

    # Look for profile links in the HTTP "link" header and get API roots
    # list from the first profile link that works.
    # TODO: Should also look for HTML "link" tag in response content
    apiroots = None
    links = r.headers['link']
    if links is None or links == '':
        return None, None, 'Missing HTTP link header'
    for link in re.split(',\s*', links):
        pattern = '''<([^>]+)>; rel="(https?://[^\"]+)"\s*$'''
        try:
            href, rel = re.match(pattern, link).groups()
        except AttributeError:
            continue # try next link, this one didn't parse

        app.logger.debug('link: %s, rel=%s' % (href, rel))
        if rel != 'https://tent.io/rels/meta-post':
            continue

        # convert relative link (like "/profile") to absolute
        href = urljoin(tent_uri, href)

        headers = {'accept': 'application/vnd.tent.post.v0+json'}
        try:
            r = requests.get(href, timeout=5, headers=headers)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            app.logger.debug('exception loading %s: %s' % (href, repr(e)))
            continue

        # profile link worked, use it
        apiroots = r.json['post']['content']['servers']
        break

    if apiroots is None or len(apiroots) == 0:
        return None, None, "No API roots found!"

    args = {'limit': '40',
            'types': 'https://tent.io/types/status/v0'}
    headers = {'accept': 'application/vnd.tent.posts-feed.v0+json'}
    posts = None
    for root in apiroots:
        url = root['urls']['posts_feed']
        try:
            r = requests.get(url, timeout=5, headers=headers, params=args)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            app.logger.debug('exception when getting %s: %s' % (url, repr(e)))
            continue

        posts = r.json['posts']
        if posts is None:
            app.logger.debug('%s returned no valid JSON' % url)
        else:
            break

    toBool = lambda v: (v.lower() != "false" and v != "0")
    if not flask_request.args.get('include_replies', True, toBool):
      posts = [post for post in posts if post['content']['text'] and post['content']['text'][0] != '^']

    if flask_request.args.get('uri', '').find('iangreenleaf') > -1:
      posts = [post for post in posts if post['content']['text'] and post['content']['text'].find("M$") != 0]

    # prepare info the template needs
    for post in posts:
        # The protocol unfortunately does not give us a canonical URL for
        # opening a post in a web browser. We can come up with a URL that
        # that returns each individual post as raw JSON, but that's it.
        #
        # So, for user-friendliness use the JSON URL only as a GUID, but
        # not a link (it will try to download a JSON file). For the time
        # being at least, we will special-case https://username.tent.is/
        # entities and provide a link in those cases only.

        # Cheating here, I should be using 'posts' not 'posts_feed'
        post['post_guid'] = root['urls']['posts_feed'] + '/posts/' + post['id']
        m = re.match('''https://(\w+)\.cupcake\.is$''', post['entity'])
        if m is not None:  # This is a Tent.is user
            post['post_link'] = 'https://micro.cupcake.io/posts/' + post['id']

        dt = datetime.utcfromtimestamp(int(post['published_at']) / 1000)
        # We don't know the actual timezone in which the user made this
        # post, but UNIX timestamps are UTC-based so we hardcode +0000.
        post['rfc822_time'] = dt.strftime('%a, %d %b %Y %H:%M:%S +0000')

    return posts, root, None


@app.route('/')
def front_page():
    tent_uri = flask_request.args.get('uri', '')
    if tent_uri is None or tent_uri == '':
        return render_template('index.html')
    posts, root, error = get_latest_posts(tent_uri)

    if error is None:
        # Generating the correct full absolute URL, given proxying,
        # is hard! This needs an nginx directive to set the made-up
        # X-Original-Request-URI header if proxying.
        feed_url = urljoin(flask_request.host_url,
                           flask_request.headers.get('X-Original-Request-URI',
                                                     '/'))
        feed_url = urljoin(feed_url,
                           '.' + url_for('user_feed') + '?uri=' + tent_uri)
        return render_template('feed.html', posts=posts, uri=tent_uri,
                               root=root, feed_url=feed_url)

    return render_template('error.html', uri=tent_uri, error=error), 404


@app.route('/feed')
def user_feed():
    tent_uri = flask_request.args.get('uri', '')
    posts, root, error = get_latest_posts(tent_uri)

    if error is None:
        response = make_response(render_template('feed.xml',
                                                  posts=posts, uri=tent_uri,
                                                  root=root))
        response.mimetype = 'application/xml'
        return response

    return render_template('error.html', uri=tent_uri, error=error), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
