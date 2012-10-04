import re
from datetime import datetime
from urlparse import urljoin
from flask import Flask, render_template, make_response, \
                  request as flask_request
import requests
app = Flask(__name__)


tent_mime = 'application/vnd.tent.v0+json'


@app.route('/')
def front_page():
    return render_template('index.html')


@app.route('/feed')
def user_feed():
    tent_uri = flask_request.args.get('uri', '')
    app.logger.debug('tent_uri is %s' % tent_uri)
    if tent_uri == '':
        return 'No URI!'
    try:
        r = requests.get(tent_uri, timeout=5)
    except requests.ConnectionError as e:
        app.logger.debug('Connection to %s failed: %s' % (tent_uri, repr(e)))
        return "Can't connect to %s" % tent_uri

    # Look for profile links in the HTTP "link" header and get API roots
    # list from the first profile link that works.
    # TODO: Should also look for HTML "link" tag in response content
    apiroots = None
    links = r.headers['link']
    if links is None or links == '':
        return 'Missing HTTP link header'
    for link in re.split(',\s*', links):
        pattern = '''<([^>]+)>; rel="(https?://[^\"]+)"\s*$'''
        try:
            href, rel = re.match(pattern, link).groups()
        except AttributeError:
            continue # try next link, this one didn't parse

        app.logger.debug('link: %s, rel=%s' % (href, rel))
        if rel != 'https://tent.io/rels/profile':
            continue

        # convert relative link (like "/profile") to absolute
        href = urljoin(tent_uri, href)

        headers = {'accept': tent_mime}
        try:
            r = requests.get(href, timeout=5, headers=headers)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            app.logger.debug('exception loading %s: %s' % (href, repr(e)))
            continue

        # profile link worked, use it
        apiroots = r.json['https://tent.io/types/info/core/v0.1.0']['servers']
        break

    if apiroots is None or len(apiroots) == 0:
        return "No API roots found!"

    args = {'limit': '10',
            'post_types': 'https://tent.io/types/post/status/v0.1.0'}
    headers = {'accept': tent_mime}
    posts = None
    for root in apiroots:
        url = root + "/posts"
        try:
            r = requests.get(url, timeout=5, headers=headers, params=args)
            r.raise_for_status()
        except requests.exceptions.RequestException as e:
            app.logger.debug('exception when getting %s: %s' % (url, repr(e)))
            continue

        posts = r.json
        if posts is None:
            app.logger.debug('%s returned no valid JSON' % url)
        else:
            break

    toBool = lambda v: (v.lower() != "false" and v != "0")
    if not flask_request.args.get('include_replies', True, toBool):
      posts = [post for post in posts if post['content']['text'][0] != '^']

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

        post['post_guid'] = root + '/posts/' + post['id']
        m = re.match('''https://(\w+)\.tent\.is/tent$''', root)
        if m is not None:  # This is a Tent.is user
            post['post_link'] = 'https://' + m.groups()[0] \
                              + '.tent.is/posts/' + post['id']

        dt = datetime.utcfromtimestamp(int(post['published_at']))
        # We don't know the actual timezone in which the user made this
        # post, but UNIX timestamps are UTC-based so we hardcode +0000.
        post['rfc822_time'] = dt.strftime('%a, %d %b %Y %H:%M:%S +0000')

    response = make_response(render_template('feed.xml',
                                              posts=posts, uri=tent_uri,
                                              root=root))
    response.mimetype = 'application/xml'
    return response

if __name__ == '__main__':
    app.run()
