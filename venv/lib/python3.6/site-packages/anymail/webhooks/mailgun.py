import json
from datetime import datetime

import hashlib
import hmac
from django.utils.crypto import constant_time_compare
from django.utils.timezone import utc

from .base import AnymailBaseWebhookView
from ..exceptions import AnymailWebhookValidationFailure
from ..inbound import AnymailInboundMessage
from ..signals import inbound, tracking, AnymailInboundEvent, AnymailTrackingEvent, EventType, RejectReason
from ..utils import get_anymail_setting, combine, querydict_getfirst


class MailgunBaseWebhookView(AnymailBaseWebhookView):
    """Base view class for Mailgun webhooks"""

    esp_name = "Mailgun"
    warn_if_no_basic_auth = False  # because we validate against signature

    api_key = None  # (Declaring class attr allows override by kwargs in View.as_view.)

    def __init__(self, **kwargs):
        api_key = get_anymail_setting('api_key', esp_name=self.esp_name,
                                      kwargs=kwargs, allow_bare=True)
        self.api_key = api_key.encode('ascii')  # hmac.new requires bytes key in python 3
        super(MailgunBaseWebhookView, self).__init__(**kwargs)

    def validate_request(self, request):
        super(MailgunBaseWebhookView, self).validate_request(request)  # first check basic auth if enabled
        try:
            # Must use the *last* value of these fields if there are conflicting merged user-variables.
            # (Fortunately, Django QueryDict is specced to return the last value.)
            token = request.POST['token']
            timestamp = request.POST['timestamp']
            signature = str(request.POST['signature'])  # force to same type as hexdigest() (for python2)
        except KeyError:
            raise AnymailWebhookValidationFailure("Mailgun webhook called without required security fields")
        expected_signature = hmac.new(key=self.api_key, msg='{}{}'.format(timestamp, token).encode('ascii'),
                                      digestmod=hashlib.sha256).hexdigest()
        if not constant_time_compare(signature, expected_signature):
            raise AnymailWebhookValidationFailure("Mailgun webhook called with incorrect signature")


class MailgunTrackingWebhookView(MailgunBaseWebhookView):
    """Handler for Mailgun delivery and engagement tracking webhooks"""

    signal = tracking

    event_types = {
        # Map Mailgun event: Anymail normalized type
        'delivered': EventType.DELIVERED,
        'dropped': EventType.REJECTED,
        'bounced': EventType.BOUNCED,
        'complained': EventType.COMPLAINED,
        'unsubscribed': EventType.UNSUBSCRIBED,
        'opened': EventType.OPENED,
        'clicked': EventType.CLICKED,
        # Mailgun does not send events corresponding to QUEUED or DEFERRED
    }

    reject_reasons = {
        # Map Mailgun (SMTP) error codes to Anymail normalized reject_reason.
        # By default, we will treat anything 400-599 as REJECT_BOUNCED
        # so only exceptions are listed here.
        499: RejectReason.TIMED_OUT,  # unable to connect to MX (also covers invalid recipients)
        # These 6xx codes appear to be Mailgun extensions to SMTP
        # (and don't seem to be documented anywhere):
        605: RejectReason.BOUNCED,  # previous bounce
        607: RejectReason.SPAM,  # previous spam complaint
    }

    def parse_events(self, request):
        return [self.esp_to_anymail_event(request.POST)]

    def esp_to_anymail_event(self, esp_event):
        # esp_event is a Django QueryDict (from request.POST),
        # which has multi-valued fields, but is *not* case-insensitive.
        # Because of the way Mailgun merges user-variables into the event,
        # we must generally use the *first* value of any multi-valued field
        # to avoid potential conflicting user-data.
        esp_event.getfirst = querydict_getfirst.__get__(esp_event)

        event_type = self.event_types.get(esp_event.getfirst('event'), EventType.UNKNOWN)
        timestamp = datetime.fromtimestamp(int(esp_event['timestamp']), tz=utc)  # use *last* value of timestamp
        # Message-Id is not documented for every event, but seems to always be included.
        # (It's sometimes spelled as 'message-id', lowercase, and missing the <angle-brackets>.)
        message_id = esp_event.getfirst('Message-Id', None) or esp_event.getfirst('message-id', None)
        if message_id and not message_id.startswith('<'):
            message_id = "<{}>".format(message_id)

        description = esp_event.getfirst('description', None)
        mta_response = esp_event.getfirst('error', None) or esp_event.getfirst('notification', None)
        reject_reason = None
        try:
            mta_status = int(esp_event.getfirst('code'))
        except (KeyError, TypeError):
            pass
        except ValueError:
            # RFC-3463 extended SMTP status code (class.subject.detail, where class is "2", "4" or "5")
            try:
                status_class = esp_event.getfirst('code').split('.')[0]
            except (TypeError, IndexError):
                # illegal SMTP status code format
                pass
            else:
                reject_reason = RejectReason.BOUNCED if status_class in ("4", "5") else RejectReason.OTHER
        else:
            reject_reason = self.reject_reasons.get(
                mta_status,
                RejectReason.BOUNCED if 400 <= mta_status < 600
                else RejectReason.OTHER)

        metadata = self._extract_metadata(esp_event)

        # tags are supposed to be in 'tag' fields, but are sometimes in undocumented X-Mailgun-Tag
        tags = esp_event.getlist('tag', None) or esp_event.getlist('X-Mailgun-Tag', [])

        return AnymailTrackingEvent(
            event_type=event_type,
            timestamp=timestamp,
            message_id=message_id,
            event_id=esp_event.get('token', None),  # use *last* value of token
            recipient=esp_event.getfirst('recipient', None),
            reject_reason=reject_reason,
            description=description,
            mta_response=mta_response,
            tags=tags,
            metadata=metadata,
            click_url=esp_event.getfirst('url', None),
            user_agent=esp_event.getfirst('user-agent', None),
            esp_event=esp_event,
        )

    def _extract_metadata(self, esp_event):
        # Mailgun merges user-variables into the POST fields. If you know which user variable
        # you want to retrieve--and it doesn't conflict with a Mailgun event field--that's fine.
        # But if you want to extract all user-variables (like we do), it's more complicated...
        event_type = esp_event.getfirst('event')
        metadata = {}

        if 'message-headers' in esp_event:
            # For events where original message headers are available, it's most reliable
            # to recover user-variables from the X-Mailgun-Variables header(s).
            headers = json.loads(esp_event['message-headers'])
            variables = [value for [field, value] in headers if field == 'X-Mailgun-Variables']
            if len(variables) >= 1:
                # Each X-Mailgun-Variables value is JSON. Parse and merge them all into single dict:
                metadata = combine(*[json.loads(value) for value in variables])

        elif event_type in self._known_event_fields:
            # For other events, we must extract from the POST fields, ignoring known Mailgun
            # event parameters, and treating all other values as user-variables.
            known_fields = self._known_event_fields[event_type]
            for field, values in esp_event.lists():
                if field not in known_fields:
                    # Unknown fields are assumed to be user-variables. (There should really only be
                    # a single value, but just in case take the last one to match QueryDict semantics.)
                    metadata[field] = values[-1]
                elif field == 'tag':
                    # There's no way to distinguish a user-variable named 'tag' from an actual tag,
                    # so don't treat this/these value(s) as metadata.
                    pass
                elif len(values) == 1:
                    # This is an expected event parameter, and since there's only a single value
                    # it must be the event param, not metadata.
                    pass
                else:
                    # This is an expected event parameter, but there are (at least) two values.
                    # One is the event param, and the other is a user-variable metadata value.
                    # Which is which depends on the field:
                    if field in {'signature', 'timestamp', 'token'}:
                        metadata[field] = values[0]  # values = [user-variable, event-param]
                    else:
                        metadata[field] = values[-1]  # values = [event-param, user-variable]

        return metadata

    _common_event_fields = {
        # These fields are documented to appear in all Mailgun opened, clicked and unsubscribed events:
        'event', 'recipient', 'domain', 'ip', 'country', 'region', 'city', 'user-agent', 'device-type',
        'client-type', 'client-name', 'client-os', 'campaign-id', 'campaign-name', 'tag', 'mailing-list',
        'timestamp', 'token', 'signature',
        # Undocumented, but observed in actual events:
        'body-plain', 'h', 'message-id',
    }
    _known_event_fields = {
        # For all Mailgun event types that *don't* include message-headers,
        # map Mailgun (not normalized) event type to set of expected event fields.
        # Used for metadata extraction.
        'clicked': _common_event_fields | {'url'},
        'opened': _common_event_fields,
        'unsubscribed': _common_event_fields,
    }


class MailgunInboundWebhookView(MailgunBaseWebhookView):
    """Handler for Mailgun inbound (route forward-to-url) webhook"""

    signal = inbound

    def parse_events(self, request):
        return [self.esp_to_anymail_event(request)]

    def esp_to_anymail_event(self, request):
        # Inbound uses the entire Django request as esp_event, because we need POST and FILES.
        # Note that request.POST is case-sensitive (unlike email.message.Message headers).
        esp_event = request
        if 'body-mime' in request.POST:
            # Raw-MIME
            message = AnymailInboundMessage.parse_raw_mime(request.POST['body-mime'])
        else:
            # Fully-parsed
            message = self.message_from_mailgun_parsed(request)

        message.envelope_sender = request.POST.get('sender', None)
        message.envelope_recipient = request.POST.get('recipient', None)
        message.stripped_text = request.POST.get('stripped-text', None)
        message.stripped_html = request.POST.get('stripped-html', None)

        message.spam_detected = message.get('X-Mailgun-Sflag', 'No').lower() == 'yes'
        try:
            message.spam_score = float(message['X-Mailgun-Sscore'])
        except (TypeError, ValueError):
            pass

        return AnymailInboundEvent(
            event_type=EventType.INBOUND,
            timestamp=datetime.fromtimestamp(int(request.POST['timestamp']), tz=utc),
            event_id=request.POST.get('token', None),
            esp_event=esp_event,
            message=message,
        )

    def message_from_mailgun_parsed(self, request):
        """Construct a Message from Mailgun's "fully-parsed" fields"""
        # Mailgun transcodes all fields to UTF-8 for "fully parsed" messages
        try:
            attachment_count = int(request.POST['attachment-count'])
        except (KeyError, TypeError):
            attachments = None
        else:
            # Load attachments from posted files: Mailgun file field names are 1-based
            att_ids = ['attachment-%d' % i for i in range(1, attachment_count+1)]
            att_cids = {  # filename: content-id (invert content-id-map)
                att_id: cid for cid, att_id
                in json.loads(request.POST.get('content-id-map', '{}')).items()
            }
            attachments = [
                AnymailInboundMessage.construct_attachment_from_uploaded_file(
                    request.FILES[att_id], content_id=att_cids.get(att_id, None))
                for att_id in att_ids
            ]

        return AnymailInboundMessage.construct(
            headers=json.loads(request.POST['message-headers']),  # includes From, To, Cc, Subject, etc.
            text=request.POST.get('body-plain', None),
            html=request.POST.get('body-html', None),
            attachments=attachments,
        )
