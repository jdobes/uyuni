# -*- coding: utf-8 -*-
#
# Copyright (c) 2010, 2011, 2012 Novell
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import re
import urlparse

import pycurl

# prevent build dependency cycles
# pylint: disable=W0611
from suseRegister.info import getProductProfile, parseProductProfileFile
from spacewalk.common.rhnLog import log_debug, log_error
from spacewalk.common.rhnException import rhnFault
from spacewalk.common.rhnConfig import initCFG, CFG, ConfigParserError
from spacewalk.server import rhnSQL

YAST_PROXY = "/root/.curlrc"
SYS_PROXY = "/etc/sysconfig/proxy"


class TransferException(Exception):
    """Transfer Error"""
    def __init__(self, value=None):
        Exception.__init__(self)
        self.value = value

    def __str__(self):
        return "%s" % self.value

    def __unicode__(self):
        return '%s' % unicode(self.value, "utf-8")


class URL(object):
    """URL class that allows modifying the various attributes of a URL"""
    # pylint: disable=R0902
    def __init__(self, url, username=None, password=None):
        u = urlparse.urlsplit(url)
        # pylint can't see inside the SplitResult class
        # pylint: disable=E1103
        self.scheme = u.scheme
        self.username = username or u.username
        self.password = password or u.password
        self.host = u.hostname
        self.port = u.port
        self.path = u.path
        self.query = u.query
        self.fragment = u.fragment

        if self.query:
            self._parse_query()

    def get_query_param(self, key, default=None):
        """Return a query parameter

        Note: this assumes that the parameter contains at most a single
        element (not a list).

        """
        # paramsdict has a list of elements as values, but we assume the
        # most common case where the list has only one element
        # pylint: disable=E1101
        p = self.paramsdict.get(key, default)
        if p:
            assert len(p) == 1, ("The query parameter contains a list of "
                                 "arguments instead of a single element. "
                                 "%s : %s" % (key, p))
            p = p[0]
        return p

    def __setattr__(self, attr, value):
        if attr == "query":
            self.__dict__[attr] = value.lstrip("?")
            self._parse_query()
        # pylint: disable=E1101
        elif attr == "paramsdict":
            # query should be used instead
            raise AttributeError("can't set attribute")
        else:
            self.__dict__[attr] = value

    def _parse_query(self):
        """Parse self.query and populate self.paramsdict

        self.paramsdict is a dict of key: [value1, value2, value3]

        """
        self.__dict__["paramsdict"] = urlparse.parse_qs(self.query)

    def getURL(self, stripPw=False):
        """Return the full url as a string"""
        netloc = ""
        if self.username:
            netloc = self.username
        if self.password and not stripPw:
            netloc = '%s:%s' % (netloc, self.password)
        elif self.password and stripPw:
            netloc = '%s:%s' % (netloc, '<secret>')
        if self.host and netloc :
            netloc = '%s@%s' % (netloc, self.host)
        elif self.host:
            netloc = self.host

        if self.port:
            netloc = '%s:%s' % (netloc, self.port)

        return urlparse.urlunsplit((self.scheme, netloc, self.path,
                                    self.query, self.fragment))


def send(url, sendData=None):
    """Connect to ncc and return the XML document as stringIO

    :arg url: the url where the request will be sent
    :kwarg sendData: do a post-request when "sendData" is given.

    Returns the XML document as stringIO object.

    """
    connect_retries = 10
    try_counter = connect_retries
    curl = pycurl.Curl()

    curl.setopt(pycurl.URL, url)
    proxy_url, proxy_user, proxy_pass = get_proxy()
    if proxy_url:
        curl.setopt(pycurl.PROXY, proxy_url)
    log_debug(2, "Connect to %s" % url)
    if sendData is not None:
        curl.setopt(pycurl.POSTFIELDS, sendData)

    # We implement our own redirection-following, because pycurl
    # 7.19 doesn't POST after it gets redirected. Ideally we'd be
    # using pycurl.POSTREDIR here, but that's in 7.21.
    curl.setopt(pycurl.FOLLOWLOCATION, False)

    response = StringIO()
    curl.setopt(pycurl.WRITEFUNCTION, response.write)

    try_counter = connect_retries
    while try_counter:
        try_counter -= 1
        try:
            curl.perform()
        except pycurl.error, e:
            if e[0] == 56: # Proxy requires authentication
                log_debug(2, e[1])
                if not (proxy_user and proxy_pass):
                    raise TransferException("Proxy requires authentication, "
                                            "but reading credentials from "
                                            "%s failed." % YAST_PROXY)
                curl.setopt(pycurl.PROXYUSERPWD,
                            "%s:%s" % (proxy_user, proxy_pass))
            elif e[0] == 60:
                log_error("Peer certificate could not be authenticated "
                          "with known CA certificates.")
                raise TransferException("Peer certificate could not be "
                                        "authenticated with known CA "
                                        "certificates.")
            else:
                log_error(e[1])
                raise

        status = curl.getinfo(pycurl.HTTP_CODE)
        if status == 200 or (URL(url).scheme == "file" and status == 0):
            # OK or file
            break
        elif status in (301, 302): # redirects
            url = curl.getinfo(pycurl.REDIRECT_URL)
            log_debug(2, "Got redirect to %s" % url)
            curl.setopt(pycurl.URL, url)
    else:
        log_error("Connecting to %s has failed after %s "
                  "tries with HTTP error code %s." %
                  (URL(url).getURL(stripPw=True), connect_retries, status))
        raise TransferException("Connection failed after %s tries with "
                                "HTTP error %s." % (connect_retries, status))

    # StringIO.write leaves the cursor at the end of the file
    response.seek(0)
    return response


def accessible(url):
    """Try if url is accessible

    :arg url: the url which is tried to access

    Returns True if url is accessible, otherwise False.

    """
    curl = pycurl.Curl()

    curl.setopt(pycurl.URL, url)
    proxy_url, proxy_user, proxy_pass = get_proxy()
    if proxy_url:
        curl.setopt(pycurl.PROXY, proxy_url)
    log_debug(2, "Connect to %s" % url)

    # We implement our own redirection-following, because pycurl
    # 7.19 doesn't POST after it gets redirected. Ideally we'd be
    # using pycurl.POSTREDIR here, but that's in 7.21.
    curl.setopt(pycurl.FOLLOWLOCATION, False)
    curl.setopt(pycurl.NOBODY, True)

    try_counter = 5
    while try_counter:
        try_counter -= 1
        try:
            curl.perform()
        except pycurl.error, e:
            if e[0] == 56: # Proxy requires authentication
                log_debug(2, e[1])
                if not (proxy_user and proxy_pass):
                    raise TransferException("Proxy requires authentication, "
                                            "but reading credentials from "
                                            "%s failed." % YAST_PROXY)
                curl.setopt(pycurl.PROXYUSERPWD,
                            "%s:%s" % (proxy_user, proxy_pass))
            else:
                break

        status = curl.getinfo(pycurl.HTTP_CODE)
        if status == 200 or (URL(url).scheme == "file" and status == 0): # OK or file
            return True
        elif status in (301, 302): # redirects
            url = curl.getinfo(pycurl.REDIRECT_URL)
            log_debug(2, "Got redirect to %s" % url)
            curl.setopt(pycurl.URL, url)
        elif status >= 400:
            break
    return False


def get_proxy():
    """Return proxy information as a (url, username, password) tuple

    Returns None if no proxy URL/credentials could be read.

    Order of lookup (https_proxy is always preferred over http_proxy):
    1. rhn.conf (server.satellite.http_proxy)
    2. .curlrc (--proxy, --proxy-user)

    """
    return (_get_proxy_from_rhn_conf() or
            _get_proxy_from_yast() or
            (None, None, None))


def findProduct(product):
    q_version = ""
    q_release = ""
    q_arch    = ""
    product_id = None
    product_lower = {}
    product_lower['name'] = product['name'].lower()

    log_debug(2, "Search for product: %s" % product)

    if product.get('version'):
        q_version = "or sp.version = :version"
        product_lower['version'] = product['version'].lower()
    if product.get('release'):
        q_release = "or sp.release = :release"
        product_lower['release'] = product['release'].lower()
    if product.get('arch'):
        q_arch = "or pat.label = :arch"
        product_lower['arch'] = product['arch'].lower()

    h = rhnSQL.prepare("""
    SELECT sp.id, sp.name, sp.version, pat.label as arch, sp.release
       FROM suseProducts sp
       LEFT JOIN rhnPackageArch pat ON pat.id = sp.arch_type_id
    WHERE sp.name = :name
       AND (sp.version IS NULL %s)
       AND (sp.release IS NULL %s)
       AND (sp.arch_type_id IS NULL %s)
    ORDER BY name, version, release, arch
    """ % (q_version, q_release, q_arch))
    h.execute(**product_lower)
    rs = h.fetchall_dict()

    if not rs:
        log_debug(1, "No Product Found")
        return None

    product_id = rs[0]['id']

    if len(rs) > 1:
        # more than one product matches.
        # search for an exact match or take the first
        for p in rs:
            if (p['version'] == product['version'] and
                p['release'] == product['release'] and
                p['arch'] == product['arch']):
                product_id = p['id']
                break

    return product_id


def channelForProduct(product, ostarget, parent_id=None, org_id=None,
                      user_id=None):
    """Find Channels for a given product and ostarget.

    If parent_id is None, a base channel is requested.
    Otherwise only channels are returned which have this id
    as parent channel.
    org_id and user_id are used to check for permissions.

    """

    product_id = findProduct(product)
    if not product_id:
        return None

    vals = {
        'pid'      : product_id,
        'ostarget' : ostarget,
        'org_id'   : org_id,
        'user_id'  : user_id
        }
    parent_statement = " IS NULL "
    if parent_id:
        parent_statement = " = :parent_id "
        vals['parent_id'] = parent_id

    h = rhnSQL.prepare("""
        SELECT ca.label arch,
        c.id,
        c.parent_channel,
        c.org_id,
        c.label,
        c.name,
        c.summary,
        c.description,
        to_char(c.last_modified, 'YYYYMMDDHH24MISS') last_modified,
        rhn_channel.available_chan_subscriptions(c.id, :org_id) available_subscriptions,
        -- If user_id is null, then the channel is subscribable
        rhn_channel.loose_user_role_check(c.id, :user_id, 'subscribe') subscribable
        FROM rhnChannel c
        JOIN suseProductChannel spc ON spc.channel_id = c.id
        JOIN suseOSTarget sot ON sot.channel_arch_id = c.channel_arch_id
        JOIN rhnChannelArch ca ON c.channel_arch_id = ca.id
        WHERE spc.product_id = :pid
          AND sot.os = :ostarget
          AND c.parent_channel %s""" % parent_statement)
    h.execute(**vals)
    rs = h.fetchall_dict()
    if not rs:
        log_debug(1, "No Channel Found")
        return None
    ret = []
    for channel in rs:
        subscribable = channel['subscribable']
        del channel['subscribable']

        if not subscribable:
            # Not allowed to subscribe to this channel
            continue

        ret.append(channel)
        log_debug(1, "Found channel %s with id %d" % (channel['label'], channel['id']))

    if ret == []:
        ret = None
    return ret


def get_mirror_credentials():
    """Return a list of mirror credential tuples (user, pass)

    N.B. The config values will be read from the global configuration:
     server.susemanager.mirrcred_user
     server.susemanager.mirrcred_pass
     server.susemanager.mirrcred_user_1
     server.susemanager.mirrcred_pass_1
     etc.

    The credentials are read sequentially, when the first value is found
    to be missing, the process is aborted and the list of credentials
    that have been read so far are returned. For example if
    server.susemanager.mirrcred_pass_1 can not be read, only the first
    pair of default mirrcreds will be returned, even though
    mirrcred_user_2, mirrcred_pass_2 etc. might still exist.

    """
    initCFG("server.susemanager")

    creds = []

    # the default values should at least always be there
    if not CFG["mirrcred_user"] or not CFG["mirrcred_pass"]:
        raise ConfigParserError("Could not read default mirror credentials: "
                                "server.susemanager.mirrcred_user, "
                                "server.susemanager.mirrcred_pass.")

    creds.append((CFG["mirrcred_user"], CFG["mirrcred_pass"]))

    # increment the credentials number, until we can't read one
    n = 1
    while True:
        try:
            creds.append((CFG["mirrcred_user_%s" % n],
                          CFG["mirrcred_pass_%s" % n]))
        except (KeyError, AttributeError):
            break
        n += 1
    return creds


def _parse_curl_proxy_credentials(text):
    """Parse proxy credentials from the string :text:

    Return a (username, password) tuple or (None, None).

    """
    try:
        user_pass = re.search('^[\s-]+proxy-user\s*=?\s*"([^:]+:.+)"\s*$',
                              text, re.M).group(1)
    except AttributeError:
        return (None, None)

    return re.sub('\\\\"', '"', user_pass).split(":")


def _parse_curl_proxy_url(text):
    try:
        return re.search('^[\s-]+proxy\s*=?\s*"(.+)"\s*$',
                         text, re.M).group(1)
    except AttributeError:
        return None


def _get_proxy_from_yast():
    """Return a tuple of (url, user, pass) proxy information from YaST

    Returns None instead of a tuple if there was no proxy url. user,
    pass can be None.

    """
    try:
        with open(YAST_PROXY) as f:
            contents = f.read()
    except IOError:
        log_debug(1, "Couldn't open " + YAST_PROXY)
        return None

    proxy_url = _parse_curl_proxy_url(contents)
    if not proxy_url:
        log_debug(1, "Could not read proxy URL from " + YAST_PROXY)
        return None

    username, password = _parse_curl_proxy_credentials(contents)

    return (proxy_url, username, password)


def _get_proxy_from_rhn_conf():
    """Return a tuple of (url, user, pass) proxy information from rhn config

    Returns None instead of a tuple if there was no proxy url. user,
    pass can be None.

    """
    initCFG("server.satellite")
    if CFG.http_proxy:
        # CFG.http_proxy format is <hostname>[:<port>] in 1.7
        url = 'http://%s' % CFG.http_proxy
        return (url, CFG.http_proxy_username, CFG.http_proxy_password)
    log_debug(1, "Could not read proxy URL from rhn config.")
