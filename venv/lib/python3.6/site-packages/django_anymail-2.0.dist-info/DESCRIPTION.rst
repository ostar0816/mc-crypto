Anymail: Django email integration for transactional ESPs
========================================================

..  This README is reused in multiple places:
    * Github: project page, exactly as it appears here
    * Docs: shared-intro section gets included in docs/index.rst
            quickstart section gets included in docs/quickstart.rst
    * PyPI: project page (via setup.py long_description),
            with several edits to freeze it to the specific PyPI release
            (see long_description_from_readme in setup.py)
    You can use docutils 1.0 markup, but *not* any Sphinx additions.
    GitHub rst supports code-block, but *no other* block directives.


.. default-role:: literal


.. _shared-intro:

.. This shared-intro section is also included in docs/index.rst

Anymail integrates several transactional email service providers (ESPs) into Django,
with a consistent API that lets you use ESP-added features without locking your code
to a particular ESP.

It currently fully supports **Mailgun, Mailjet, Postmark, SendinBlue, SendGrid,**
and **SparkPost,** and has limited support for **Mandrill.**

Anymail normalizes ESP functionality so it "just works" with Django's
built-in `django.core.mail` package. It includes:

* Support for HTML, attachments, extra headers, and other features of
  `Django's built-in email <https://docs.djangoproject.com/en/v2.0/topics/email/>`_
* Extensions that make it easy to use extra ESP functionality, like tags, metadata,
  and tracking, with code that's portable between ESPs
* Simplified inline images for HTML email
* Normalized sent-message status and tracking notification, by connecting
  your ESP's webhooks to Django signals
* "Batch transactional" sends using your ESP's merge and template features
* Inbound message support, to receive email through your ESP's webhooks,
  with simplified, portable access to attachments and other inbound content

Anymail is released under the BSD license. It is extensively tested against Django 1.8--2.0
(including Python 2.7, Python 3 and PyPy).
Anymail releases follow `semantic versioning <http://semver.org/>`_.

.. END shared-intro

.. image:: https://travis-ci.org/anymail/django-anymail.svg?branch=v2.0
       :target: https://travis-ci.org/anymail/django-anymail
       :alt:    build status on Travis-CI

.. image:: https://readthedocs.org/projects/anymail/badge/?version=v2.0
       :target: https://anymail.readthedocs.io/en/v2.0/
       :alt:    documentation on ReadTheDocs

**Resources**

* Full documentation: https://anymail.readthedocs.io/en/v2.0/
* Package on PyPI: https://pypi.python.org/pypi/django-anymail
* Project on Github: https://github.com/anymail/django-anymail
* Changelog: https://github.com/anymail/django-anymail/releases


Anymail 1-2-3
-------------

.. _quickstart:

.. This quickstart section is also included in docs/quickstart.rst

Here's how to send a message.
This example uses Mailgun, but you can substitute Mailjet or Postmark or SendGrid
or SparkPost or any other supported ESP where you see "mailgun":

1. Install Anymail from PyPI:

   .. code-block:: console

        $ pip install django-anymail[mailgun]

   (The `[mailgun]` part installs any additional packages needed for that ESP.
   Mailgun doesn't have any, but some other ESPs do.)


2. Edit your project's ``settings.py``:

   .. code-block:: python

        INSTALLED_APPS = [
            # ...
            "anymail",
            # ...
        ]

        ANYMAIL = {
            # (exact settings here depend on your ESP...)
            "MAILGUN_API_KEY": "<your Mailgun key>",
            "MAILGUN_SENDER_DOMAIN": 'mg.example.com',  # your Mailgun domain, if needed
        }
        EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"  # or sendgrid.EmailBackend, or...
        DEFAULT_FROM_EMAIL = "you@example.com"  # if you don't already have this in settings


3. Now the regular `Django email functions <https://docs.djangoproject.com/en/v2.0/topics/email/>`_
   will send through your chosen ESP:

   .. code-block:: python

        from django.core.mail import send_mail

        send_mail("It works!", "This will get sent through Mailgun",
                  "Anymail Sender <from@example.com>", ["to@example.com"])


   You could send an HTML message, complete with an inline image,
   custom tags and metadata:

   .. code-block:: python

        from django.core.mail import EmailMultiAlternatives
        from anymail.message import attach_inline_image_file

        msg = EmailMultiAlternatives(
            subject="Please activate your account",
            body="Click to activate your account: http://example.com/activate",
            from_email="Example <admin@example.com>",
            to=["New User <user1@example.com>", "account.manager@example.com"],
            reply_to=["Helpdesk <support@example.com>"])

        # Include an inline image in the html:
        logo_cid = attach_inline_image_file(msg, "/path/to/logo.jpg")
        html = """<img alt="Logo" src="cid:{logo_cid}">
                  <p>Please <a href="http://example.com/activate">activate</a>
                  your account</p>""".format(logo_cid=logo_cid)
        msg.attach_alternative(html, "text/html")

        # Optional Anymail extensions:
        msg.metadata = {"user_id": "8675309", "experiment_variation": 1}
        msg.tags = ["activation", "onboarding"]
        msg.track_clicks = True

        # Send it:
        msg.send()

.. END quickstart


See the `full documentation <https://anymail.readthedocs.io/en/v2.0/>`_
for more features and options, including receiving messages and tracking
sent message status.


