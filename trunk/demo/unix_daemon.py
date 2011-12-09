#!/usr/bin/env python
# $Id$

"""A basic unix daemon using the python-daemon library:
http://pypi.python.org/pypi/python-daemon

Example usages:

 $ python unix_daemon.py start
 $ python unix_daemon.py stop
 $ python unix_daemon.py status
 $ python unix_daemon.py --logfile /var/log/ftpd.log start
 $ python unix_daemon.py --pidfile /var/run/ftpd.pid start

This is just a proof of concept which demonstrates how to daemonize
the FTP server.
You might want to use this as an example and provide the necessary
customizations.

Parts you might want to customize are:
 - the global constants (PID_FILE, LOG_FILE, UMASK, WORKDIR)
 - get_server() function

Authors:
 - Michele Petrazzo - michele.petrazzo <at> gmail.com
 - Ben Timby - btimby <at> gmail.com
 - Giampaolo Rodola' - g.rodola <at> gmail.com
"""

from __future__ import with_statement

import os
import errno
import sys
import time
import optparse
import signal

from pyftpdlib import ftpserver

# http://pypi.python.org/pypi/python-daemon
import daemon
import daemon.pidfile


# overridable options
PID_FILE = "/var/run/pyftpdlib.pid"
LOG_FILE = None
UMASK = 0
WORKDIR = os.getcwd()


def pid_exists(pid):
    """Return True if a process with the given PID is currently running."""
    try:
        os.kill(pid, 0)
    except OSError, e:
        return e.errno == errno.EPERM
    else:
        return True

def get_pid():
    """Return PID saved in the pid file as an if possible, else None."""
    try:
        with open(PID_FILE) as f:
            return int(f.read().strip())
    except IOError, err:
        if err.errno != errno.ENOENT:
            raise

def kill():
    """Keep attempting to kill the daemon for 5 seconds, first using
    SIGTERM, then using SIGKILL.
    """
    pid = get_pid()
    if not pid or not pid_exists(pid):
        print "daemon not running"
        return
    sig = signal.SIGTERM
    i = 0
    while True:
        sys.stdout.write('.')
        sys.stdout.flush()
        try:
            os.kill(pid, sig)
        except OSError, e:
            if e.errno == errno.ESRCH:
                print "\nstopped (pid %s)" % pid
                return
            else:
                raise
        i += 1
        if i == 25:
            sig = signal.SIGKILL
        elif i == 50:
            sys.exit("\ncould not kill daemon (pid %s)" % pid)
        time.sleep(0.1)

def status():
    """Print daemon status and exit."""
    pid = get_pid()
    if not pid or not pid_exists(pid):
        print "daemon not running"
    else:
        print "daemon running with pid %s" % pid
    sys.exit(0)

def get_server():
    """Return a pre-configured FTP server instance."""
    authorizer = ftpserver.DummyAuthorizer()
    authorizer.add_user('user', '12345', os.getcwd(), perm='elradfmwM')
    authorizer.add_anonymous(os.getcwd())
    ftp_handler = ftpserver.FTPHandler
    ftp_handler.authorizer = authorizer
    server = ftpserver.FTPServer(('', 21), ftp_handler)
    return server

def daemonize():
    """A wrapper around pytho-daemonize context manager."""
    pid = get_pid()
    if pid and pid_exists(pid):
        sys.exit('daemon already running (pid %s)' % pid)
    ctx = daemon.DaemonContext(
        working_directory=WORKDIR,
        umask=UMASK,
        pidfile=daemon.pidfile.TimeoutPIDLockFile(PID_FILE)
    )
    if LOG_FILE is not None:
        ctx.stdout = ctx.stderr = open(LOG_FILE, 'wb')

    # instance FTPd before daemonizing, so that in case of problems we
    # get an exception here and exit immediately
    get_server().close_all()
    with ctx:
        server = get_server()
        server.serve_forever()

def main():
    global PID_FILE, LOG_FILE
    USAGE = "python [-d PIDFILE] [-o LOGFILE]\n\n" \
            "Commands:\n  - start\n  - stop\n  - status"
    parser = optparse.OptionParser(usage=USAGE)
    parser.add_option('-l', '--logfile', dest='logfile',
                      help='save stdout to a file')
    parser.add_option('-p', '--pidfile', dest='pidfile', default=PID_FILE,
                      help='file to store/retreive daemon pid')
    options, args = parser.parse_args()

    if options.pidfile:
        PID_FILE = options.pidfile
    if options.pidfile:
        LOG_FILE = options.logfile

    if not args:
        server = get_server()
        server.serve_forever()
    else:
        if len(args) != 1:
            sys.exit('too many commands')
        elif args[0] == 'start':
            daemonize()
        elif args[0] == 'stop':
            kill()
        elif args[0] == 'status':
            status()
        else:
            sys.exit('invalid command')

if __name__ == '__main__':
    sys.exit(main())
