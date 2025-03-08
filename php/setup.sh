#!/bin/sh

sync && install-php-extensions \
  apcu \
  bcmath \
  bz2 \
  calendar \
  exif \
  gd \
  gettext \
  imagick \
  intl \
  mcrypt \
  memcached \
  mysqli \
  opcache \
  pdo_mysql \
  pdo_pgsql \
  pgsql \
  redis \
  soap \
  uuid \
  zip \
  xsl \
  xdebug \
  @composer

tools=" \
    ghostscript \
    msmtp \
    " &&
  apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y $tools

curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar
chmod +x wp-cli.phar
mv wp-cli.phar /usr/local/bin/wp
