import re

from ..exceptions import AnymailRequestsAPIError
from ..message import AnymailRecipientStatus
from ..utils import get_anymail_setting

from .base_requests import AnymailRequestsBackend, RequestsPayload


class EmailBackend(AnymailRequestsBackend):
    """
    Postmark API Email Backend
    """

    esp_name = "Postmark"

    def __init__(self, **kwargs):
        """Init options from Django settings"""
        esp_name = self.esp_name
        self.server_token = get_anymail_setting('server_token', esp_name=esp_name, kwargs=kwargs, allow_bare=True)
        api_url = get_anymail_setting('api_url', esp_name=esp_name, kwargs=kwargs,
                                      default="https://api.postmarkapp.com/")
        if not api_url.endswith("/"):
            api_url += "/"
        super(EmailBackend, self).__init__(api_url, **kwargs)

    def build_message_payload(self, message, defaults):
        return PostmarkPayload(message, defaults, self)

    def raise_for_status(self, response, payload, message):
        # We need to handle 422 responses in parse_recipient_status
        if response.status_code != 422:
            super(EmailBackend, self).raise_for_status(response, payload, message)

    def parse_recipient_status(self, response, payload, message):
        parsed_response = self.deserialize_json_response(response, payload, message)
        try:
            error_code = parsed_response["ErrorCode"]
            msg = parsed_response["Message"]
        except (KeyError, TypeError):
            raise AnymailRequestsAPIError("Invalid Postmark API response format",
                                          email_message=message, payload=payload, response=response,
                                          backend=self)

        message_id = parsed_response.get("MessageID", None)
        rejected_emails = []

        if error_code == 300:  # Invalid email request
            # Either the From address or at least one recipient was invalid. Email not sent.
            if "'From' address" in msg:
                # Normal error
                raise AnymailRequestsAPIError(email_message=message, payload=payload, response=response,
                                              backend=self)
            else:
                # Use AnymailRecipientsRefused logic
                default_status = 'invalid'
        elif error_code == 406:  # Inactive recipient
            # All recipients were rejected as hard-bounce or spam-complaint. Email not sent.
            default_status = 'rejected'
        elif error_code == 0:
            # At least partial success, and email was sent.
            # Sadly, have to parse human-readable message to figure out if everyone got it.
            default_status = 'sent'
            rejected_emails = self.parse_inactive_recipients(msg)
        else:
            raise AnymailRequestsAPIError(email_message=message, payload=payload, response=response,
                                          backend=self)

        return {
            recipient.addr_spec: AnymailRecipientStatus(
                message_id=message_id,
                status=('rejected' if recipient.addr_spec.lower() in rejected_emails
                        else default_status)
            )
            for recipient in payload.all_recipients
        }

    def parse_inactive_recipients(self, msg):
        """Return a list of 'inactive' email addresses from a Postmark "OK" response

        :param str msg: the "Message" from the Postmark API response
        """
        # Example msg with inactive recipients:
        #   "Message OK, but will not deliver to these inactive addresses: one@xample.com, two@example.com."
        #   " Inactive recipients are ones that have generated a hard bounce or a spam complaint."
        # Example msg with everything OK: "OK"
        match = re.search(r'inactive addresses:\s*(.*)\.\s*Inactive recipients', msg)
        if match:
            emails = match.group(1)  # "one@xample.com, two@example.com"
            return [email.strip().lower() for email in emails.split(',')]
        else:
            return []


class PostmarkPayload(RequestsPayload):

    def __init__(self, message, defaults, backend, *args, **kwargs):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            # 'X-Postmark-Server-Token': see get_request_params (and set_esp_extra)
        }
        self.server_token = backend.server_token  # added to headers later, so esp_extra can override
        self.all_recipients = []  # used for backend.parse_recipient_status
        super(PostmarkPayload, self).__init__(message, defaults, backend, headers=headers, *args, **kwargs)

    def get_api_endpoint(self):
        if 'TemplateId' in self.data or 'TemplateModel' in self.data:
            # This is the one Postmark API documented to have a trailing slash. (Typo?)
            return "email/withTemplate/"
        else:
            return "email"

    def get_request_params(self, api_url):
        params = super(PostmarkPayload, self).get_request_params(api_url)
        params['headers']['X-Postmark-Server-Token'] = self.server_token
        return params

    def serialize_data(self):
        return self.serialize_json(self.data)

    #
    # Payload construction
    #

    def init_payload(self):
        self.data = {}   # becomes json

    def set_from_email_list(self, emails):
        # Postmark accepts multiple From email addresses
        # (though truncates to just the first, on their end, as of 4/2017)
        self.data["From"] = ", ".join([email.address for email in emails])

    def set_recipients(self, recipient_type, emails):
        assert recipient_type in ["to", "cc", "bcc"]
        if emails:
            field = recipient_type.capitalize()
            self.data[field] = ', '.join([email.address for email in emails])
            self.all_recipients += emails  # used for backend.parse_recipient_status

    def set_subject(self, subject):
        self.data["Subject"] = subject

    def set_reply_to(self, emails):
        if emails:
            reply_to = ", ".join([email.address for email in emails])
            self.data["ReplyTo"] = reply_to

    def set_extra_headers(self, headers):
        self.data["Headers"] = [
            {"Name": key, "Value": value}
            for key, value in headers.items()
        ]

    def set_text_body(self, body):
        self.data["TextBody"] = body

    def set_html_body(self, body):
        if "HtmlBody" in self.data:
            # second html body could show up through multiple alternatives, or html body + alternative
            self.unsupported_feature("multiple html parts")
        self.data["HtmlBody"] = body

    def make_attachment(self, attachment):
        """Returns Postmark attachment dict for attachment"""
        att = {
            "Name": attachment.name or "",
            "Content": attachment.b64content,
            "ContentType": attachment.mimetype,
        }
        if attachment.inline:
            att["ContentID"] = "cid:%s" % attachment.cid
        return att

    def set_attachments(self, attachments):
        if attachments:
            self.data["Attachments"] = [
                self.make_attachment(attachment) for attachment in attachments
            ]

    # Postmark doesn't support metadata
    # def set_metadata(self, metadata):

    # Postmark doesn't support delayed sending
    # def set_send_at(self, send_at):

    def set_tags(self, tags):
        if len(tags) > 0:
            self.data["Tag"] = tags[0]
            if len(tags) > 1:
                self.unsupported_feature('multiple tags (%r)' % tags)

    def set_track_clicks(self, track_clicks):
        self.data["TrackLinks"] = 'HtmlAndText' if track_clicks else 'None'

    def set_track_opens(self, track_opens):
        self.data["TrackOpens"] = track_opens

    def set_template_id(self, template_id):
        self.data["TemplateId"] = template_id

    # merge_data: Postmark doesn't support per-recipient substitutions

    def set_merge_global_data(self, merge_global_data):
        self.data["TemplateModel"] = merge_global_data

    def set_esp_extra(self, extra):
        self.data.update(extra)
        # Special handling for 'server_token':
        self.server_token = self.data.pop('server_token', self.server_token)
