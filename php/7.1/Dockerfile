FROM php:7.1-fpm-alpine3.13


ADD https://github.com/mlocati/docker-php-extension-installer/releases/latest/download/install-php-extensions /usr/local/bin/
RUN chmod uga+x /usr/local/bin/install-php-extensions

ADD setup.sh /usr/local/lib/setup
RUN chmod uga+x /usr/local/lib/setup

RUN /usr/local/lib/setup

COPY php.ini /usr/local/etc/php/