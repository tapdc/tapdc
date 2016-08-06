
# TAP-DC Website

This is the code for tap-dc.org

## Files

 - www/ -- all the front-end code
 - www/_*.html -- page fragments
 - www/*.html -- full pages
 - www/media/ -- all the pictures used on the website
 - www/lib/ -- all the 3rd-party dependencies (jquery, fonts, etc.)

 - ssi.js -- this is a simple [Server-Side Includes](https://en.wikipedia.org/wiki/Server_Side_Includes) server that I wrote in NodeJS
 - fb.py -- this is a bot I wrote in Python that scrapes events off Facebook and generates 3 page fragments: _upcoming.html _past.html _next.html

## Running

```node ssi.js```

The server (ssi.js) automatically runs the bot (fb.py) every hour.

## Notes

 - You will need to register for a Facebook app under your name and get a "client token" in order to use the bot (fb.py). Copy the token where it says token = '' (line 34).

 - No images are used for the TAP-DC logo, since I was unable to obtain hi-res images. Instead, I drew the logo entirely with CSS/HTML. The code is in _logo.html
