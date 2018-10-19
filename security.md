For protection against CSRF attacks
- Add csrf_token tag inside form element.


Without this, it is possible for malicious network users to sniff authentication credentials or
any other information transferred between client and server, and in some cases – active network
attackers – to alter data that is sent in either direction.

- SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

To make requests over HTTP are redirected to HTTPS.
-  SECURE_SSL_REDIRECT = True


If a browser connects initially via HTTP, which is the default for most browsers,
it is possible for existing cookies to be leaked.
- SESSION_COOKIE_SECURE = True
- CSRF_COOKIE_SECURE = True


For sites that should only be accessed over HTTPS, it is possible to instruct modern
browsers to refuse to connect to domain name via an insecure connection
(for a given period of time) by setting the “Strict-Transport-Security” header.
This reduces exposure to some SSL-stripping man-in-the-middle (MITM) attacks.

To set the HTTP Strict Transport Security header on all responses that do not already have it.
- SECURE_HSTS_SECONDS = 31536000

To add the includeSubDomains directive to the HTTP Strict Transport Security header.
- SECURE_HSTS_INCLUDE_SUBDOMAINS = True

To add the preload directive to the HTTP Strict Transport Security header.
- SECURE_HSTS_PRELOAD = True