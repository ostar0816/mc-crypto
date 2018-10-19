from __future__ import absolute_import  # we want the sparkpost package, not our own module

from .base import AnymailBaseBackend, BasePayload
from ..exceptions import AnymailAPIError, AnymailImproperlyInstalled, AnymailConfigurationError
from ..message import AnymailRecipientStatus
from ..utils import get_anymail_setting

try:
    from sparkpost import SparkPost, SparkPostException
except ImportError:
    raise AnymailImproperlyInstalled(missing_package='sparkpost', backend='sparkpost')


class EmailBackend(AnymailBaseBackend):
    """
    SparkPost Email Backend (using python-sparkpost client)
    """

    esp_name = "SparkPost"

    def __init__(self, **kwargs):
        """Init options from Django settings"""
        super(EmailBackend, self).__init__(**kwargs)
        # SPARKPOST_API_KEY is optional - library reads from env by default
        self.api_key = get_anymail_setting('api_key', esp_name=self.esp_name,
                                           kwargs=kwargs, allow_bare=True, default=None)
        try:
            self.sp = SparkPost(self.api_key)  # SparkPost API instance
        except SparkPostException as err:
            # This is almost certainly a missing API key
            raise AnymailConfigurationError(
                "Error initializing SparkPost: %s\n"
                "You may need to set ANYMAIL = {'SPARKPOST_API_KEY': ...} "
                "or ANYMAIL_SPARKPOST_API_KEY in your Django settings, "
                "or SPARKPOST_API_KEY in your environment." % str(err)
            )

    # Note: SparkPost python API doesn't expose requests session sharing
    # (so there's no need to implement open/close connection management here)

    def build_message_payload(self, message, defaults):
        return SparkPostPayload(message, defaults, self)

    def post_to_esp(self, payload, message):
        params = payload.get_api_params()
        try:
            response = self.sp.transmissions.send(**params)
        except SparkPostException as err:
            raise AnymailAPIError(
                str(err), backend=self, email_message=message, payload=payload,
                response=getattr(err, 'response', None),  # SparkPostAPIException requests.Response
                status_code=getattr(err, 'status', None),  # SparkPostAPIException HTTP status_code
            )
        return response

    def parse_recipient_status(self, response, payload, message):
        try:
            accepted = response['total_accepted_recipients']
            rejected = response['total_rejected_recipients']
            transmission_id = response['id']
        except (KeyError, TypeError) as err:
            raise AnymailAPIError(
                "%s in SparkPost.transmissions.send result %r" % (str(err), response),
                backend=self, email_message=message, payload=payload,
            )

        # SparkPost doesn't (yet*) tell us *which* recipients were accepted or rejected.
        # (* looks like undocumented 'rcpt_to_errors' might provide this info.)
        # If all are one or the other, we can report a specific status;
        # else just report 'unknown' for all recipients.
        recipient_count = len(payload.all_recipients)
        if accepted == recipient_count and rejected == 0:
            status = 'queued'
        elif rejected == recipient_count and accepted == 0:
            status = 'rejected'
        else:  # mixed results, or wrong total
            status = 'unknown'
        recipient_status = AnymailRecipientStatus(message_id=transmission_id, status=status)
        return {recipient.addr_spec: recipient_status for recipient in payload.all_recipients}


class SparkPostPayload(BasePayload):
    def init_payload(self):
        self.params = {}
        self.all_recipients = []
        self.to_emails = []
        self.merge_data = {}

    def get_api_params(self):
        # Compose recipients param from to_emails and merge_data (if any)
        recipients = []
        if len(self.merge_data) > 0:
            # Build JSON recipient structures
            for email in self.to_emails:
                rcpt = {'address': {'email': email.addr_spec}}
                if email.display_name:
                    rcpt['address']['name'] = email.display_name
                try:
                    rcpt['substitution_data'] = self.merge_data[email.addr_spec]
                except KeyError:
                    pass  # no merge_data or none for this recipient
                recipients.append(rcpt)
        else:
            # Just use simple recipients list
            recipients = [email.address for email in self.to_emails]
        if recipients:
            self.params['recipients'] = recipients

        # Must remove empty string "content" params when using stored template
        if self.params.get('template', None):
            for content_param in ['subject', 'text', 'html']:
                try:
                    if not self.params[content_param]:
                        del self.params[content_param]
                except KeyError:
                    pass

        return self.params

    def set_from_email_list(self, emails):
        # SparkPost supports multiple From email addresses,
        # as a single comma-separated string
        self.params['from_email'] = ", ".join([email.address for email in emails])

    def set_to(self, emails):
        if emails:
            self.to_emails = emails  # bound to params['recipients'] in get_api_params
            self.all_recipients += emails

    def set_cc(self, emails):
        if emails:
            self.params['cc'] = [email.address for email in emails]
            self.all_recipients += emails

    def set_bcc(self, emails):
        if emails:
            self.params['bcc'] = [email.address for email in emails]
            self.all_recipients += emails

    def set_subject(self, subject):
        self.params['subject'] = subject

    def set_reply_to(self, emails):
        if emails:
            # reply_to is only documented as a single email, but this seems to work:
            self.params['reply_to'] = ', '.join([email.address for email in emails])

    def set_extra_headers(self, headers):
        if headers:
            self.params['custom_headers'] = dict(headers)  # convert CaseInsensitiveDict to plain dict for SP lib

    def set_text_body(self, body):
        self.params['text'] = body

    def set_html_body(self, body):
        if 'html' in self.params:
            # second html body could show up through multiple alternatives, or html body + alternative
            self.unsupported_feature("multiple html parts")
        self.params['html'] = body

    def add_attachment(self, attachment):
        if attachment.inline:
            param = 'inline_images'
            name = attachment.cid
        else:
            param = 'attachments'
            name = attachment.name or ''

        self.params.setdefault(param, []).append({
            'type': attachment.mimetype,
            'name': name,
            'data': attachment.b64content})

    # Anymail-specific payload construction
    def set_envelope_sender(self, email):
        self.params['return_path'] = email.addr_spec

    def set_metadata(self, metadata):
        self.params['metadata'] = metadata

    def set_send_at(self, send_at):
        try:
            self.params['start_time'] = send_at.replace(microsecond=0).isoformat()
        except (AttributeError, TypeError):
            self.params['start_time'] = send_at  # assume user already formatted

    def set_tags(self, tags):
        if len(tags) > 0:
            self.params['campaign'] = tags[0]
            if len(tags) > 1:
                self.unsupported_feature('multiple tags (%r)' % tags)

    def set_track_clicks(self, track_clicks):
        self.params['track_clicks'] = track_clicks

    def set_track_opens(self, track_opens):
        self.params['track_opens'] = track_opens

    def set_template_id(self, template_id):
        # 'template' transmissions.send param becomes 'template_id' in API json 'content'
        self.params['template'] = template_id

    def set_merge_data(self, merge_data):
        self.merge_data = merge_data  # merged into params['recipients'] in get_api_params

    def set_merge_global_data(self, merge_global_data):
        self.params['substitution_data'] = merge_global_data

    # ESP-specific payload construction
    def set_esp_extra(self, extra):
        self.params.update(extra)
