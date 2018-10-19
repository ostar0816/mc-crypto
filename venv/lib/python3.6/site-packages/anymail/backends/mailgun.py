from datetime import datetime

from ..exceptions import AnymailRequestsAPIError, AnymailError
from ..message import AnymailRecipientStatus
from ..utils import get_anymail_setting, rfc2822date

from .base_requests import AnymailRequestsBackend, RequestsPayload


class EmailBackend(AnymailRequestsBackend):
    """
    Mailgun API Email Backend
    """

    esp_name = "Mailgun"

    def __init__(self, **kwargs):
        """Init options from Django settings"""
        esp_name = self.esp_name
        self.api_key = get_anymail_setting('api_key', esp_name=esp_name, kwargs=kwargs, allow_bare=True)
        self.sender_domain = get_anymail_setting('sender_domain', esp_name=esp_name, kwargs=kwargs,
                                                 allow_bare=True, default=None)
        api_url = get_anymail_setting('api_url', esp_name=esp_name, kwargs=kwargs,
                                      default="https://api.mailgun.net/v3")
        if not api_url.endswith("/"):
            api_url += "/"
        super(EmailBackend, self).__init__(api_url, **kwargs)

    def build_message_payload(self, message, defaults):
        return MailgunPayload(message, defaults, self)

    def parse_recipient_status(self, response, payload, message):
        # The *only* 200 response from Mailgun seems to be:
        #     {
        #       "id": "<20160306015544.116301.25145@example.org>",
        #       "message": "Queued. Thank you."
        #     }
        #
        # That single message id applies to all recipients.
        # The only way to detect rejected, etc. is via webhooks.
        # (*Any* invalid recipient addresses will generate a 400 API error)
        parsed_response = self.deserialize_json_response(response, payload, message)
        try:
            message_id = parsed_response["id"]
            mailgun_message = parsed_response["message"]
        except (KeyError, TypeError):
            raise AnymailRequestsAPIError("Invalid Mailgun API response format",
                                          email_message=message, payload=payload, response=response,
                                          backend=self)
        if not mailgun_message.startswith("Queued"):
            raise AnymailRequestsAPIError("Unrecognized Mailgun API message '%s'" % mailgun_message,
                                          email_message=message, payload=payload, response=response,
                                          backend=self)
        # Simulate a per-recipient status of "queued":
        status = AnymailRecipientStatus(message_id=message_id, status="queued")
        return {recipient.addr_spec: status for recipient in payload.all_recipients}


class MailgunPayload(RequestsPayload):

    def __init__(self, message, defaults, backend, *args, **kwargs):
        auth = ("api", backend.api_key)
        self.sender_domain = backend.sender_domain
        self.all_recipients = []  # used for backend.parse_recipient_status

        # late-binding of recipient-variables:
        self.merge_data = None
        self.merge_global_data = None
        self.to_emails = []

        super(MailgunPayload, self).__init__(message, defaults, backend, auth=auth, *args, **kwargs)

    def get_api_endpoint(self):
        if self.sender_domain is None:
            raise AnymailError("Cannot call Mailgun unknown sender domain. "
                               "Either provide valid `from_email`, "
                               "or set `message.esp_extra={'sender_domain': 'example.com'}`",
                               backend=self.backend, email_message=self.message, payload=self)
        return "%s/messages" % self.sender_domain

    def serialize_data(self):
        self.populate_recipient_variables()
        return self.data

    def populate_recipient_variables(self):
        """Populate Mailgun recipient-variables header from merge data"""
        merge_data = self.merge_data

        if self.merge_global_data is not None:
            # Mailgun doesn't support global variables.
            # We emulate them by populating recipient-variables for all recipients.
            if merge_data is not None:
                merge_data = merge_data.copy()  # don't modify the original, which doesn't belong to us
            else:
                merge_data = {}
            for email in self.to_emails:
                try:
                    recipient_data = merge_data[email]
                except KeyError:
                    merge_data[email] = self.merge_global_data
                else:
                    # Merge globals (recipient_data wins in conflict)
                    merge_data[email] = self.merge_global_data.copy()
                    merge_data[email].update(recipient_data)

        if merge_data is not None:
            self.data['recipient-variables'] = self.serialize_json(merge_data)

    #
    # Payload construction
    #

    def init_payload(self):
        self.data = {}   # {field: [multiple, values]}
        self.files = []  # [(field, multiple), (field, values)]

    def set_from_email_list(self, emails):
        # Mailgun supports multiple From email addresses
        self.data["from"] = [email.address for email in emails]
        if self.sender_domain is None and len(emails) > 0:
            # try to intuit sender_domain from first from_email
            self.sender_domain = emails[0].domain or None

    def set_recipients(self, recipient_type, emails):
        assert recipient_type in ["to", "cc", "bcc"]
        if emails:
            self.data[recipient_type] = [email.address for email in emails]
            self.all_recipients += emails  # used for backend.parse_recipient_status
        if recipient_type == 'to':
            self.to_emails = [email.addr_spec for email in emails]  # used for populate_recipient_variables

    def set_subject(self, subject):
        self.data["subject"] = subject

    def set_reply_to(self, emails):
        if emails:
            reply_to = ", ".join([str(email) for email in emails])
            self.data["h:Reply-To"] = reply_to

    def set_extra_headers(self, headers):
        for key, value in headers.items():
            self.data["h:%s" % key] = value

    def set_text_body(self, body):
        self.data["text"] = body

    def set_html_body(self, body):
        if "html" in self.data:
            # second html body could show up through multiple alternatives, or html body + alternative
            self.unsupported_feature("multiple html parts")
        self.data["html"] = body

    def add_attachment(self, attachment):
        # http://docs.python-requests.org/en/v2.4.3/user/advanced/#post-multiple-multipart-encoded-files
        if attachment.inline:
            field = "inline"
            name = attachment.cid
        else:
            field = "attachment"
            name = attachment.name
        self.files.append(
            (field, (name, attachment.content, attachment.mimetype))
        )

    def set_envelope_sender(self, email):
        # Only the domain is used
        self.sender_domain = email.domain

    def set_metadata(self, metadata):
        for key, value in metadata.items():
            self.data["v:%s" % key] = value

    def set_send_at(self, send_at):
        # Mailgun expects RFC-2822 format dates
        # (BasePayload has converted most date-like values to datetime by now;
        # if the caller passes a string, they'll need to format it themselves.)
        if isinstance(send_at, datetime):
            send_at = rfc2822date(send_at)
        self.data["o:deliverytime"] = send_at

    def set_tags(self, tags):
        self.data["o:tag"] = tags

    def set_track_clicks(self, track_clicks):
        # Mailgun also supports an "htmlonly" option, which Anymail doesn't offer
        self.data["o:tracking-clicks"] = "yes" if track_clicks else "no"

    def set_track_opens(self, track_opens):
        self.data["o:tracking-opens"] = "yes" if track_opens else "no"

    # template_id: Mailgun doesn't offer stored templates.
    # (The message body and other fields *are* the template content.)

    def set_merge_data(self, merge_data):
        # Processed at serialization time (to allow merging global data)
        self.merge_data = merge_data

    def set_merge_global_data(self, merge_global_data):
        # Processed at serialization time (to allow merging global data)
        self.merge_global_data = merge_global_data

    def set_esp_extra(self, extra):
        self.data.update(extra)
        # Allow override of sender_domain via esp_extra
        # (but pop it out of params to send to Mailgun)
        self.sender_domain = self.data.pop("sender_domain", self.sender_domain)
