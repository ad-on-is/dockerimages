# PHP7-FPM images for web development

![Status](https://gitlab.com/ad-on-is/php/badges/master/pipeline.svg) ![Pulls](https://img.shields.io/docker/pulls/adisdurakovic/php.svg)

- Optimized PHP Docker images for Web-Development
- Based on [official PHP Docker images](https://hub.docker.com/r/_/php/)

## Installed PHP extensions

- APCu
- BC Math
- Bzip2
- Calendar
- Exif
- GD
- Intl
- Memcached
- Mcrypt
- MySQLi
- MySQL (PDO)
- Zend OPcache
- PostgreSQL
- Redis
- SOAP
- Zip
- XDebug (`dev` only)

## Additional tools

- ImageMagick
- GhostScript
- GraphicsMagick
- SSMTP

## CLIs

- Composer
- WP-CLI

## Optimized for all PHP-frameworks and CMS

![Frameworks](https://dnmc.at/frameworks.png)

## Source repository

https://gitlab.com/ad-on-is/php

## Docker repositories

- `adisdurakovic/php`

## Available tags and Dockerfile links

- [_`latest, 8.0` (Dockerfile)_](https://gitlab.com/ad-on-is/php/blob/master/Dockerfile)
- [_`7.4` (Dockerfile)_](https://gitlab.com/ad-on-is/php/blob/master/7.4/Dockerfile)
- [_`7.3` (Dockerfile)_](https://gitlab.com/ad-on-is/php/blob/master/7.3/Dockerfile)
- [_`7.2` (Dockerfile)_](https://gitlab.com/ad-on-is/php/blob/master/7.2/Dockerfile)
- [`7.1` (7.1/Dockerfile)](https://gitlab.com/ad-on-is/php/blob/master/7.1/Dockerfile)
- [`7.0` (7.0/Dockerfile)](https://gitlab.com/ad-on-is/php/blob/master/7.0/Dockerfile)

## Usage example with docker-compose.yml

    version: '3'

    services:

        nginx:
            image: nginx:latest
            ports:
                - 80:80
                - 443:443
            links:
                - mysql
                - php-fpm
            container_name: nginx

        php-fpm:
            image: adisdurakovic/php-dev:7.2
            container_name: php-fpm

        mysql:
            image: mysql:5.7
            container_name: mysql
            ports:
                - 3306:3306
