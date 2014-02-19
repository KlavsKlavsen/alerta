
import os
import sys
import smtplib
import socket
import urllib2
import datetime

from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

from alerta.common import log as logging
from alerta.common import config

LOG = logging.getLogger(__name__)
CONF = config.CONF


class Mailer(object):

    mailer_opt = {
        'smtp_host': 'localhost',
        'smtp_port': 25,
        'mail_user': 'alerta@guardian.co.uk',
        'mail_list': 'websys@guardian.co.uk',
    }

    def __init__(self, alert):

        config.register_opts(Mailer.mailer_opt)

        self.subject = '[%s] %s' % (alert.status, alert.summary)

        self.text = "-" * 60 + "\n"
        self.text += "[%s] %s\n" % (alert.status, alert.summary)
        self.text += "-" * 60 + "\n\n"

        self.text += "Alert Details\n\n"

        self.text += "Alert ID: %s\n" % alert.get_id()
        self.text += "Create Time: %s\n" % alert.get_create_time()
        self.text += "Environment: %s\n" % ", ".join(alert.environment)
        self.text += "Service: %s\n" % ", ".join(alert.service)
        self.text += "Resource: %s\n" % alert.resource
        self.text += "Event: %s\n" % alert.event
        self.text += "Group: %s\n" % alert.group
        self.text += "Value: %s\n" % alert.value
        self.text += "Severity: %s -> %s\n" % (alert.previous_severity, alert.severity)
        self.text += "Status: %s\n" % alert.status
        self.text += "Text: %s\n" % alert.text
        self.text += "Threshold Info: %s\n" % alert.threshold_info
        self.text += "Duplicate Count: %s\n" % alert.duplicate_count
        self.text += "Origin: %s\n" % alert.origin
        self.text += "Tags: %s\n" % ", ".join(k + '=' + v for k, v in alert.tags.items())
        self.text += "More Info: %s\n\n" % alert.more_info

        if hasattr(alert, 'graph_urls'):
            self.text += "Graphs\n\n"
            for graph in alert.graph_urls:
                self.text += '%s\n' % graph
            self.text += "\n"

        if CONF.debug:
            self.text += "Raw Alert\n\n"
            self.text += "%s\n\n" % alert.get_body()

        self.text += "To acknowledge this alert visit this URL:\n"
        self.text += "%s?id=%s\n\n" % (CONF.dashboard_url, alert.get_id())

        self.text += "Generated by %s on %s at %s\n" % (
            os.path.basename(sys.argv[0]), os.uname()[1], datetime.datetime.now().strftime("%a %d %b %H:%M:%S"))

        LOG.debug('Email Text: %s', self.text)

        self.graph_urls = alert.graph_urls if hasattr(alert, 'graph_urls') else None

    def send(self, mail_to=None):

        LOG.debug('mail_to = %s', mail_to)

        msg = MIMEMultipart('related')
        msg['Subject'] = self.subject
        msg['From'] = CONF.mail_user
        msg['To'] = ", ".join(mail_to)
        msg.preamble = self.subject

        msg_text = MIMEText(self.text, 'plain', 'utf-8')
        msg.attach(msg_text)

        for graph in self.graph_urls:
            try:
                img = MIMEImage(urllib2.urlopen(graph).read())
                msg.attach(img)
            except Exception, e:
                LOG.warning('Unknown exception raised while attaching graphs to email: %s', e)
                pass

        try:
            mx = smtplib.SMTP(CONF.smtp_host)
        except (socket.error, socket.herror, socket.gaierror), e:
            LOG.error('Mail server connection error: %s', e)
            return

        try:
            if CONF.debug:
                mx.set_debuglevel(True)
            mx.sendmail(CONF.mail_user, mail_to, msg.as_string())
            mx.quit()
        except AttributeError, e:
            LOG.error('Problem with mail attributes: %s', e)

        except smtplib.SMTPException, e:
            LOG.error('Failed to send mail to %s on %s:%s : %s', ", ".join(mail_to), CONF.mail_host, CONF.mail_port, e)



